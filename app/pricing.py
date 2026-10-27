"""線上估價：依示範清潔過往成交（每人每小時中位數 400、P75 500、P90 667；方案 4h×4 次 8,400 ≈ 525/h）偏高估。
客戶不用自己判斷是居家、大掃除、裝潢細清還是社區清潔：表單只問「什麼空間」「現在什麼狀況」，這裡自動分類。
參數存在 settings.pricing（JSON），管理員可在後台調整；這裡是預設值。結果一律標示「原則上以主管確認為準」。"""
import json
import math
import re
import integrations as ix

DEFAULT = {
    'rate_single': 450,        # 居家單次：每人每小時（示範清潔過往中位數 400、P75 500）
    'rate_plan': 420,          # 定期方案：每人每小時（4 次以上）
    'rate_deep': 500,          # 大掃除／細清／搬家：每人每小時
    'rate_reno': 550,          # 裝潢細清：每人每小時（粉塵、殘膠，最費工）
    'rate_shop': 450,          # 店面／辦公室
    'bnb_per_room': 400,       # 民宿：每間房
    'min_single': 1800, 'min_deep': 3600, 'min_reno': 3000, 'min_bnb': 1600,
    'k_deep': 0.25, 'k_reno': 0.30,   # 大掃除／裝潢細清：每坪要幾個人時
    'pet_pct': 10, 'ladder': 300, 'no_lift_per_floor': 150, 'townhouse_pct': 10,
    'addons': {'冰箱清潔': 600, '窗簾拆洗': 900, '冷氣濾網': 400, '抽油煙機': 1500, '除塵蟎': 800, '收納整理': 1200, '洗衣摺衣': 500},     # 「垃圾清運 800」改成加購垃圾清收（每袋，見 trash_addon）
    'low_value': 3000,         # 單次初估在這以內：看照片線上報價；超過就請客戶現場估價
    'low_value_bnb': 6000,     # 民宿房間多、單價低：門檻另設（民宿線主力）
    'site_visit_fee': 500,     # 現場估價費
    'community_visit_fee': 0,  # 社區清潔現場估價費（想打進社區，預設免費）
    'max_auto_size': 120,      # 超過這個坪數一律現場估價
    # 品牌差異（各品牌在自己的 pricing 設定裡覆寫）
    'spaces': [],              # 表單可選的空間（空＝全部）；小幫手：['home']
    'quote_only': False,       # True＝不給系統初估，一律由專人報價（小幫手：定價還沒整理前）
    # 民宿線民宿房務（民宿線專屬；2026/09/30 價目表，未稅）
    'bnb_off_1': 1400, 'bnb_off_n': 1200, 'bnb_peak_1': 1600, 'bnb_peak_n': 1400, 'bnb_hol_1': 2300, 'bnb_hol_n': 2200,
    'bnb_overtime': 250, 'bnb_rooms_per_person': 4, 'bnb_deep': 5900, 'bnb_trash': 800, 'bnb_trash_month': 3000,
    'bnb_peak': ['06-15~09-14', '12-15~03-14'],
    # 垃圾清收（標準袋一袋約 100–120 公升；負責人定錨，多袋、上限、夥伴怎麼算問店長 → garbage.py）
    'trash_bag': 1200, 'trash_bag_more': 0, 'trash_max_bags': 3, 'trash_addon': 1000,    # 第一袋／第二袋起（0＝同第一袋）／一次最多幾袋線上初估（0＝不限）／清潔加購每袋
    'trash_pay': 600, 'trash_pay_mode': 'bag', 'trash_addon_pay': 0,                      # 夥伴：單獨清收固定酬勞（bag 每袋／visit 每次）；清潔加購另加（0＝算在時薪）
    'trash_no': '廚餘、大型家具家電、裝潢廢棄物、危險物品（可另外詢價）',
    'helper_rate': 450, 'helper_min_hours': 3,           # 居家小幫手時薪（每人每小時）
    'helper_hours_by_size': '10:3,20:4,30:5,40:6',     # 日常清潔依坪數建議時數（1 人；坪數上限:小時）；40 坪以上 2 人。店長可改（決策卡）
    # 國定連假（含連假中的週末）。⚠ 2026 依行政院人事行政總處公告，請店長每年核對更新
    'holidays': ['2026-01-01', '2026-02-14~2026-02-22', '2026-02-27~2026-03-01', '2026-04-03~2026-04-06', '2026-05-01~2026-05-03',
                 '2026-06-19~2026-06-21', '2026-09-25~2026-09-28', '2026-10-09~2026-10-11', '2026-10-24~2026-10-26', '2026-12-25~2026-12-27',
                 # 2027：人事行政總處 115/05/21 公告「116 年政府行政機關辦公日曆表」（春節 2/4 小年夜～2/10；全年無補班）
                 '2027-01-01~2027-01-03', '2027-02-04~2027-02-10', '2027-02-27~2027-03-01', '2027-04-03~2027-04-06', '2027-04-30~2027-05-02',
                 '2027-06-09', '2027-09-15', '2027-09-28', '2027-10-09~2027-10-11', '2027-10-23~2027-10-25', '2027-12-24~2027-12-26', '2027-12-31~2028-01-02'],
}
MAMA_SERVICES = ['日常清潔（時薪）', '月方案・基礎月護（每月 4 次）', '月方案・進階月安（每月 8 次）', '月方案・尊榮月恆（每月 12 次）', '單次清潔（看現場報價）',
                 '大掃除／裝潢後細清／退租清潔（免費估價）']
