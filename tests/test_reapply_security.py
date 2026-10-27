"""安全：知道某位夥伴的電話，不能用陌生 LINE 冒用他的身分重新應徵（進篩選、掛檔案）。

情境：夥伴 wor-demo02 以前被婉拒、目前暫停，系統設定「再應徵直接進篩選」（reapply_mode=screen）。
陌生 LINE 帳號填了同一支電話送出應徵 → 只能建「綁定待確認」，不能 screen、不能改 worker_files；
管理層核准綁定後才進篩選；按「不是本人」則擱置資料作廢。
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

from _demo import APP, NO_WINDOW, env_for, run_seed

SCENARIO = textwrap.dedent('''
    import json, sys, time
    sys.path.insert(0, sys.argv[1])
    decision = sys.argv[2]
    import core as c, integrations as ix, recruit, worker_portal as wp, line_bot
    c.initialize()
    con = c.connect()
    recruit.ensure(con)
    WID = 'wor-demo02'
    phone = con.execute('SELECT phone FROM workers WHERE id=?', (WID,)).fetchone()[0]
    ix.set_setting(con, 'reapply_mode', 'screen')
    con.execute("UPDATE workers SET status='paused' WHERE id=?", (WID,))
    con.execute("INSERT INTO interviews(id,worker_id,status,created_at,decided_at,note) VALUES('iv-old',?,'rejected','2026-01-01','2026-01-02','')", (WID,))
    UID = 'U-stranger-test'
    con.execute("INSERT INTO line_users(account,user_id,display_name) VALUES('demoshop',?,'陌生人')", (UID,))
    con.execute("INSERT INTO line_bind(code,kind,ref_id,expires,account) VALUES('Atok123','apply',?,?,'demoshop')", (UID, int(time.time()) + 3600))
    con.execute("INSERT INTO worker_files(id,worker_id,ref,kind,created_at) VALUES('wf-test',NULL,'apply:tok123','photo','2026-01-01')")
    con.commit()

    def snap():
        return {'interviews': con.execute('SELECT COUNT(*) FROM interviews WHERE worker_id=?', (WID,)).fetchone()[0],
                'screening': con.execute("SELECT COUNT(*) FROM interviews WHERE worker_id=? AND status='screening'", (WID,)).fetchone()[0],
                'file_owner': con.execute("SELECT worker_id FROM worker_files WHERE id='wf-test'").fetchone()[0],
                'bound': con.execute('SELECT worker_id FROM line_users WHERE account=? AND user_id=?', ('demoshop', UID)).fetchone()[0]}

    before = snap()
    with con:
        res = wp.apply(con, 'tok123', {'name': '冒用者', 'phone': phone})
    after_apply = snap()
    rid = con.execute("SELECT id FROM bind_requests WHERE user_id=? AND status='open'", (UID,)).fetchone()[0]
    pending = bool(ix.setting(con, f'reapply_pending:{rid}'))
    with con:
        line_bot.decide_bind(con, rid, decision == 'approve', '測試')
    after_decide = snap()
    print(json.dumps({'res': res, 'before': before, 'after_apply': after_apply, 'pending': pending, 'after_decide': after_decide,
                      'pending_after': bool(ix.setting(con, f'reapply_pending:{rid}'))}, ensure_ascii=False))
''')


class ReapplyImpersonationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix='dispatch-reapply-'))
        r = run_seed(self.tmp)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_scenario(self, decision):
        env = {**env_for(self.tmp), 'DISPATCH_NO_PUSH': '1', 'DISPATCH_QUIET_TEST': '1'}
        r = subprocess.run([sys.executable, '-c', SCENARIO, str(APP), decision], env=env, capture_output=True,
                           text=True, encoding='utf-8', timeout=120, creationflags=NO_WINDOW)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_stranger_with_same_phone_cannot_screen_or_attach_files(self):
        out = self.run_scenario('reject')
        self.assertEqual(out['res']['rescreen'], 'pending_bind')
        self.assertEqual(out['after_apply']['interviews'], out['before']['interviews'])      # 沒有觸發 screen
        self.assertEqual(out['after_apply']['screening'], 0)
        self.assertIsNone(out['after_apply']['file_owner'])                                   # 檔案沒有掛到既有夥伴名下
        self.assertIsNone(out['after_apply']['bound'])                                        # LINE 沒有被綁上
        self.assertTrue(out['pending'])
        # 管理層按「不是本人」：一樣不篩選、不掛檔案，擱置的資料作廢
        self.assertEqual(out['after_decide']['interviews'], out['before']['interviews'])
        self.assertIsNone(out['after_decide']['file_owner'])
        self.assertFalse(out['pending_after'])

    def test_screen_runs_only_after_bind_approved(self):
        out = self.run_scenario('approve')
        self.assertEqual(out['after_apply']['interviews'], out['before']['interviews'])
        self.assertIsNone(out['after_apply']['file_owner'])
        self.assertEqual(out['after_decide']['bound'], 'wor-demo02')
        self.assertEqual(out['after_decide']['screening'], 1)                                 # 核准後才進篩選
        self.assertEqual(out['after_decide']['file_owner'], 'wor-demo02')                     # 核准後才掛檔案
        self.assertFalse(out['pending_after'])


if __name__ == '__main__':
    unittest.main()
