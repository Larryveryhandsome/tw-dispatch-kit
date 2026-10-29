"""示範 server 端到端：真的啟動 server、用 HTTP 打。"""
import datetime
import subprocess
import sys
import textwrap
import time
import unittest

from _demo import APP, NO_WINDOW, Demo, env_for, signature_png

D = None


def setUpModule():
    global D
    D = Demo().start()


def tearDownModule():
    if D:
        D.stop()


def future(days=5):
    return (datetime.date.today() + datetime.timedelta(days=days)).isoformat()


QUOTE_FORM = {'account': 'demoshop', 'space': 'home', 'condition': 'regular', 'size': '25', 'rooms': '2', 'baths': '1',
              'name': '測試小姐', 'phone': '0900-000-999', 'address': '宜蘭縣宜蘭市示範路 1 號', 'area': '宜蘭縣宜蘭市',
              'slot': '09:00–13:00', 'photo_via': 'human', 'tools': 'full', 'consent': True}


class PagesTest(unittest.TestCase):
    def test_public_pages_200(self):
        for path in ('/intro', '/home', '/book', '/mall', '/privacy', '/join', '/manifest.webmanifest', '/style.css', '/app.js'):
            with self.subTest(path=path):
                s, body, _ = D.call(path)
                self.assertEqual(s, 200, body[:200])

    def test_first_visit_shows_intro_with_ad(self):
        s, body, _ = D.call('/')
        self.assertEqual(s, 200)
        self.assertIn('0928-880-392', body)                     # 客製化廣告要保留

    def test_demo_banner_keeps_ad(self):
        s, body, _ = D.call('/demo-banner.js')
        self.assertEqual(s, 200)
        self.assertIn('0928-880-392', body)
        self.assertIn('林其衞', body)

    def test_logged_in_pages_200(self):
        jar, _, _ = D.login('admin')
        for path in ('/', '/api/state', '/api/me', '/api/quotes', '/api/billing', '/api/brands'):
            with self.subTest(path=path):
                s, body, _ = D.call(path, jar=jar)
                self.assertEqual(s, 200, body[:200])

    def test_worker_portal_200(self):
        s, body, _ = D.call('/wp/demo-portal-worker-01')
        self.assertEqual(s, 200, body[:200])

    def test_unknown_page_not_served(self):
        s, _, _ = D.call('/no-such-page-xyz')
        self.assertIn(s, (401, 403, 404))                            # 沒登入：不回 200


class EnterTest(unittest.TestCase):
    def test_enter_each_role(self):
        for who, role in (('admin', 'admin'), ('staff', 'staff'), ('finance', 'finance'), ('worker', 'cleaner')):
            with self.subTest(who=who):
                jar, s, h = D.login(who)
                self.assertEqual(s, 302)
                self.assertIn('Set-Cookie', h)
                s, me = D.json('/api/me', jar=jar)
                self.assertEqual(s, 200)
                self.assertEqual(me['role'], role)

    def test_enter_unknown_role_falls_back_to_admin(self):
        jar, s, _ = D.login('../../etc')
        self.assertEqual(s, 302)
        self.assertEqual(D.json('/api/me', jar=jar)[1]['username'], 'admin')

    def test_api_without_login_refused(self):
        s, body = D.json('/api/state')
        self.assertIn(s, (401, 403), body)


class StopGuardTest(unittest.TestCase):
    def test_stop_refused_through_proxy(self):
        for headers in ({'Host': 'demo-public.invalid'}, {'Cf-Connecting-Ip': '203.0.113.9'},
                        {'X-Forwarded-For': '203.0.113.9'}, {'Host': f'evil.example.com:{D.port}'}):
            with self.subTest(headers=headers):
                s, body, _ = D.call('/__demo_stop', headers=headers)
                self.assertEqual(s, 403, body)
        time.sleep(0.6)
        self.assertIsNone(D.proc.poll(), '被擋下的停止請求不能讓 server 停掉')
        self.assertEqual(D.call('/intro')[0], 200)


