"""安全：夥伴銀行帳戶不能從任何 GET API 漏給沒有 money 權限的人。

BankFieldsTest（test_demo_server.py）只看 /api/state；這裡把 server.py 裡所有 `path == '/api/...'`
的 GET 端點都打一遍（含常見查詢參數），客服排班（staff）與夥伴（worker）的回應都不能出現
其他夥伴的銀行帳號。端點清單直接從 server.py 讀，之後新增的端點會自動納入檢查。
"""
import re
import unittest

from _demo import APP, Demo

D = None
MARK = '7777-000-{:06d}'          # 每位夥伴一組可辨識的假帳號


def setUpModule():
    global D
    D = Demo().start()
    con = D.db()
    try:
        for i, (wid,) in enumerate(con.execute('SELECT id FROM workers ORDER BY id').fetchall(), 1):
            con.execute('UPDATE workers SET bank_account=? WHERE id=?', (MARK.format(i), wid))
        con.commit()
    finally:
        con.close()


def tearDownModule():
    if D:
        D.stop()


def get_paths():
    src = (APP / 'server.py').read_text(encoding='utf-8')
    return sorted(set(re.findall(r"path == '(/api/[^']*)'", src)))


class BankNoLeakTest(unittest.TestCase):
    def setUp(self):
        con = D.db()
        try:
            self.accounts = {r['id']: r['bank_account'] for r in con.execute('SELECT id,bank_account FROM workers')}
            self.order = con.execute('SELECT id FROM orders LIMIT 1').fetchone()[0]
        finally:
            con.close()

    def sweep(self, who, allowed=()):
        jar, _, _ = D.login(who)
        paths = get_paths()
        self.assertGreater(len(paths), 20)                               # 確認真的讀到端點清單
        leaks = []
        for p in paths:
            for qs in ('', '?id=wor-demo02', '?id=' + self.order, '?worker_id=wor-demo02'):
                s, body, _ = D.call(p + qs, jar=jar)
                for wid, acct in self.accounts.items():
                    if wid not in allowed and acct in body:
                        leaks.append((p + qs, s, wid))
        self.assertEqual(leaks, [])

    def test_admin_can_see(self):                                        # 對照組：管理員看得到，表示測試有意義
        jar, _, _ = D.login('admin')
        s, body, _ = D.call('/api/state', jar=jar)
        self.assertEqual(s, 200)
        self.assertTrue(all(a in body for a in self.accounts.values()))

    def test_staff_sees_no_bank_account(self):
        self.sweep('staff')

    def test_worker_sees_no_other_bank_account(self):
        self.sweep('worker', allowed=('wor-demo01',))                    # 示範夥伴帳號＝wor-demo01，自己的帳戶可以看


if __name__ == '__main__':
    unittest.main()
