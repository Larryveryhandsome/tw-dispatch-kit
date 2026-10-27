"""自架模式：create_admin 建第一個管理員、server.py 用帳密登入。"""
import http.cookiejar
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

from _demo import APP, NO_WINDOW, env_for, free_port


def server_log(tmp):
    p = tmp / 'server.log'
    return p.read_text(encoding='utf-8', errors='replace')[-3000:] if p.exists() else ''


class SelfHostTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp(prefix='dispatch-selfhost-'))
        cls.env = {**env_for(cls.tmp / 'data'), 'DISPATCH_NO_PUSH': '1', 'DISPATCH_QUIET_TEST': '1'}
        cls.port = free_port()
        cls.base = f'http://127.0.0.1:{cls.port}'

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def admin(self, user, pw):
        return subprocess.run([sys.executable, str(APP / 'create_admin.py'), user, '老闆'], env={**self.env, 'DISPATCH_ADMIN_PASSWORD': pw},
                              capture_output=True, text=True, encoding='utf-8', timeout=60, creationflags=NO_WINDOW)

    def test_weak_password_rejected(self):
        r = self.admin('boss2', '12345678901')                 # 只有數字
        self.assertNotEqual(r.returncode, 0)
        r = self.admin('boss2', 'short')
        self.assertNotEqual(r.returncode, 0)

    def test_create_admin_and_login(self):
        r = self.admin('boss', 'test-pass-12345')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        env = {**self.env, 'DISPATCH_PORT': str(self.port)}
        log = open(self.tmp / 'server.log', 'w', encoding='utf-8')
        proc = subprocess.Popen([sys.executable, str(APP / 'server.py')], env=env, stdout=log, stderr=subprocess.STDOUT, creationflags=NO_WINDOW)
        try:
            for _ in range(60):
                try:
                    urllib.request.urlopen(self.base + '/health', timeout=2).close()
                    break
                except OSError:
                    time.sleep(0.5)
            jar = http.cookiejar.CookieJar()
            op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

            def login(pw):
                req = urllib.request.Request(self.base + '/api/login', data=json.dumps({'username': 'boss', 'password': pw}).encode(),
                                             headers={'Content-Type': 'application/json', 'Origin': self.base}, method='POST')
                try:
                    with op.open(req, timeout=20) as res:
                        return res.status
                except urllib.error.HTTPError as e:
                    with e:
                        return e.code
            self.assertEqual(login('wrong-pass-123'), 403)
            self.assertEqual(login('test-pass-12345'), 200)
            # server 是先回應、再提交交易：登入回應後馬上打下一個請求，偶爾會比 commit 早到（CI 上觀察到），稍等重試
            me = None
            for _ in range(20):
                try:
                    with op.open(self.base + '/api/me', timeout=20) as res:
                        me = json.loads(res.read())
                        break
                except urllib.error.HTTPError as e:
                    e.close()
                    time.sleep(0.25)
            self.assertIsNotNone(me, server_log(self.tmp))
            self.assertEqual(me['role'], 'admin')
        finally:
            proc.terminate()                   # 只結束這個測試自己開的子行程
            proc.wait(timeout=10)
            log.close()


if __name__ == '__main__':
    unittest.main()