class OutboundBlockedTest(unittest.TestCase):
    def test_demo_blocks_all_outbound(self):
        code = textwrap.dedent('''
            import socket, sys, urllib.request
            sys.path.insert(0, sys.argv[1])
            import demo_server
            out = []
            try:
                urllib.request.urlopen('https://api.line.me/v2/bot/info', timeout=5); out.append('line-open')
            except Exception as e:
                out.append('line-blocked' if '示範版已關閉對外連線' in str(e) or isinstance(e, OSError) else 'line-other:' + repr(e))
            s = socket.socket()
            try:
                s.connect(('1.1.1.1', 443)); out.append('ip-open')
            except ConnectionRefusedError as e:
                out.append('ip-blocked' if '示範版已關閉對外連線' in str(e) else 'ip-refused-other')
            print(' '.join(out))
        ''')
        r = subprocess.run([sys.executable, '-c', code, str(APP)], env=env_for(D.tmp / 'probe'), capture_output=True,
                           text=True, encoding='utf-8', timeout=60, creationflags=NO_WINDOW)
        self.assertEqual(r.stdout.strip(), 'line-blocked ip-blocked', r.stdout + r.stderr)


class QuoteFlowTest(unittest.TestCase):
    def test_estimate(self):
        s, e = D.json('/api/public/estimate', QUOTE_FORM)
        self.assertEqual(s, 200, e)
        self.assertEqual(e['service_type'], '居家清潔')
        self.assertGreater(e['total'], 0)
        self.assertIn('原則上', e['note'])                       # 初估要有保護語
        self.assertFalse([k for k in e if k.startswith('internal_')], '內部初估不能給客戶看')

    def test_estimate_requires_origin(self):
        s, body, _ = D.call('/api/public/estimate', QUOTE_FORM, headers={'Origin': 'https://evil.example.com'})
        self.assertEqual(s, 403, body)

    def test_quote_requires_consent(self):
        s, e = D.json('/api/public/quote', {**QUOTE_FORM, 'date': future(), 'consent': False})
        self.assertEqual(s, 400)
        self.assertIn('個人資料', e['error'])

    def test_quote_requires_address(self):
        s, e = D.json('/api/public/quote', {**QUOTE_FORM, 'date': future(), 'address': ''})
        self.assertEqual(s, 400)

    def test_quote_rejects_past_date(self):
        s, e = D.json('/api/public/quote', {**QUOTE_FORM, 'date': datetime.date.today().isoformat()})
        self.assertEqual(s, 400, e)

    def test_quote_created_and_waits_for_review(self):
        s, q = D.json('/api/public/quote', {**QUOTE_FORM, 'date': future()})
        self.assertEqual(s, 200, q)
        self.assertTrue(q['token'])
        s, v = D.json('/api/public/quote/' + q['token'])
        self.assertEqual(s, 200)
        self.assertNotEqual(v['stage'], 'sent')                   # 主管還沒確認：客戶還不能簽
        jar, _, _ = D.login('admin')
        s, lst = D.json('/api/quotes', jar=jar)
        self.assertIn(q['no'], [x['id'] for x in lst['quotes']])

    def test_sign_sent_quote_creates_order(self):
        con = D.db()
        before = con.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
        con.close()
        s, v = D.json('/api/public/quote/demo-quote-0001')
        self.assertEqual(s, 200)
        self.assertEqual(v['stage'], 'sent')
        sign = {'name': '測試簽收', 'agree': True, 'terms_digest': v['terms_digest'], 'signature': signature_png(), 'tools': 'full',
                'level': 1, 'dirt': 'light', 'want_freq': '單次', 'want_hours': '4'}
        s, e = D.json('/api/public/quote/demo-quote-0001/sign', {**sign, 'terms_digest': 'tampered'})
        self.assertEqual(s, 400, e)                                # 條款摘要不符不能簽
        s, e = D.json('/api/public/quote/demo-quote-0001/sign', {**sign, 'signature': ''})
        self.assertEqual(s, 400, e)                                # 沒簽名不能簽
        s, e = D.json('/api/public/quote/demo-quote-0001/sign', sign)
        self.assertEqual(s, 200, e)
        s, e2 = D.json('/api/public/quote/demo-quote-0001/sign', sign)
        self.assertEqual(s, 200, e2)
        self.assertTrue(e2.get('already'))                         # 重複送出不重複建單
        con = D.db()
        after = con.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
        con.close()
        self.assertEqual(after, before + 1)


