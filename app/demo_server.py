"""示範版啟動器：只在本機跑、封鎖所有對外連線、資料庫放在示範資料夾的 data\\。
用法：python demo_server.py           （Windows 想不跳視窗可用 pythonw；預設埠 5480，可用環境變數 DEMO_PORT 改）
      python  demo_server.py --stop   （停止示範 server）"""
import os, pathlib, socket, sys

HERE = pathlib.Path(__file__).resolve().parent
DEMO_PORT = int(os.environ.get('DEMO_PORT', '5480'))

os.environ['DISPATCH_NO_PUSH'] = '1'                       # 不連 LINE／LINE Pay／Google／推播
os.environ['DISPATCH_QUIET_TEST'] = '1'
os.environ['DISPATCH_AIB_LOCAL'] = '0'                     # 不叫本機 AI
os.environ.setdefault('DISPATCH_DATA', str(HERE.parent / 'data'))      # 測試可以改到暫存資料夾
os.environ['DISPATCH_PORT'] = str(DEMO_PORT)
os.environ.setdefault('DISPATCH_PUBLIC_HOSTS', 'demo-public.invalid')   # 要放上網示範時設成你的網域（例：demo.example.com）
os.environ['DISPATCH_SITE_HOSTS'] = 'demo-site.invalid'

# ── 網路防護：除了本機示範埠，其他連線一律拒絕（保證不會連到 LINE、Google、金流或任何外部服務）──
_ALLOWED = {('127.0.0.1', DEMO_PORT), ('localhost', DEMO_PORT)}
_orig_connect, _orig_connect_ex = socket.socket.connect, socket.socket.connect_ex

def _ok(addr):
    return isinstance(addr, tuple) and (str(addr[0]), int(addr[1])) in _ALLOWED

def _guard_connect(self, addr):
    if self.family in (socket.AF_INET, socket.AF_INET6) and not _ok(addr):
        raise ConnectionRefusedError(f'示範版已關閉對外連線：{addr[0] if isinstance(addr, tuple) else addr}')
    return _orig_connect(self, addr)

def _guard_connect_ex(self, addr):
    if self.family in (socket.AF_INET, socket.AF_INET6) and not _ok(addr):
        return 111
    return _orig_connect_ex(self, addr)

def _guard_getaddrinfo(host, *a, **k):
    if str(host) not in ('127.0.0.1', 'localhost', '::1', 'None', ''):
        raise socket.gaierror(f'示範版已關閉對外連線：{host}')
    return _orig_gai(host, *a, **k)

_orig_gai = socket.getaddrinfo
socket.socket.connect = _guard_connect
socket.socket.connect_ex = _guard_connect_ex
socket.getaddrinfo = _guard_getaddrinfo

_PROXY_HEADERS = ('Cf-Connecting-Ip', 'X-Forwarded-For', 'X-Real-Ip', 'Forwarded')

def _local_direct(h):
    """本機直連：來源 127.0.0.1、Host 是本機示範埠、而且沒有任何代理標頭（Tunnel 進來的請求來源也是 127.0.0.1，要靠這兩點擋）。"""
    host = (h.headers.get('Host') or '').lower()
    return (h.client_address[0] == '127.0.0.1' and host in (f'127.0.0.1:{DEMO_PORT}', f'localhost:{DEMO_PORT}')
            and not any(h.headers.get(k) for k in _PROXY_HEADERS))

DEMO_USERS = {'admin': '/', 'staff': '/', 'finance': '/', 'worker': '/wp/demo-portal-worker-01'}   # 帳號 → 進入後的頁面

def stop():
    import urllib.request
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{DEMO_PORT}/__demo_stop', timeout=3) as r:
            print(r.read().decode())
    except Exception as e:
        print('示範 server 沒有在跑或已停止：', e)

def run():
    sys.path.insert(0, str(HERE))
    os.chdir(HERE)
    logdir = pathlib.Path(os.environ['DISPATCH_DATA']) / 'logs'; logdir.mkdir(parents=True, exist_ok=True)
    if sys.stdout is None or 'pythonw' in sys.executable.lower():       # pythonw 沒有主控台：輸出寫到 log
        f = open(logdir / 'demo_server.log', 'a', encoding='utf-8', buffering=1)
        sys.stdout = sys.stderr = f
    probe = socket.socket()
    if _orig_connect_ex(probe, ('127.0.0.1', DEMO_PORT)) == 0:
        print(f'埠 {DEMO_PORT} 已被占用（示範可能已經在跑），不重複啟動'); probe.close(); return
    probe.close()
    import server
    _orig_get = server.Handler.do_GET

    def do_GET(self):                                   # 停止示範：只接受本機
        if self.path.startswith('/__demo_stop'):             # 停止示範：只接受「本機直連」（經過 Cloudflare Tunnel／反向代理的一律拒絕）
            if not _local_direct(self):
                return self.send_bytes('只能在本機停止示範 server'.encode('utf-8'), 'text/plain; charset=utf-8', 403)
            self.send_response(200); self.send_header('Content-Type', 'text/plain; charset=utf-8'); self.end_headers()
            self.wfile.write('示範 server 已停止'.encode('utf-8')); self.wfile.flush()
            import threading
            threading.Timer(0.3, lambda: os._exit(0)).start(); return
        path = self.path.split('?')[0]
        if path == '/enter':                            # 示範免登入：直接以示範帳號進入（?as=admin／staff／finance／worker）
            import contextlib, urllib.parse, accounts as acc, core
            who = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get('as', ['admin'])[0]
            who = who if who in DEMO_USERS else 'admin'
            with server.LOCK, contextlib.closing(core.connect()) as con, con:
                u = con.execute('SELECT * FROM users WHERE username=? AND active=1', (who,)).fetchone()
                if not u:
                    return self.send_bytes('示範帳號不存在，請先執行 python app/seed_demo.py 建立示範資料'.encode('utf-8'), 'text/plain; charset=utf-8', 503)
                con.execute('UPDATE users SET must_change=0,failed=0,locked_until=0 WHERE id=?', (u['id'],))
                token, life = acc.new_session(con, dict(u), self.ip())
            return self.send_bytes(b'', 'text/plain', 302, {'Location': DEMO_USERS[who], 'Set-Cookie': self.cookie_header(token, life)})
        if path in ('/', '/index.html'):                # 沒登入就自動以管理員進入，不出現登入畫面
            import contextlib, accounts as acc, core
            t = self.token()
            with contextlib.closing(core.connect()) as con:
                ok = bool(t and acc.session_user(con, t))
            if not ok:                                  # 第一次來：先看說明頁（按「直接試玩」才進系統）
                return self.send_bytes((HERE / 'demo_intro.html').read_bytes(), 'text/html; charset=utf-8')
        if path == '/intro':
            return self.send_bytes((HERE / 'demo_intro.html').read_bytes(), 'text/html; charset=utf-8')
        return _orig_get(self)
    server.Handler.do_GET = do_GET
    server.main()

if __name__ == '__main__':
    stop() if '--stop' in sys.argv else run()
