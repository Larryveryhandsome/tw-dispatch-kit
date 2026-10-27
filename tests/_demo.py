"""測試共用：在暫存資料夾建示範資料、用隨機埠啟動示範 server，測完停掉並清掉暫存資料。

不連網、不需要任何金鑰。示範 server 本身會擋掉所有對外連線（見 app/demo_server.py）。
"""
import base64
import http.cookiejar
import json
import os
import pathlib
import shutil
import socket
import sqlite3
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / 'app'
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)      # Windows：不要跳黑色視窗


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def env_for(data_dir, port=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith('DISPATCH_')}
    env['DISPATCH_DATA'] = str(data_dir)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    if port:
        env['DEMO_PORT'] = str(port)
    return env


def run_seed(data_dir):
    return subprocess.run([sys.executable, str(APP / 'seed_demo.py')], env=env_for(data_dir), capture_output=True,
                          text=True, encoding='utf-8', timeout=180, creationflags=NO_WINDOW)


class Demo:
    """一個跑在暫存資料夾、隨機埠的示範 server。"""

    def __init__(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix='dispatch-test-'))
        self.data = self.tmp / 'data'
        self.port = free_port()
        self.base = f'http://127.0.0.1:{self.port}'
        self.proc = None
        self.log = None

    def start(self):
        r = run_seed(self.data)
        if r.returncode != 0:
            raise RuntimeError('seed_demo 失敗：' + r.stdout[-2000:] + r.stderr[-2000:])
        self.log = open(self.tmp / 'server.log', 'w', encoding='utf-8')
        self.proc = subprocess.Popen([sys.executable, str(APP / 'demo_server.py')], env=env_for(self.data, self.port),
                                     stdout=self.log, stderr=subprocess.STDOUT, creationflags=NO_WINDOW)
        deadline = time.time() + 60
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError('示範 server 沒起來：' + (self.tmp / 'server.log').read_text(encoding='utf-8')[-2000:])
            try:
                with urllib.request.urlopen(self.base + '/intro', timeout=2) as res:
                    if res.status == 200:
                        return self
            except (urllib.error.URLError, OSError):
                time.sleep(0.5)
        raise RuntimeError('示範 server 60 秒內沒有回應')

    def stop(self):
        if self.proc and self.proc.poll() is None:
            try:
                urllib.request.urlopen(self.base + '/__demo_stop', timeout=3).read()
                self.proc.wait(timeout=10)
            except Exception:
                self.proc.terminate()          # 只結束我們自己開的這個子行程
                self.proc.wait(timeout=10)
        if self.log:
            self.log.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ── HTTP ──
    def call(self, path, data=None, jar=None, headers=None, method=None):
        h = {'Origin': self.base, **(headers or {})}
        body = None
        if data is not None:
            body = json.dumps(data).encode('utf-8')
            h['Content-Type'] = 'application/json'
        req = urllib.request.Request(self.base + path, data=body, headers=h, method=method or ('POST' if data is not None else 'GET'))
        handlers = [NoRedirect()]
        if jar is not None:
            handlers.append(urllib.request.HTTPCookieProcessor(jar))
        opener = urllib.request.build_opener(*handlers)
        try:
            with opener.open(req, timeout=20) as r:
                return r.status, r.read().decode('utf-8', 'replace'), dict(r.headers)
        except urllib.error.HTTPError as e:
            with e:
                return e.code, e.read().decode('utf-8', 'replace'), dict(e.headers)

    def json(self, path, data=None, jar=None, headers=None):
        s, b, _ = self.call(path, data, jar, headers)
        try:
            return s, json.loads(b)
        except ValueError:
            return s, {'_raw': b}

    def login(self, who):
        jar = http.cookiejar.CookieJar()
        s, _, h = self.call(f'/enter?as={who}', jar=jar)
        return jar, s, h

    def db(self):
        con = sqlite3.connect(self.data / 'operations.db')
        con.row_factory = sqlite3.Row
        return con


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def signature_png(w=200, h=80):
    """簽名框用的假簽名（合法 PNG）。"""
    raw = b''.join(b'\x00' + bytes((x * 7 + y * 13) % 256 for x in range(w)) for y in range(h))

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 0, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))
    return 'data:image/png;base64,' + base64.b64encode(png).decode()
