"""建立全新示範資料庫，塞入「虛構」假資料（客戶、夥伴、工單、估價單、月結）。
所有姓名、電話（0900-000-xxx）、地址（示範路）都是編的，不對應任何真實的人。
用法：python seed_demo.py        （舊的示範資料庫會改名保留在 data\\ 底下，不會刪）"""
import datetime as dt, json, os, pathlib, random, sys, time

HERE = pathlib.Path(__file__).resolve().parent
os.environ['DISPATCH_NO_PUSH'] = '1'
os.environ['DISPATCH_QUIET_TEST'] = '1'
os.environ.setdefault('DISPATCH_DATA', str(HERE.parent / 'data'))
sys.path.insert(0, str(HERE))
import demo_server  # noqa: F401  （載入網路防護：建資料過程也不會連外）
import core as c
import accounts as acc

random.seed(20261027)
DATA = pathlib.Path(os.environ['DISPATCH_DATA']); DATA.mkdir(parents=True, exist_ok=True)
db = DATA / 'operations.db'
if db.exists():
    stamp = time.strftime('%Y%m%d_%H%M%S')
    for suf in ('', '-wal', '-shm'):
        p = pathlib.Path(str(db) + suf)
        if p.exists(): p.rename(DATA / f'_舊示範資料_{stamp}.db{suf}')

c.initialize()
TODAY = dt.datetime.now(c.TZ).date()
con = c.connect()
c.CTX.actor = '示範資料'
cur = con.cursor()

def ins(table, row):
    cols = ','.join(row); q = ','.join('?' * len(row))
    cur.execute(f'INSERT INTO {table}({cols}) VALUES({q})', tuple(row.values()))
    return row.get('id')

# ── 帳號 ──
def user(uid, username, name, role, worker_id=None):
    ins('users', {'id': uid, 'username': username, 'name': name, 'pw': acc.hash_pw('demo1234'), 'role': role,
                  'worker_id': worker_id, 'active': 1, 'must_change': 0, 'pw_set_at': int(time.time())})

# ── 夥伴（6 位）──
WORKERS = [('林小雯', '宜蘭縣宜蘭市、宜蘭縣礁溪鄉', '居家清潔、廚房深層'), ('陳美玉', '宜蘭縣羅東鎮、宜蘭縣五結鄉', '居家清潔、民宿退房'),
           ('黃雅芬', '宜蘭縣宜蘭市、宜蘭縣員山鄉', '辦公室清潔、玻璃'), ('張淑華', '宜蘭縣羅東鎮、宜蘭縣冬山鄉', '居家清潔、整理收納'),
           ('李佩君', '宜蘭縣礁溪鄉、宜蘭縣頭城鎮', '民宿退房、布品更換'), ('吳家豪', '宜蘭縣全區', '裝潢後清潔、高處玻璃')]
wids = []
for i, (n, rg, sk) in enumerate(WORKERS, 1):
    wid = f'wor-demo{i:02d}'
    ins('workers', {'id': wid, 'name': n + '（示範）', 'phone': f'0900-000-{100 + i:03d}', 'regions': rg, 'skills': sk, 'rate': str(random.choice([220, 230, 250, 260])),
                    'status': 'active', 'notes': '示範用虛構夥伴', 'portal_token': f'demo-portal-worker-{i:02d}', 'bank_name': '示範銀行',
                    'bank_account': '0000-000-000000', 'bank_holder': n, 'payout_cycle': 'month'})
    wids.append(wid)

user('u-demo-admin', 'admin', '示範管理員', 'admin')
user('u-demo-staff', 'staff', '示範客服', 'staff')
user('u-demo-finance', 'finance', '示範帳務', 'finance')
user('u-demo-worker', 'worker', '林小雯（示範）', 'cleaner', wids[0])