class PermissionTest(unittest.TestCase):
    def setUp(self):
        self.jar, _, _ = D.login('worker')

    def test_worker_sees_only_own_jobs(self):
        s, st = D.json('/api/state', jar=self.jar)
        self.assertEqual(s, 200)
        self.assertEqual(st['role'], 'cleaner')
        self.assertNotIn('customers', st)                          # 夥伴拿不到客戶清單
        self.assertNotIn('workers', st)                            # 也拿不到其他夥伴資料
        self.assertTrue(st['mine'])
        con = D.db()
        try:
            for job in st['mine']:
                owner = con.execute('SELECT worker_id FROM assignments WHERE id=?', (job['assignment_id'],)).fetchone()[0]
                self.assertEqual(owner, 'wor-demo01', job['assignment_id'])
        finally:
            con.close()

    def test_worker_blocked_from_admin_apis(self):
        for path in ('/api/quotes', '/api/billing', '/api/ledger', '/api/chats', '/api/brands', '/api/payhist'):
            with self.subTest(path=path):
                s, _, _ = D.call(path, jar=self.jar)
                self.assertEqual(s, 403)

    def test_worker_cannot_confirm_quote(self):
        s, me = D.json('/api/me', jar=self.jar)
        s, body, _ = D.call('/api/quote/confirm', {'token': 'demo-quote-0002'}, jar=self.jar, headers={'X-CSRF-Token': me['csrf']})
        self.assertEqual(s, 403, body)

    def test_post_without_csrf_refused(self):
        jar, _, _ = D.login('admin')
        s, body, _ = D.call('/api/quote/confirm', {'token': 'demo-quote-0002'}, jar=jar)
        self.assertIn(s, (400, 403), body)


class BankFieldsTest(unittest.TestCase):
    """夥伴的銀行帳戶只有 money 權限（管理員、帳務）看得到、改得到；客服排班（staff）不行。"""
    BANK = ('bank_name', 'bank_account', 'bank_holder', 'payout_cycle')

    def test_staff_cannot_see_bank_fields(self):
        jar, _, _ = D.login('staff')
        s, st = D.json('/api/state', jar=jar)
        self.assertEqual(s, 200)
        self.assertTrue(st['workers'])
        for w in st['workers']:
            for k in self.BANK + ('rate',):
                self.assertIsNone(w.get(k), f"{w['id']} {k}")
        jar, _, _ = D.login('admin')
        s, st = D.json('/api/state', jar=jar)
        self.assertTrue(any(w.get('bank_account') for w in st['workers']))      # 管理員看得到（確認測試有意義）

    def test_staff_cannot_change_bank_fields(self):
        con = D.db()
        before = dict(con.execute('SELECT * FROM workers WHERE id=?', ('wor-demo03',)).fetchone())
        con.close()
        jar, _, _ = D.login('staff')
        s, me = D.json('/api/me', jar=jar)
        payload = {'id': 'wor-demo03', 'version': before['version'], 'name': before['name'], 'notes': 'staff 改備註',
                   'bank_name': '惡意銀行', 'bank_account': '9999-999-999999', 'bank_holder': '別人', 'payout_cycle': 'week'}
        s, out = D.json('/api/save/workers', payload, jar=jar, headers={'X-CSRF-Token': me['csrf']})
        self.assertEqual(s, 200, out)
        for k in self.BANK:
            self.assertIsNone(out.get(k), k)                                  # 回應也不帶出銀行欄位
        con = D.db()
        after = dict(con.execute('SELECT * FROM workers WHERE id=?', ('wor-demo03',)).fetchone())
        con.close()
        self.assertEqual(after['notes'], 'staff 改備註')                       # 一般欄位照常可改
        for k in self.BANK:
            self.assertEqual(after[k], before[k], k)                          # 銀行欄位沒被改


class ZZStopTest(unittest.TestCase):
    """最後跑：本機直連可以停掉示範 server。"""

    def test_local_stop(self):
        s, body, _ = D.call('/__demo_stop')
        self.assertEqual(s, 200, body)
        D.proc.wait(timeout=10)
        self.assertIsNotNone(D.proc.poll())


if __name__ == '__main__':
    unittest.main()
