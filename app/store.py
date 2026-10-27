"""公開的「商店資訊」頁（/store?b=demoshop|bnb|helper）：LINE Pay 等金流審核要看的網站資訊——
公司名稱、統編、地址、聯絡方式、服務項目與價格、付款方式、取消與退款政策、隱私權政策、服務條款。
價格直接讀系統價目（pricing），改價這裡自動跟著變；條款讀合約（contract），跟簽約內容一致。
"""
import json
import integrations as ix

LEGAL = {'name': '示範服務股份有限公司', 'tax_id': '00000000', 'address': '○○縣○○市示範路 1 號',
         'source': '經濟部商工登記公示資料（114/02/20 核准設立）'}

def legal(con):
    try:
        return {**LEGAL, **json.loads(ix.setting(con, 'company_legal') or '{}')}
    except ValueError:
        return LEGAL

def _prices(con, b):
    import pricing
    cfg = pricing.config(con, b)
    if b == 'bnb':
        return [('民宿日常房務（淡季，4 小時）', f"一人 {cfg['bnb_off_1']:,} 元／二人以上每人 {cfg['bnb_off_n']:,} 元"),
                ('民宿日常房務（旺季，4 小時）', f"一人 {cfg['bnb_peak_1']:,} 元／二人以上每人 {cfg['bnb_peak_n']:,} 元"),
                ('民宿日常房務（國定連假，4 小時）', f"一人 {cfg['bnb_hol_1']:,} 元／二人以上每人 {cfg['bnb_hol_n']:,} 元"),
                ('超時', f"每人每小時 {cfg['bnb_overtime']:,} 元"), ('旺季後大掃除', f"{cfg['bnb_deep']:,} 元起"),
                ('垃圾代丟', f"單次 {cfg['bnb_trash']:,} 元／包月（4 次）{cfg['bnb_trash_month']:,} 元")]
    if b == 'helper':
        out = [('日常清潔', f"每人每小時 {cfg['helper_rate']:,} 元（至少 {cfg['helper_min_hours']} 小時）")]
        out += [(k.replace('月方案・', '月方案：'), f'{v[1]:,} 元／月') for k, v in pricing.MAMA_PLANS.items()]
        return out + [('單次清潔、大掃除、裝潢後細清、退租清潔', '依現場狀況報價（免費估價）')]
    out = [('居家清潔（單次）', f"每人每小時 {cfg['rate_single']:,} 元起（每次 {cfg['min_single']:,} 元起）"),
           ('居家清潔（定期，每月 4 次以上）', f"每人每小時 {cfg['rate_plan']:,} 元起"),
           ('大掃除／細清／搬家前後', f"每人每小時 {cfg['rate_deep']:,} 元起（{cfg['min_deep']:,} 元起）"),
           ('裝潢後細清', f"每人每小時 {cfg['rate_reno']:,} 元起（{cfg['min_reno']:,} 元起）"),
           ('店面／辦公室清潔', f"每人每小時 {cfg['rate_shop']:,} 元起")]
    out += [(f'加購：{k}', f'{v:,} 元起') for k, v in (cfg.get('addons') or {}).items()]
    return out + [('現場估價', f"{cfg['site_visit_fee']:,} 元（社區清潔免費）")]

def view(con, b):
    import brands, contract, line_bot, booking
    b = b if b in ('demoshop', 'bnb', 'helper') else 'demoshop'
    bn = brands.name(b); lg = legal(con)
    terms = contract.terms(bn, '', b)
    pick = lambda key: next((t['items'] for t in terms if key in t['title']), [])
    contact = {'line': f"https://line.me/R/ti/p/{line_bot.basic_id(con, b)}", 'line_id': line_bot.basic_id(con, b),
               'phone': ix.setting(con, 'store_phone') or '', 'email': ix.setting(con, 'store_email') or '', 'hours': ix.setting(con, 'store_hours') or '每日 09:00–18:00（官方 LINE 留言 24 小時都收得到）'}
    return {'brand': b, 'brand_name': bn, 'company': lg, 'contact': contact, 'prices': _prices(con, b), 'faq': __import__('seo').faq(con, b),      # AEO：店長審核過的常見問答
            'price_note': '以上為未稅參考價，實際金額以正式報價單為準（原則上依坪數、髒污程度、人數與時數計算）。國定連假與春節期間另有加價，以公告為準。',
            'pay_methods': ['銀行匯款（報價單上有匯款帳戶，匯款後在 LINE 回報末五碼）'] + (['LINE Pay（服務當天或完工後的款項：報價單或付款通知上按「用 LINE Pay 付款」）'] if __import__('linepay').live(con, b) else ['LINE Pay 線上付款（即將開放，用於服務當天或完工後的款項）']),
            'payment_rules': pick('付款'), 'cancel_rules': pick('改期'),
            'refund_rules': ['可退的款項，原則上於確認後 7 個工作天內退回：LINE Pay 付款原路退回 LINE Pay；匯款付款退回您指定的帳戶。',
                             '服務品質有疑慮，請於完工當日（最遲 3 天內）在官方 LINE 按「有地方需要加強」或留言；原則上先安排補做，無法補做時依實際情況協商部分退款。',
                             '本服務為到府勞務，服務完成後原則上不適用商品退貨；已提供的服務時數依實際完成計算。'],
            'service_flow': ['官方 LINE 線上估價（拍照）或預約現場估價', '收到正式報價單，線上閱讀條款並簽名', '依期限付款，收款後正式排定', '服務前一天提醒、清潔人員到場打卡', '完工照片傳給您確認驗收'],
            'privacy_url': f'/privacy?b={b}', 'book_url': f'/book?b={b}'}