# ── 客戶（15 位）＋ 服務地點 ──
CUSTOMERS = [('王雅琪', '家庭', '宜蘭市', 'before'), ('陳志明', '家庭', '羅東鎮', 'before'), ('晨光民宿（示範）', '民宿', '礁溪鄉', 'month'),
             ('李宛蓉', '家庭', '宜蘭市', 'after'), ('森林咖啡（示範）', '商業空間', '羅東鎮', 'month'), ('周品妤', '家庭', '五結鄉', 'before'),
             ('海風民宿（示範）', '民宿', '頭城鎮', 'month'), ('蔡明哲', '家庭', '員山鄉', 'before'), ('示範牙醫診所', '商業空間', '宜蘭市', 'month'),
             ('許靜宜', '家庭', '冬山鄉', 'after'), ('鄭家瑋', '家庭', '羅東鎮', 'before'), ('小日子工作室（示範）', '辦公室', '宜蘭市', 'month'),
             ('謝佳穎', '家庭', '礁溪鄉', 'before'), ('林俊宏', '家庭', '宜蘭市', 'deposit'), ('楊惠如', '家庭', '五結鄉', 'before')]
custs = []
for i, (n, kind, area, pay) in enumerate(CUSTOMERS, 1):
    cid = f'cus-demo{i:02d}'
    nm = n if '示範' in n else n + '（示範）'
    ins('customers', {'id': cid, 'name': nm, 'phone': f'0900-000-{i:03d}', 'status': 'active', 'line_account': 'demoshop',
                      'notes': f'示範用虛構客戶（{kind}）', 'code': f'D{i:03d}', 'channel': 'DEMO', 'pay_method': pay,
                      'billing_rule': '月結' if pay == 'month' else ''})
    sid = f'sit-demo{i:02d}'
    stype = {'家庭': '居家清潔', '民宿': '民宿退房清潔', '商業空間': '商業空間清潔', '辦公室': '辦公室清潔'}[kind]
    ins('sites', {'id': sid, 'customer_id': cid, 'name': f'{nm.replace("（示範）", "")}{"家" if kind == "家庭" else ""}',
                  'address': f'宜蘭縣{area}示範路 {10 + i * 3} 號（虛構地址）', 'service_type': stype, 'area': area,
                  'checklist': '浴室水垢\n廚房油汙\n全室吸拖' if kind == '家庭' else '垃圾清運\n地板拖洗\n玻璃擦拭',
                  'entry_mode': 'home' if kind == '家庭' else 'key', 'rate': '', 'notes': '示範案場'})
    custs.append((cid, sid, nm, stype, pay))