MAMA_PLANS = {'月方案・基礎月護（每月 4 次）': (4, 8400), '月方案・進階月安（每月 8 次）': (8, 16000), '月方案・尊榮月恆（每月 12 次）': (12, 24600)}

def suggest_hours(cfg, size):
    """日常清潔依坪數建議（小時, 人數）：設定「10:3,20:4,30:5,40:6」＝10 坪以內 3 小時、20 坪以內 4 小時…；超過最後一格 2 人 × 4 小時起。沒填坪數回 None。"""
    if not size or size <= 0:
        return None
    rows = []
    for part in str(cfg.get('helper_hours_by_size') or '').split(','):
        a, _, b = part.partition(':')
        try:
            rows.append((float(a), float(b)))
        except ValueError:
            continue
    for cap, h in sorted(rows):
        if size <= cap:
            return h, 1
    return 4.0, 2

def helper_estimate(cfg, f):
    """居家小幫手（確認）：日常時薪 450×人×時（至少 3 小時）；月方案固定價；單次、大掃除類看現場。"""
    svc = f.get('service_type') if f.get('service_type') in MAMA_SERVICES else MAMA_SERVICES[0]
    if svc in MAMA_PLANS:
        n, price = MAMA_PLANS[svc]
        return {'mode': 'auto', 'service_type': svc.split('（')[0], 'items': [{'label': svc, 'amount': price // n}], 'per_visit': price // n, 'visits': n, 'total': price,   # 品項記每次價，報價單會乘次數
                'hours': 4, 'people': 1, 'low_value': True, 'visit_fee': 0, 'freq': f'每月 {n} 次', 'note': '每月固定次數，於每月 5 號前付當月費用。'}
    if svc.startswith('日常清潔'):
        people = max(1, int(_num(f.get('people'), 1))); want = _num(f.get('hours'), 0) or 0
        sug = suggest_hours(cfg, _num(f.get('size'), 0))            # 客人填的時數比坪數建議少 → 用建議時數估（某客戶乙 17 坪填 3 小時，實際要 4 小時）
        need = sug[0] * sug[1] / people if sug else 0                 # 建議總人時 ÷ 客人選的人數
        hours = round(max(cfg.get('helper_min_hours', 3), want or need or 4, need) * 2) / 2
        amt = int(round(cfg.get('helper_rate', 450) * people * hours))
        note = (f"依 {_num(f.get('size'), 0):g} 坪，建議 {sug[1]} 人 × {sug[0]:g} 小時" + (f"（您填 {want:g} 小時，初估先用建議時數）" if want and want < hours else '') + '。' if sug else '') + '原則上以實際完成時數為準；實際金額以我們確認、您簽收的正式報價單為準。'
        tb, ta = trash_addon(cfg, f); tadd = [{'label': f'加購：{TRASH} {tb} 袋', 'amount': ta}] if tb else []      # 加購垃圾清收
        return {'mode': 'auto', 'service_type': '居家清潔', 'items': [{'label': f"日常清潔 {people} 人 × {hours:g} 小時（每人每小時 {cfg.get('helper_rate', 450)}）", 'amount': amt}] + tadd,
                'per_visit': amt + ta, 'visits': 1, 'total': amt + ta, 'hours': hours, 'people': people, 'low_value': True, 'visit_fee': 0, 'note': note,
                'suggest': {'hours': sug[0], 'people': sug[1]} if sug else None}
    st = '大掃除／細清' if svc.startswith('大掃除') else '居家清潔'
    return {'mode': 'auto', 'service_type': st, 'items': [], 'per_visit': 0, 'visits': 1, 'total': 0, 'hours': 4, 'people': 1, 'low_value': True, 'visit_fee': 0,
            'note': '這項需要看現場：請上傳照片，專人會看過照片後報價，必要時免費到府估價。'}

TRASH = '垃圾清收'

def trash_bags(v, top=20):
    """袋數（0～top）；亂填當 0。"""
    try:
        n = int(float(v or 0))
    except (TypeError, ValueError):
        return 0
    return max(0, min(n, top))

def trash_price(cfg, n):
    """單獨垃圾清收 n 袋：第一袋 trash_bag，第二袋起 trash_bag_more（0＝同第一袋）。"""
    if n <= 0:
        return 0
    one = int(cfg.get('trash_bag', 1200)); more = int(cfg.get('trash_bag_more') or one)
    return one + more * (n - 1)

def trash_estimate(cfg, f):
    """ 垃圾清收：每袋計價；超過一次上限袋數 → 不給初估，專人報價。"""
    n = max(1, trash_bags(f.get('bags'))); mx = int(cfg.get('trash_max_bags') or 0)
    base = {'mode': 'auto', 'service_type': TRASH, 'visits': 1, 'hours': 1 if n <= 2 else 1.5, 'people': 1, 'low_value': True, 'visit_fee': 0, 'bags': n}
    if mx and n > mx:
        return {**base, 'items': [], 'per_visit': 0, 'total': 0, 'note': f'一次超過 {mx} 袋由專人看照片報價；原則上以正式報價單為準。'}
    amt = trash_price(cfg, n)
    return {**base, 'items': [{'label': f'{TRASH} {n} 袋（每袋約 100–120 公升）', 'amount': amt}], 'per_visit': amt, 'total': amt,
            'note': '以上為系統初估，會先交給主管確認，確認後正式報價單會傳到您的 LINE；原則上以正式報價單為準。'}

def trash_addon(cfg, f):
    """清潔時加購垃圾清收：(袋數, 金額)。"""
    n = trash_bags(f.get('trash_bags'), 10)
    return (n, n * int(cfg.get('trash_addon', 1000))) if n else (0, 0)

BNB_SERVICES = ['日常房務', '旺季後大掃除', '垃圾代丟（單次）', '垃圾代丟（包月 4 次）', '代管諮詢']
PAY_METHODS = ['當日結算', '預付', '月結']

def _in_ranges(day, ranges):
    """day＝YYYY-MM-DD；ranges＝['YYYY-MM-DD~YYYY-MM-DD' 或 'MM-DD~MM-DD'（可跨年）或單日]。"""
    md = day[5:]
    for r in ranges or []:
        a, _, b = r.partition('~'); b = b or a
        if len(a) == 10:
            if a <= day <= b:
                return True
        elif (a <= md <= b) if a <= b else (md >= a or md <= b):
            return True
    return False

def bnb_season(cfg, day):
    if day and _in_ranges(day, cfg.get('holidays')):
        return 'hol', '國定連假'
    if day and _in_ranges(day, cfg.get('bnb_peak')):
        return 'peak', '旺季'
    return 'off', '淡季'

def bnb_estimate(cfg, f):
    """民宿線民宿房務：日常房務按人頭（1 人／2 人以上每人）× 季節；大掃除、垃圾代丟固定價；代管由專人說明。"""
    svc = f.get('service_type') if f.get('service_type') in BNB_SERVICES else '日常房務'
    rooms = int(_num(f.get('rooms'), 0))
    if svc == '代管諮詢':
        return {'mode': 'site_visit', 'service_type': '民宿代管', 'visit_fee': 0, 'reason': '代管方案會由專人聯絡，說明方案內容並了解您的民宿狀況。'}
    if svc == '旺季後大掃除':
        return {'mode': 'auto', 'service_type': '民宿大掃除', 'items': [{'label': '旺季後大掃除（單次優惠價）', 'amount': cfg['bnb_deep']}], 'per_visit': cfg['bnb_deep'],
                'visits': 1, 'total': cfg['bnb_deep'], 'hours': 4, 'people': 2, 'low_value': True, 'visit_fee': 0,
                'note': '依房間數、坪數與現場狀況確認；重垢、霉斑、特殊污漬或大坪數會另外估價。'}
    if svc.startswith('垃圾代丟'):
        amt = cfg['bnb_trash_month'] if '包月' in svc else cfg['bnb_trash']
        return {'mode': 'auto', 'service_type': svc, 'items': [{'label': svc, 'amount': amt}], 'per_visit': amt, 'visits': 1, 'total': amt, 'hours': 1, 'people': 1,
                'low_value': True, 'visit_fee': 0, 'note': ''}
    people = max(1, int(_num(f.get('people'), 0)) or (-(-max(rooms, 1) // cfg['bnb_rooms_per_person'])))
    k, sname = bnb_season(cfg, f.get('date') or '')
    rate = cfg[f'bnb_{k}_1'] if people == 1 else cfg[f'bnb_{k}_n'] * people
    return {'mode': 'auto', 'service_type': '民宿清潔', 'items': [{'label': f'日常房務（{sname}）{people} 人出勤', 'amount': rate}], 'per_visit': rate, 'visits': 1, 'total': rate,
            'hours': 4, 'people': people, 'low_value': True, 'visit_fee': 0, 'season': sname,
            'note': f"每次出勤約 2–4 小時，超時每小時 {cfg['bnb_overtime']} 元；1 位約可完成 4 間雙人房。未稅。"}
FREQ = {'單次': 1, '先試掃一次': 1, '每月 2 次（雙週）': 2, '每月 4 次': 4, '每月 8 次': 8, '每天／每週多次': 20}

# 客戶回答 → 服務類型（客戶不用懂術語）
SPACES = {'home': '住家', 'bnb': '民宿', 'shop': '店面／辦公室', 'community': '社區・大樓公共區域', 'factory': '廠房・其他'}
CONDITIONS = {'regular': '平常有住，想定期維持乾淨', 'deep': '很久沒徹底打掃（半年以上）', 'reno': '剛裝潢或整修完', 'move': '空屋（搬入前／搬出後）'}
def classify(space, condition=''):
    if space == 'home':
        return {'regular': '居家清潔', 'deep': '大掃除／細清', 'reno': '裝潢細清', 'move': '搬家前後清潔'}.get(condition, '居家清潔')
    return {'bnb': '民宿清潔', 'shop': '店面／辦公室清潔', 'community': '社區清潔', 'factory': '其他'}.get(space, '其他')

# 標準清潔範圍（報價單「規格與範圍說明」＋給夥伴看的範圍），讓報價一致化；店長可在審核時增刪
SCOPES = {
    '居家清潔': ['客廳、房間地面吸塵與拖地', '桌面、櫃面、窗台、開關面板擦拭除塵', '廚房檯面、水槽、爐台外部清潔', '浴室馬桶、洗手台、淋浴區、鏡面清潔', '垃圾集中整理'],
    '大掃除／細清': ['天花板、燈具、排風口除塵', '門窗、窗溝、紗窗擦拭', '櫃體內外、踢腳板、門框門片擦拭', '廚房油汙、浴室水垢加強清潔', '地面清潔與死角除塵'],
    '裝潢細清': ['天花板、燈具、排風口除塵清潔', '牆面、磁磚、廁間隔板、門框門片清潔', '馬桶、洗手台、鏡面、五金配件清潔', '地面粉塵、污漬、排水孔清潔', '裝潢後殘留垃圾集中整理'],
    '搬家前後清潔': ['全室天花板、牆面除塵', '櫃體、抽屜內外擦拭', '廚房、浴室深度清潔', '門窗、窗溝、紗窗擦拭', '地面清潔與垃圾集中整理'],
    '民宿清潔': ['床單被套更換與床鋪整理', '浴室清潔與備品補充', '地面吸塵拖地、垃圾集中打包', '桌面、櫃面擦拭', '退房狀況檢查回報'],
    '店面／辦公室清潔': ['地面吸塵與拖地', '桌面、櫃台、玻璃擦拭', '廁所清潔', '茶水間清潔', '垃圾集中整理'],
    '垃圾清收': ['到府收取打包好的垃圾（標準袋一袋約 100–120 公升）', '一般垃圾、分類好的資源回收', '原則上不收廚餘、大型家具家電、裝潢廢棄物、危險物品（可另外詢價）'],
}

def key(name, brand):
    """每個品牌的定價／範圍各自一份（品牌分清楚）；示範清潔沿用原本的設定名稱。"""
    return name if (brand or 'demoshop') == 'demoshop' else f'{name}_{brand}'

def config(con, brand='demoshop'):
    try:
        return {**DEFAULT, **json.loads(ix.setting(con, key('pricing', brand), '{}'))}
    except ValueError:
        return DEFAULT

def scopes(con, brand='demoshop'):
    """標準清潔範圍：店長在後台改過就用她的版本（每個品牌各自一份）。"""
    try:
        return {**SCOPES, **json.loads(ix.setting(con, key('scopes', brand), '{}'))}
    except ValueError:
        return SCOPES

def _num(v, default=0):
    m = re.findall(r'\d+(?:\.\d+)?', str(v or ''))
    return float(m[0]) if m else default

def advice(f, e):
    """表單快填完時的提示：「我們建議 XXX，時數 X 小時、人數 X 人」＋依據。現階段依過往案例（坪數表、線上估價算法）。"""
    sug = e.get('suggest') or {}
    hours, people = sug.get('hours') or e.get('hours'), sug.get('people') or e.get('people')
    if not hours or not people or e.get('hourly') or (e.get('mode') == 'site_visit' and not e.get('over')) or (e.get('mode') == 'auto' and not e.get('total')):
        return None
    why = []
    if _num(f.get('size')):
        why.append(f"{_num(f.get('size')):g} 坪")
    if _num(f.get('rooms')) and f.get('space') == 'bnb':
        why.append(f"{int(_num(f.get('rooms')))} 間房")
    if _num(f.get('baths')) > 1:
        why.append(f"{int(_num(f.get('baths')))} 間浴室")
    if f.get('pets'):
        why.append('有寵物')
    if f.get('lift') == '無電梯' and _num(f.get('floors')) >= 3:
        why.append(f"{int(_num(f.get('floors')))} 樓沒有電梯")
    svc = e.get('service_type') or '清潔'
    text = f"我們建議{svc}，時數 {float(hours):g} 小時、人數 {int(people)} 人"
    return {'text': text, 'hours': float(hours), 'people': int(people),
            'why': ('依' + '、'.join(why) + '，' if why else '') + '參考我們過往同類案例；實際以專人確認、您簽收的正式報價單為準。'}

def estimate(con, f):
    """包一層：每個初估都附 advice（表單快填完時的建議提示）。"""
    e = _estimate(con, f)
    try:
        a = None if e.get('service_type') == TRASH else advice(f, e)       # 垃圾清收不給時數建議
    except Exception:
        a = None
    if a:
        e['advice'] = a
    return e

def _estimate(con, f):
    """f：space、condition（或直接 service_type）、freq、size（坪）、rooms、baths、floors、lift、kind、pets、ladder、addons[]。
    回傳 {mode: auto|site_visit, service_type, items, total, hours, people, per_visit, visits, low_value, visit_fee, note}。"""
    import brands
    cfg = config(con, brands.pick(f.get('account')))
    b = brands.line_for(con, brands.pick(f.get('account')), f.get('line'))
    if b.get('kind') == 'trash':           # 垃圾代丟（月方案；垃圾清收不做了）
        import daidiu
        return daidiu.estimate(con, cfg, f)
    if b.get('kind') == 'bnb':             # 民宿線民宿房務（民宿線專屬價目）
        return bnb_estimate(cfg, f)
    if b.get('kind') == 'helper':            # 居家小幫手（小幫手專屬價目）
        return helper_estimate(cfg, f)
    if b.get('kind') == 'hourly':          # 時數制業務線（陪玩陪讀、私人管家…）：每小時價格 × 時數 × 人數
        h = b.get('hourly') or {}; rate = int(h.get('rate') or 0); hours = max(float(h.get('min_hours') or 2), _num(f.get('hours'), 0) or float(h.get('min_hours') or 2))
        people = max(1, int(_num(f.get('people'), 1))); st = f.get('service_type') or ((b.get('services') or [b.get('name')])[0])
        per = int(round(rate * hours * people / 50) * 50)
        return {'mode': 'auto', 'service_type': st, 'items': [{'label': f"{st}：{people} {h.get('unit') or '位'} × {hours:g} 小時", 'amount': per}],
                'per_visit': per, 'visits': 1, 'total': per, 'hours': hours, 'people': 1, 'low_value': True, 'visit_fee': 0, 'hourly': True,
                'note': '以上為系統初估，會先交給主管確認，確認後正式報價單會傳到您的 LINE；原則上以正式報價單為準。'}
    st = classify(f['space'], f.get('condition')) if f.get('space') else (f.get('service_type') or '居家清潔')
    if cfg.get('quote_only'):              # 這個品牌的定價還沒整理：不給初估，由專人看照片報價
        return {'mode': 'auto', 'service_type': st, 'items': [], 'per_visit': 0, 'visits': FREQ.get(f.get('freq') or '單次', 1), 'total': 0, 'hours': 3, 'people': 1,
                'low_value': True, 'visit_fee': 0, 'note': '報價會由專人看過照片後提供。'}
    size = _num(f.get('size')); rooms = int(_num(f.get('rooms'), 0)); baths = int(_num(f.get('baths'), 1)) or 1
    floors = int(_num(f.get('floors'), 1)) or 1; visits = FREQ.get(f.get('freq') or '單次', 1)
    if st in ('社區清潔', '其他') or (st != '民宿清潔' and not size) or size > cfg['max_auto_size']:
        fee = cfg['community_visit_fee'] if st == '社區清潔' else cfg['site_visit_fee']
        why = '社區清潔會由專人到現場了解需求再報價。' if st == '社區清潔' else ('請先填坪數。' if not size and st != '其他' else '這類空間需要專人到現場看過才能報準確的價格。')
        return {'mode': 'site_visit', 'service_type': st, 'reason': why, 'visit_fee': fee}
    items = []
    if st == '民宿清潔':
        n = max(rooms, 1); base = max(n * cfg['bnb_per_room'], cfg['min_bnb'])
        hours = max(3, round(n * 0.6 + baths * 0.3, 1)); people = 1 if n <= 4 else 2
        items.append((f'民宿清潔 {n} 間房', base))
    elif st in ('大掃除／細清', '搬家前後清潔', '裝潢細清'):
        k, rate, mn = (cfg['k_reno'], cfg['rate_reno'], cfg['min_reno']) if st == '裝潢細清' else (cfg['k_deep'], cfg['rate_deep'], cfg['min_deep'])
        ph = max(5 if st == '裝潢細清' else 8, size * k + baths * 1.5 + 1.5)          # 人時
        people = max(2, math.ceil(ph / 7)); hours = math.ceil(ph / people * 2) / 2
        base = max(math.ceil(ph * rate / 100) * 100, mn)
        items.append((st, base))
    elif st == '店面／辦公室清潔':
        hours = max(3, math.ceil((size / 12 + baths * 0.3) * 2) / 2); people = 1 if hours <= 5 else 2; hours = math.ceil(hours / people * 2) / 2
        base = max(math.ceil(hours * people * cfg['rate_shop'] / 100) * 100, cfg['min_single'])
        items.append((st, base))
    else:   # 居家清潔
        hours = min(8, max(3, math.ceil((4 + (size - 30) / 15 + max(0, baths - 2) * 0.5) * 2) / 2)); people = 1 if hours <= 5 else 2
        if people == 2:
            hours = math.ceil(hours / 2 * 2) / 2
        rate = cfg['rate_plan'] if visits >= 4 else cfg['rate_single']
        base = max(math.ceil(hours * people * rate / 100) * 100, cfg['min_single'] if visits < 4 else 0)
        items.append((st, base))
    extra = []
    if (f.get('kind') or '') == '透天' and floors >= 2:
        extra.append((f'透天 {floors} 層樓梯與樓層', math.ceil(base * cfg['townhouse_pct'] / 100 / 100) * 100))
    if f.get('pets'):
        extra.append(('寵物毛髮加強', math.ceil(base * cfg['pet_pct'] / 100 / 100) * 100))
    if f.get('ladder'):
        extra.append(('高處清潔（自備梯子）', cfg['ladder']))
    if f.get('lift') == '無電梯' and floors >= 3:
        extra.append(('無電梯搬運工具', cfg['no_lift_per_floor'] * (floors - 2)))
    for a in f.get('addons') or []:
        if a in cfg['addons']:
            extra.append((f'加購：{a}', cfg['addons'][a]))
    tb, ta = trash_addon(cfg, f)
    if tb:                                 # 清潔加購垃圾清收（每袋）
        extra.append((f'加購：{TRASH} {tb} 袋', ta))
    items += extra
    per_visit = base + sum(v for _, v in extra)
    scale = per_visit - sum(v for l, v in extra if l.startswith('加購：'))      # 加購不算進線上報價上限（只看清潔本身＋樓層、寵物這類加價）
    total = per_visit * visits
    lv = cfg.get('low_value_bnb', cfg['low_value']) if f.get('space') == 'bnb' else cfg['low_value']
    if scale > lv:           # 單次（不含加購）超過門檻：請客戶現場估價（收估價費），店長可在後台改回線上報價
        return {'mode': 'site_visit', 'service_type': st, 'visit_fee': cfg['site_visit_fee'], 'over': True, 'internal_total': total, 'internal_per_visit': per_visit,
                'internal_items': [{'label': l, 'amount': a} for l, a in items], 'hours': hours, 'people': people, 'visits': visits,
                'reason': f"這個規模需要專人到現場看過，才能報給您準確的價格。"}
    return {'mode': 'auto', 'service_type': st, 'items': [{'label': l, 'amount': a} for l, a in items], 'per_visit': per_visit, 'visits': visits, 'total': total,
            'hours': hours, 'people': people, 'low_value': scale <= lv, 'visit_fee': cfg['site_visit_fee'],
            'note': '以上為系統初估，報價會先交給主管確認，確認後正式報價單會傳到您的 LINE；原則上以正式報價單為準。'}

def draft_items(f, est, scope_map=None):
    """系統初估 → 報價單品項（項目／規格與範圍說明／費用）。主項目帶標準範圍，加價項各自一列。"""
    if est.get('hourly'):
        return [{'title': est['service_type'], 'sub': (f.get('notes') or '')[:40], 'scope': [], 'amount': est['items'][0]['amount']}]
    st = est['service_type']; size = f.get('size'); rb = '・'.join(x for x in (f"{size} 坪" if size else '', f"{f.get('rooms')} 房" if f.get('rooms') else '',
                                                                             f"{f.get('baths')} 衛" if f.get('baths') else '') if x)
    its = est.get('items') or est.get('internal_items') or []
    if not its:
        return []
    if st == TRASH:                         # 垃圾清收寫袋數（夥伴酬勞也照這裡的袋數算，garbage.bags）
        rb = f"{est.get('bags') or 1} 袋（每袋約 100–120 公升）"
    if st == '垃圾代丟':                     # 寫方案（金額是月費，不乘次數）
        rb = its[0]['label'].split('・', 1)[-1]
    out = [{'title': st, 'sub': rb, 'scope': list((scope_map or SCOPES).get(st, [])), 'amount': its[0]['amount']}]
    for it in its[1:]:
        out.append({'title': it['label'].replace('加購：', ''), 'sub': '加購' if it['label'].startswith('加購') else '', 'scope': [], 'amount': it['amount']})
    if est['visits'] > 1:
        out = [{**x, 'amount': x['amount'] * est['visits']} for x in out]
        out[0]['sub'] = (out[0]['sub'] + '・' if out[0]['sub'] else '') + f"每月 {est['visits']} 次"
    return out
