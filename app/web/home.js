'use strict';
/* 官方網站（公開）：品牌主張、服務、參考價格、流程、付款與退款、客戶好評（客戶同意不具名分享的）、公司資訊、LINE 預約。
   LINE Pay 正式商店申請「官方網址」需要自架、服務已上架的網站；內容沿用商店資訊頁（價格讀系統價目、條款讀合約），陪玩／管家依店長營運手冊「尚未上線、先不放價格」。 */
const esc = s => String(s ?? '').replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
const li = xs => '<ul>' + xs.map(x => `<li>${esc(x)}</li>`).join('') + '</ul>';
const COPY = {
  demoshop: { tag: '把時間留給生活，把日常交給示範清潔。', lead: '台北、新北、桃園、台中、台南、高雄六都與宜蘭到府清潔：居家清潔、大掃除、裝潢後細清、搬家前後清潔、店面與辦公室清潔。線上拍照估價、正式報價單、清潔前後照片，讓您每一次都放心。',
    svc: [['居家清潔', '單次、定期（每週／隔週／每月）都可以，固定夥伴優先安排。'], ['大掃除／細清', '很久沒徹底打掃、過年前大掃除，依坪數與髒污程度報價。'], ['裝潢後細清', '粉塵、殘膠、油漆點，交屋入住前一次清乾淨。'],
      ['搬家前後清潔', '退租、空屋、搬入前清潔，照片給屋主／房東確認。'], ['店面／辦公室', '定期或單次清潔，可配合營業時間。'], ['垃圾代丟', '每週固定幾天，晚上把垃圾放門口，當晚收走（月費方案）。'], ['配合廠商', '窗簾拆洗送洗、高空清洗，一起幫您安排。']],
    soon: [['陪玩姊姊', '家長在場的兒童互動活動（繪本、藝術、益智遊戲）。'], ['私人管家', '家務執行型、生活管理型，幫忙打理家庭大小事。']] },
  bnb: { tag: '民宿房務，交給專業的團隊。', lead: '宜蘭民宿退房清潔、備品補充與房務整理，配合入住時間，完工照片即時回報。', svc: [['民宿退房清潔', '依房間數報價，配合退房、入住時間。'], ['整棟大掃除', '淡季或換季整棟深度清潔。'], ['房務整理', '備品補充、床包更換、垃圾分類。']], soon: [] },
  helper: { tag: '像小幫手一樣細心，把家整理乾淨。', lead: '台北、新北、桃園、台中、台南、高雄六都與宜蘭到府居家清潔與大掃除，線上拍照估價、正式報價單、完工照片確認。', svc: [['居家清潔', '單次或定期到府清潔。'], ['大掃除／細清', '依坪數與髒污程度報價。'], ['社區清潔', '社區公共區域定期清潔。'], ['垃圾代丟', '每週固定幾天，晚上把垃圾放門口，當晚收走（月費方案）。']], soon: [] }
};
(async () => {
  const b = new URLSearchParams(location.search).get('b') || 'demoshop';
  let v, t = [];
  try { v = await (await fetch('/api/public/store?b=' + encodeURIComponent(b))).json(); } catch (e) { document.getElementById('app').innerHTML = '<p class="sub" style="padding:40px 0">暫時打不開，請稍後再試，或直接加入官方 LINE 詢問。</p>'; return; }
  try { t = await (await fetch('/api/public/testimonials?b=' + encodeURIComponent(b))).json(); } catch (e) { t = []; }
  const cp = COPY[b] || COPY.demoshop, c = v.company, k = v.contact;
  document.title = `${v.brand_name}｜${b === 'bnb' ? '宜蘭到府清潔・民宿房務' : '台北・新北・桃園・台中・台南・高雄・宜蘭到府清潔'}`;      // 示範清潔、小幫手六都都有
  const book = `${v.book_url}`, line = k.line;
  let h = `<div class="nav">${b === 'demoshop' ? '<img src="/brand-wordmark.png" alt="示範 示範清潔">' : `<span class="bn">${esc(v.brand_name)}</span>`}<div class="row"><a class="btn-ghost" href="${esc(line)}">加入官方 LINE</a></div></div>
    <div class="hero"><h1>${esc(cp.tag)}</h1><p>${esc(cp.lead)}</p><div class="row"><a class="btn-line" href="${esc(book)}">線上估價／預約</a><a class="btn-ghost" href="${esc(line)}">LINE 問問看</a></div></div>`;
  h += `<section><h2>服務項目</h2><p class="lead">原則上都先看照片或現場估價，再給您正式報價單。</p><div class="grid">${cp.svc.map(([a, d]) => `<div class="tile"><h3>${esc(a)}</h3><p>${esc(d)}</p></div>`).join('')}
    ${cp.soon.map(([a, d]) => `<div class="tile"><h3>${esc(a)}<span class="soon">即將推出</span></h3><p>${esc(d)}</p></div>`).join('')}</div></section>`;
  h += `<section><h2>參考價格</h2><p class="lead">${esc(v.price_note)}</p><div class="pt">${v.prices.map(([a, p]) => `<div>${esc(a)}</div><div>${esc(p)}</div>`).join('')}</div>
    <div class="row" style="margin-top:14px"><a class="btn-line" href="${esc(book)}">拍照線上估價</a></div></section>`;
  h += `<section><h2>服務流程</h2><div class="steps">${v.service_flow.map(x => `<div>${esc(x)}</div>`).join('')}</div></section>`;
  h += `<section><h2>為什麼選擇${esc(v.brand_name)}</h2><div class="grid">
    <div class="tile"><h3>正式報價單</h3><p>品項、範圍、金額寫清楚，線上閱讀條款後簽名，原則上不臨時加價。</p></div>
    <div class="tile"><h3>清潔前後照片</h3><p>每一次都拍清潔前、完工照片，完工後傳給您確認驗收。</p></div>
    <div class="tile"><h3>LINE 一對一通知</h3><p>人員安排、前一天提醒、到場通知、完工照片，都在官方 LINE 通知您。</p></div>
    <div class="tile"><h3>夥伴把關</h3><p>新進夥伴經過面試、背景查核（良民證）、實作與訓練才會派工。</p></div></div></section>`;
  if (t.length) h += `<section><h2>客戶怎麼說</h2><p class="lead">以下為客戶同意分享的評價（不具名）。</p><div class="grid">${t.slice(0, 6).map(x => `<div class="quote"><p>「${esc(x.text)}」</p><small>${'⭐'.repeat(x.stars || 5)}　${esc(x.month || '')}${x.service ? '・' + esc(x.service) : ''}</small></div>`).join('')}</div></section>`;
  if ((v.faq || []).length) h += `<section id="faq"><h2>常見問題</h2><div class="card">${v.faq.map(([q, a]) => `<h3 style="font-size:17px;margin:14px 0 4px">${esc(q)}</h3><p style="margin:0;color:var(--sub);line-height:1.7">${esc(a)}</p>`).join('')}</div></section>`;      //  AEO：店長審核過的常見問答
  h += `<section><h2>付款方式</h2><div class="card">${li(v.pay_methods)}</div></section>`;
  h += `<section><h2>付款、改期與退款</h2><div class="card"><b>付款</b>${li(v.payment_rules)}<b>改期與取消</b>${li(v.cancel_rules)}<b>退款</b>${li(v.refund_rules)}</div></section>`;
  h += `<footer><b>${esc(v.brand_name)}</b>　由 ${esc(c.name)} 經營（統一編號 ${esc(c.tax_id)}）<br>地址：${esc(c.address)}<br>
    官方 LINE：<a href="${esc(line)}">${esc(k.line_id)}</a>${k.phone ? `　電話：<a href="tel:${esc(k.phone)}">${esc(k.phone)}</a>` : ''}${k.email ? `　Email：<a href="mailto:${esc(k.email)}">${esc(k.email)}</a>` : ''}<br>${esc(k.hours)}<br>
    <a href="/store?b=${esc(b)}">商店資訊</a>　・　<a href="${esc(v.privacy_url)}">隱私權政策</a>　・　<a href="${esc(book)}">線上估價／預約</a></footer>`;
  document.getElementById('app').innerHTML = h;
})();