# ── 工單：過去 14 天（完成）、未來 14 天（已排定／待派工）＋ 9 月份月結客戶的工單 ──
SLOTS = [('09:00', '12:00', 3), ('09:00', '13:00', 4), ('13:30', '16:30', 3), ('14:00', '17:00', 3), ('08:30', '11:30', 3)]
orders = []
def make_order(day, ci, slot, status, workers_n=1, note=''):
    cid, sid, nm, stype, pay = custs[ci]
    st, en, hrs = slot
    oid = f'ord-demo{len(orders) + 1:03d}'
    amt = (hrs * 650 * workers_n + random.choice([0, 200, 400])) * 100           # 金額單位：分
    row = {'id': oid, 'site_id': sid, 'customer_id': cid, 'title': f'{stype}｜{nm.replace("（示範）", "")}', 'date': day.isoformat(),
           'start': st, 'end': en, 'required_workers': workers_n, 'status': status, 'billing_mode': 'fixed', 'approved_amount': amt,
           'review_note': '示範工單：客戶已確認時間', 'customer_confirmed': 1, 'notes': note, 'source': 'demo', 'created_at': c.now()}
    if status == 'completed':
        row.update({'actual_start': st, 'actual_end': en, 'confirmed_at': c.now(), 'completed_at': f'{day.isoformat()}T{en}:00+08:00',
                    'acceptance': 'accepted', 'charge_approved': 1, 'approval_note': '依報價金額', 'rating': random.choice([5, 5, 5, 4])})
    elif status == 'confirmed':
        row['confirmed_at'] = c.now()
    ins('orders', row)
    picked = random.sample(wids, workers_n) if status != 'review' else []
    for w in picked:
        aid = f'asg-{oid[4:]}-{w[-2:]}'
        rate = cur.execute('SELECT rate FROM workers WHERE id=?', (w,)).fetchone()[0]
        a = {'id': aid, 'order_id': oid, 'worker_id': w, 'status': 'accepted', 'pay_mode': 'hourly', 'rate': rate,
             'work_token': f'demo-work-{oid[4:]}-{w[-2:]}'}
        if status == 'completed':
            a['approved_minutes'] = hrs * 60
            a['amount'] = int(rate) * hrs * 100
        ins('assignments', a)
        if status == 'completed':
            cur.execute('INSERT INTO timesheets(id,assignment_id,start,end,pause,minutes,notes) VALUES(?,?,?,?,?,?,?)',
                        (c.uid('ts'), aid, st, en, 0, hrs * 60, '示範工時'))
    if status == 'completed':
        cur.execute('INSERT INTO service_reports(id,order_id,notes,customer_confirmed) VALUES(?,?,?,?)',
                    (c.uid('rpt'), oid, '已完成浴室、廚房、全室吸拖；客戶現場驗收 OK（示範）', 1))
    orders.append((oid, ci, day, status, amt))
    return oid

for d in range(-14, 15):
    day = TODAY + dt.timedelta(days=d)
    if day.weekday() == 6:                  # 週日休息
        continue
    for k in range(random.choice([1, 2, 2, 3])):
        ci = random.randrange(len(custs))
        slot = random.choice(SLOTS)
        n = 2 if custs[ci][3] in ('民宿退房清潔', '商業空間清潔') and random.random() < .5 else 1
        if d < 0:
            st = 'completed'
        elif d == 0:
            st = 'confirmed'
        else:
            st = random.choices(['confirmed', 'review'], [0.75, 0.25])[0]
        make_order(day, ci, slot, st, n)

# 9 月份：月結客戶每週一次（做為「上個月已收款」的月結示範）
MONTHLY = [i for i, x in enumerate(custs) if x[4] == 'month']
first = TODAY.replace(day=1)
prev_month = (first - dt.timedelta(days=1)).replace(day=1)
for ci in MONTHLY:
    for wk in range(4):
        make_order(prev_month + dt.timedelta(days=2 + wk * 7 + ci % 3), ci, SLOTS[0], 'completed', 1)

