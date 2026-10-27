import json
import pathlib
import shutil
import sqlite3
import tempfile
import unittest

from _demo import run_seed


class SeedTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix='dispatch-seed-'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_seed_builds_fake_data(self):
        r = run_seed(self.tmp)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        counts = json.loads(r.stdout.strip().splitlines()[-1].split('：', 1)[1])
        self.assertEqual(counts['customers'], 15)
        self.assertEqual(counts['workers'], 6)
        self.assertEqual(counts['users'], 4)
        self.assertGreater(counts['orders'], 0)
        con = sqlite3.connect(self.tmp / 'operations.db')
        try:
            self.assertEqual(con.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            names = [r[0] for r in con.execute('SELECT name FROM workers')]
            self.assertTrue(all('示範' in n for n in names), names)            # 夥伴全部是虛構示範資料
            phones = [r[0] for r in con.execute("SELECT phone FROM customers WHERE phone<>''")]
            self.assertTrue(all(p.startswith('0900-000-') for p in phones), phones)
            users = {r[0] for r in con.execute('SELECT username FROM users')}
            self.assertEqual(users, {'admin', 'staff', 'finance', 'worker'})
        finally:
            con.close()

    def test_reseed_keeps_old_db(self):
        self.assertEqual(run_seed(self.tmp).returncode, 0)
        r = run_seed(self.tmp)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(list(self.tmp.glob('_舊示範資料_*.db')), '舊的示範資料庫應改名保留，不應刪除')
        self.assertTrue((self.tmp / 'operations.db').exists())


if __name__ == '__main__':
    unittest.main()
