"""POST 要先提交交易、再送出回應。

以前交易區塊裡的 `return self.respond(...)` 在提交前就把回應送出去，客戶端緊接著的下一個請求
偶爾會讀到還沒提交的狀態（CI 上看過：剛送出的報價單馬上打開回 400「找不到這張報價單」）。
這裡讓示範 server 每次送出回應後多等 0.3 秒（模擬慢機器，剛好落在舊寫法「已回應、未提交」的空窗），
舊寫法每次都會失敗，新寫法不受影響。
"""
import datetime
import sys
import textwrap
import unittest

from _demo import APP, Demo
from test_demo_server import QUOTE_FORM

SLOW = textwrap.dedent('''
    import sys, time
    app = sys.argv[1]
    sys.argv = [app + '/demo_server.py']
    sys.path.insert(0, app)
    import demo_server            # 先讓示範版設定好環境、擋外連
    import server
    _orig = server.Handler.send_bytes
    def slow(self, *a, **k):
        _orig(self, *a, **k)
        time.sleep(0.3)
    server.Handler.send_bytes = slow
    demo_server.run()
''')

D = None


def setUpModule():
    global D
    D = Demo()
    D.cmd = [sys.executable, '-c', SLOW, str(APP)]
    D.start()


def tearDownModule():
    if D:
        D.stop()


class CommitBeforeRespondTest(unittest.TestCase):
    def test_new_quote_readable_right_away(self):
        date = (datetime.date.today() + datetime.timedelta(days=5)).isoformat()
        for _ in range(3):
            s, q = D.json('/api/public/quote', {**QUOTE_FORM, 'date': date})
            self.assertEqual(s, 200, q)
            s, v = D.json('/api/public/quote/' + q['token'])
            self.assertEqual(s, 200, v)                                   # 舊寫法：400 找不到這張報價單

    def test_logged_in_post_visible_right_away(self):
        jar, _, _ = D.login('admin')
        s, me = D.json('/api/me', jar=jar)
        self.assertEqual(s, 200, me)
        s, out = D.json('/api/tour', {'key': 'commit-check'}, jar=jar, headers={'X-CSRF-Token': me['csrf']})
        self.assertEqual(s, 200, out)
        s, st = D.json('/api/state', jar=jar)
        self.assertEqual(s, 200)
        self.assertIn('commit-check', str(st.get('tours')))

    def test_failed_post_still_returns_error(self):                      # 交易回復時要回錯誤，不能送出暫存的成功回應
        s, e = D.json('/api/public/quote', {**QUOTE_FORM, 'date': datetime.date.today().isoformat()})
        self.assertEqual(s, 400, e)
        self.assertIn('error', e)


if __name__ == '__main__':
    unittest.main()