# ── 月結帳單：上個月（已核定＋已收款）、本月（草稿）──
def invoice(ci, period, status, paid):
    cid = custs[ci][0]
    ol = [o for o in orders if o[1] == ci and o[3] == 'completed' and o[2].strftime('%Y-%m') == period]
    if not ol: return
    iid = f'inv-demo-{period}-{ci:02d}'
    y, m = map(int, period.split('-'))
    due = (dt.date(y + m // 12, m % 12 + 1, 10)).isoformat()
    ins('invoices', {'id': iid, 'customer_id': cid, 'period': period, 'due_date': due, 'status': status, 'notes': '示範月結帳單',
                     'issued_at': c.now() if status == 'issued' else ''})
    total = 0
    for oid, _, day, _, amt in ol:
        ins('invoice_lines', {'id': c.uid('ln'), 'invoice_id': iid, 'order_id': oid, 'description': f'{day.isoformat()} {custs[ci][3]}', 'amount': amt}); total += amt
    if paid:
        ins('payments', {'id': c.uid('pay'), 'invoice_id': iid, 'amount': total, 'date': (dt.date(y + m // 12, m % 12 + 1, 5)).isoformat(),
                         'method': '轉帳', 'reference': '示範匯款末五碼 00000', 'request_key': c.uid('req')})

for ci in MONTHLY:
    invoice(ci, prev_month.strftime('%Y-%m'), 'issued', True)
    invoice(ci, TODAY.strftime('%Y-%m'), 'draft', False)

# ── 夥伴月結（上個月已發薪）──
for w in wids:
    al = cur.execute("SELECT a.id,a.amount FROM assignments a JOIN orders o ON o.id=a.order_id WHERE a.worker_id=? AND o.status='completed' AND o.date LIKE ?",
                     (w, prev_month.strftime('%Y-%m') + '%')).fetchall()
    if not al: continue
    sid_ = f'set-demo-{w[-2:]}'
    ins('settlements', {'id': sid_, 'worker_id': w, 'period': prev_month.strftime('%Y-%m'), 'status': 'paid', 'paid_at': c.now(), 'reference': '示範轉帳'})
    for aid, amt in al:
        ins('settlement_lines', {'id': c.uid('sl'), 'settlement_id': sid_, 'assignment_id': aid, 'amount': amt or 0})

con.commit()

# ── 估價單（走系統正式的估價流程）──
import booking
QUOTES = [('home', 'regular', '25', '2', '宜蘭縣宜蘭市示範路 88 號', '徐小姐（示範）', '0900-000-201'),
          ('home', 'deep', '35', '2', '宜蘭縣羅東鎮示範路 120 號', '江先生（示範）', '0900-000-202'),
          ('home', 'moving', '18', '1', '宜蘭縣礁溪鄉示範路 7 號', '高小姐（示範）', '0900-000-203'),
          ('home', 'regular', '40', '3', '宜蘭縣五結鄉示範路 56 號', '彭先生（示範）', '0900-000-204')]
qn = 0
for i, (space, cond, size, baths, addr, name, phone) in enumerate(QUOTES):
    try:
        with con:
            booking.create_quote(con, {'tools': 'none', 'account': 'demoshop', 'space': space, 'condition': cond, 'size': size, 'baths': baths,
                                       'date': (TODAY + dt.timedelta(days=5 + i * 2)).isoformat(), 'slot': '09:00–13:00', 'area': '',
                                       'address': addr, 'name': name, 'phone': phone, 'photo_via': 'human', 'notes': '示範估價需求'}, f'10.0.0.{i + 1}')
        qn += 1
    except Exception as e:
        print('估價單建立失敗（略過）：', type(e).__name__, e)
ids = [r[0] for r in con.execute('SELECT id FROM quotes ORDER BY id')]
vu = (TODAY + dt.timedelta(days=7)).isoformat()
for k, qid in enumerate(ids):            # 第 1 張：已傳給客戶（客戶端看得到正式報價）；第 2、4 張：待店長確認；第 3 張：等照片
    stage = {0: 'sent', 1: 'review', 3: 'review'}.get(k, 'photos')
    con.execute('UPDATE quotes SET stage=?,sent_at=?,valid_until=?,reviewed_by=? WHERE id=?',
                (stage, c.now() if stage == 'sent' else '', vu if stage == 'sent' else '', '示範管理員' if stage == 'sent' else '', qid))
    con.execute('UPDATE quotes SET token=? WHERE id=?', (f'demo-quote-{k + 1:04d}', qid))      # 固定網址：/q/demo-quote-0001
con.commit()

s = {t: con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ('customers', 'workers', 'sites', 'orders', 'assignments', 'quotes', 'invoices', 'payments', 'settlements', 'users')}
s['orders_past'] = con.execute("SELECT COUNT(*) FROM orders WHERE date<? AND date>=?", (TODAY.isoformat(), (TODAY - dt.timedelta(days=14)).isoformat())).fetchone()[0]
s['orders_future'] = con.execute("SELECT COUNT(*) FROM orders WHERE date>=?", (TODAY.isoformat(),)).fetchone()[0]
con.close()
print('示範資料建立完成：', json.dumps(s, ensure_ascii=False))
