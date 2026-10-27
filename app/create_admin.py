"""自架用：建立（或重設）第一個管理員帳號。

用法：python app/create_admin.py <帳號> [顯示名稱]
密碼會在終端機輸入（不顯示、不寫進指令紀錄）；管理員密碼至少 10 碼、不能只有數字。
資料庫位置照環境變數 DISPATCH_DATA（預設 app/data）。"""
import getpass
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import accounts as acc  # noqa: E402
import core  # noqa: E402


def create(username, name, pw):
    username = (username or '').strip()
    if not re.fullmatch(r'[A-Za-z0-9_.-]{3,30}', username):
        raise ValueError('帳號只能用英文、數字、底線、點、減號，3～30 個字')
    acc.validate_pw(pw, 'admin')
    core.initialize()
    con = core.connect()
    try:
        with con:
            row = con.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()
            if row:
                con.execute('UPDATE users SET pw=?,role=?,active=1,must_change=0,failed=0,locked_until=0,pw_set_at=? WHERE id=?',
                            (acc.hash_pw(pw), 'admin', int(time.time()), row[0]))
                return '已重設管理員密碼：' + username
            con.execute('INSERT INTO users(id,username,name,pw,role,active,must_change,pw_set_at) VALUES(?,?,?,?,?,1,0,?)',
                        (core.uid('u'), username, name or username, acc.hash_pw(pw), 'admin', int(time.time())))
            return '已建立管理員：' + username
    finally:
        con.close()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    pw = os.environ.get('DISPATCH_ADMIN_PASSWORD') or getpass.getpass('設定密碼（至少 10 碼）：')
    if not os.environ.get('DISPATCH_ADMIN_PASSWORD') and pw != getpass.getpass('再輸入一次：'):
        print('兩次密碼不一樣')
        return 1
    print(create(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else '', pw))
    return 0


if __name__ == '__main__':
    sys.exit(main())
