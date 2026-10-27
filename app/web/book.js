const locDay = d => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);   // 當地日期
'use strict';
/* 預約・估價表單：客戶只回答「什麼地方」「現在什麼狀況」＋拍照，系統分類初估；正式報價由主管確認後傳到 LINE。 */
const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
const fmt = n => 'NT$ ' + Number(n).toLocaleString('zh-TW');
const viaPick = () => ($('#viaHuman') || {}).checked ? 'human' : $('#viaLine').checked ? 'line' : 'upload';      // 不方便拍照 → 轉專人
// 地址打了縣市、鄉鎮 → 下拉自動帶（以前要打地址又要選，常選錯）
document.addEventListener('change', e => { if (e.target.id !== 'address' || typeof regionSingle !== 'function') return;
  const m = e.target.value.replace(/\s/g, '').match(/([\u4e00-\u9fff]{2}[縣市])?([\u4e00-\u9fff]{1,3}[鄉鎮市區])/);
  if (m && $('#county')) REG = regionSingle($('#county'), $('#area'), (m[1] || $('#county').value) + m[2]); });
const acc = new URLSearchParams(location.search).get('b') || 'demoshop';
let OPT = null, EST = null, CREATED = null, SENT = 0, REG = null, DRAFT = null; const PICS = [];
const radios = (id, obj) => { $('#' + id).innerHTML = Object.entries(obj).map(([k, t], i) => `<label><input type="radio" name="${id}" value="${k}"${i === 0 ? ' checked' : ''}> ${t}</label>`).join(''); };
const pick = n => ($(`[name="${n}"]:checked`) || {}).value;
const picks = n => $$(`[name="${n}"]:checked`).map(x => x.value);
let HOURLY = false, BNB = false, MAMA = false, TRASH = false, LINE = null, HEAD = '', SUBT = '';
function applyLine(ln) {        // 品牌底下的業務線：清潔（坪數＋照片）或時數制（陪玩陪讀、私人管家⋯）
  LINE = ln; HOURLY = ln.kind === 'hourly'; BNB = ln.kind === 'bnb'; MAMA = ln.kind === 'helper'; TRASH = ln.kind === 'trash'; const hr = ln.hourly || {}, B = OPT.brand || {};
  $$('[name=line]').forEach(x => x.checked = x.value === ln.id);
  $('#hourlyBox').hidden = !HOURLY; $('#toolsBox').hidden = HOURLY || TRASH; $('#cleanBox').hidden = HOURLY || BNB || MAMA || TRASH; $('#bnbBox').hidden = !BNB; $('#helperBox').hidden = !MAMA; $('#trashBox').hidden = !TRASH;
  const pb = $('#photoBox'); if (!pb.dataset.h) { pb.dataset.h = pb.querySelector('h3').textContent; pb.dataset.b = pb.querySelector('.banner').innerHTML; }
  if (TRASH) { pb.querySelector('h3').textContent = '3. 垃圾照片（至少 1 張）'; pb.querySelector('.banner').innerHTML = '請拍一張<b>平常一次的垃圾量</b>（看得出幾袋、多大），可以的話再拍放垃圾的位置。不方便拍可以改用官方 LINE 傳。';      //  垃圾代丟；要看垃圾量
    const PL = (OPT.trash || {}).plans || [];
    $('#tplan').innerHTML = PL.map((x, i) => `<label><input type="radio" name="tplan" value="${x.name}"${i === 0 ? ' checked' : ''}> ${x.label}　${fmt(x.price)}${x.per_week ? '／月' : ''}</label>`).join('');
    $('#twd').innerHTML = [...'一二三四五六日'].map((d, i) => `<label><input type="checkbox" name="twd" value="${i}"> 週${d}</label>`).join('');
    $('#trest').innerHTML = [...'一二三四五六日'].map((d, i) => `<label><input type="checkbox" name="trest" value="${i}"> 週${d}</label>`).join(''); }
  else if (!BNB) { pb.querySelector('h3').textContent = pb.dataset.h; pb.querySelector('.banner').innerHTML = pb.dataset.b; }
  $('#slot').closest('div').hidden = TRASH; $('#dateH').textContent = TRASH ? '4. 從哪天開始收' : '4. 希望的時間';
  if (MAMA) $('#msvc').innerHTML = ((OPT.helper || {}).services || []).map((t, i) => `<label><input type="radio" name="msvc" value="${t}"${i === 0 ? ' checked' : ''}> ${t}</label>`).join(''); $('#photoBox').hidden = HOURLY && !hr.photos; $('#dateBox').hidden = HOURLY;
  if (BNB) {                          // 民宿線民宿房務：只有民宿相關服務；照片選填（擺放照片、須知）
    const bb = OPT.bnb || {};
    $('#bsvc').innerHTML = (bb.services || []).map((t, i) => `<label><input type="radio" name="bsvc" value="${t}"${i === 0 ? ' checked' : ''}> ${t}</label>`).join('');
    $('#bpay').innerHTML = ''; { const l_ = $('#bpay').previousElementSibling; if (l_ && l_.tagName === 'LABEL') l_.hidden = true; } $('#bpay').hidden = true;      // 付款方式不給客戶選
    $('#photoBox').querySelector('h3').textContent = '3. 房間擺放照片（選填）';
    $('#photoBox').querySelector('.banner').innerHTML = '可以傳房間、備品擺放的照片或須知，沒有人在現場也能照著做。';
  }
  $('.headline').textContent = HOURLY || TRASH ? `預約${ln.name}` : HEAD;
  $('.sub').textContent = HOURLY || TRASH ? `${ln.intro || ''} 選好時間送出，報價會先由主管確認，再傳到您的 LINE。` : SUBT;
  if (HOURLY) {
    $('#hsvc').innerHTML = (ln.services.length ? ln.services : [ln.name]).map((t, i) => `<label><input type="radio" name="hsvc" value="${t}"${i === 0 ? ' checked' : ''}> ${t}</label>`).join('');
    $('#hhours').value = hr.min_hours || 2; $('#hhours').min = hr.min_hours || 1;
    $('#hpeopleL').textContent = hr.people_label || '人數'; $('#hnoteL').textContent = hr.note_label || '需求說明';
    if (!$('#hdate').value) { const d = new Date(); d.setDate(d.getDate() + 2); $('#hdate').value = locDay(d); }
  }
  if (OPT.freq) refresh();
}
async function init() {
  { const t = new Date(Date.now() + 8 * 3600e3 + 864e5).toISOString().slice(0, 10); const hd = document.getElementById('hdate'); if (hd) hd.min = t; }      // 選今天、過去的日期送出才被擋
  try { OPT = await (await fetch('/api/public/options?b=' + encodeURIComponent(acc))).json(); }
  catch (e) { $('main').innerHTML = '<div class="card"><h2 style="margin-top:0">暫時打不開</h2><p>網路不穩或系統忙碌，請稍後重新整理；也可以直接在官方 LINE 跟我們說。</p><button class="btn full" onclick="location.reload()">重新整理</button><div id="lqc"></div></div>'; lqContact('#lqc', acc); return; }      //  
  const B = OPT.brand || {}; HEAD = $('.headline').textContent; SUBT = $('.sub').textContent;
  if (B.name) { document.title = `預約・估價｜${B.name}`; $('.wm').alt = B.name; }
  const lines = OPT.lines || [], want = new URLSearchParams(location.search).get('l');
  if (lines.length > 1) {        // 一個品牌有多條業務線：先選要哪一種服務
    $('#lineBox').hidden = false;
    $('#lines').innerHTML = lines.map(l => `<label><input type="radio" name="line" value="${l.id}"> ${l.name}</label>`).join('');
    $('#lines').addEventListener('change', e => applyLine(lines.find(l => l.id === e.target.value)));
  }
  applyLine(lines.find(l => l.id === want) || lines[0] || { id: '', kind: 'cleaning', name: '清潔服務', services: [], hourly: {} });
  radios('space', OPT.spaces); radios('cond', OPT.conditions);
  $('#freq').innerHTML = OPT.freq.map((t, i) => `<label><input type="radio" name="freq" value="${t}"${i === 0 ? ' checked' : ''}> ${t}</label>`).join('');
  $('#addon').innerHTML = Object.keys(OPT.addons).map(t => `<label><input type="checkbox" name="addon" value="${t}"> ${t}</label>`).join('');
  if ((OPT.trash || {}).addon) $('#trashAddL').textContent = `清潔時一起收垃圾（每袋約 100–120 公升，每袋 ${fmt(OPT.trash.addon)}）`;
  REG = regionSingle($('#county'), $('#area'), '宜蘭縣');
  const chkOut = () => { const c = REG.county(), out = !(OPT.service_counties || ['宜蘭縣']).includes(c); $('#outside').hidden = !out; if (out) $('#outside').textContent = outsideNote(c, OPT.service_counties, (OPT.brand || {}).name); };
  $('#county').addEventListener('change', chkOut); chkOut();
  brandHead((OPT.brand || {}).id, (OPT.brand || {}).name);
  document.querySelectorAll('img.wm').forEach(i => { i.style.visibility = ''; i.alt = (OPT.brand || {}).title || ''; });   // 品牌確定後才顯示字標（民宿線／小幫手不會閃過 示範）
  if ((OPT.brand || {}).name) $('#agreeBrand').textContent = OPT.brand.name;        // 民宿線／小幫手不出現示範清潔
  $('#slot').innerHTML = BNB ? '<option>11:00–15:00（依退房時間）</option><option>上午</option><option>下午</option>' : OPT.slots.map(x => `<option>${x}</option>`).join('');   // 民宿線：預設依退房時間
  const t = new Date(); t.setDate(t.getDate() + 3); $('#date').value = locDay(t);
  t.setDate(t.getDate() - 2); $('#date').min = locDay(t);
  const t0 = new URLSearchParams(location.search).get('t');
  if (t0) {                // 從 LINE 來的已綁定客戶：帶入稱呼、電話、地址
    const r = await fetch('/api/public/prefill?t=' + encodeURIComponent(t0)); const v = await r.json().catch(() => ({}));
    if (r.ok) {
      $('#name').value = v.name || ''; $('#phone').value = v.phone || ''; $('#line').value = v.line_name || '';
      const fillSite = s => {      // 綁定的業主帶入地址、掃具（現場有哪些）
        if (!s) return; $('#address').value = s.address || ''; if (s.area) REG = regionSingle($('#county'), $('#area'), s.area);
        if (s.tools) { const r = $(`[name="tools"][value="${s.tools}"]`); if (r) r.checked = true; }
        const note = s.tools_note || '', m = note.match(/現場有：([^；]*)/);
        $$('#toolsHave input').forEach(x => x.checked = !!m && m[1].split('、').includes(x.value));
        $('#toolsNote').value = note.replace(/現場有：[^；]*；?/, ''); refresh && refresh();
      };
      const ss = v.sites || []; fillSite(ss[0]);
      if (ss.length > 1) {         // 多個地點：選一個（也可以填新的）
        const box = document.createElement('div'); box.id = 'sitePick'; box.className = 'chips';
        box.innerHTML = '<span class="small">選地點：</span>' + ss.map((s, i) => `<label><input type="radio" name="sitepick" value="${i}"${i ? '' : ' checked'}> ${(s.name || s.address).replace(/</g, '&lt;')}</label>`).join('')
          + `<label><input type="radio" name="sitepick" value="new"> 新地點</label>`;
        $('#address').parentNode.insertBefore(box, $('#address'));
        box.addEventListener('change', () => { const k = pick('sitepick'); if (k === 'new') { $('#address').value = ''; $('#address').focus(); } else fillSite(ss[+k]); });
      }
      $('.sub').textContent = `${v.name} 您好！資料已幫您帶入，確認一下、拍幾張照片就好。報價會先由主管確認，再傳到您的 LINE。`;
    }
  }
  $('#bk').addEventListener('input', refresh); $('#bk').addEventListener('change', refresh); refresh();
  DRAFT = Draft.attach('book:' + acc + ':' + (new URLSearchParams(location.search).get('l') || ''), $('#bk'), { skip: ['website'],      // 填到一半離開不會不見（照片也帶回）
    extra: { get: () => PICS.slice(SENT), set: v => { PICS.push(...v.slice(0, Math.max(0, OPT.max_photos - PICS.length))); drawThumbs(); } } });
  DRAFT.restore();
}
function form() {          // 清潔類一律帶「現場掃具」（時數制服務不用）
  const f = form0();
  if (!HOURLY && !TRASH) { f.tools = pick('tools') || ''; f.tools_note = (() => { const h = [...document.querySelectorAll('#toolsHave input:checked')].map(x => x.value); return (h.length ? '現場有：' + h.join('、') + (($('#toolsNote').value || '').trim() ? '；' : '') : '') + $('#toolsNote').value; })(); }      // 勾現場有哪些工具
  if (!$('#trashAddBox').hidden && $('#trashAdd').checked) f.trash_bags = $('#taBags').value;      //  清潔加購垃圾清收
  if ($('#moreBox')) {           //  雲端搬本機：Google 表單原有的選填欄位
    f.email = $('#email').value.trim(); f.heard = $('#heard').value; f.referrer = f.heard === '親友推薦' ? $('#referrer').value.trim() : '';
    f.pref_days = TRASH ? [] : [...document.querySelectorAll('#prefDays input:checked')].map(x => x.value);
  }
  return f;
}
function form0() {
  if (MAMA) return { account: acc, line: LINE.id, service_type: pick('msvc'), service: pick('msvc'), space: 'home', people: $('#mpeople').value, hours: $('#mhours').value,
    size: $('#msize').value, rooms: $('#mrooms').value, date: $('#date').value, slot: $('#slot').value, area: REG ? REG.get() : $('#area').value, address: $('#address').value,
    name: $('#name').value, phone: $('#phone').value, line_name: $('#line').value, company: $('#company').value, tax_id: $('#taxid').value, invoice: !!($('#invoice') || {}).checked,
    notes: $('#notes').value, website: $('#website').value, photo_via: viaPick(), t: new URLSearchParams(location.search).get('t') || '', r: new URLSearchParams(location.search).get('r') || '', src: new URLSearchParams(location.search).get('src') || '' };
  if (BNB) return { account: acc, line: LINE.id, service_type: pick('bsvc'), service: pick('bsvc'), space: 'bnb', rooms: $('#brooms').value, size: $('#bsize').value,
    people: $('#bpeople').value, lift: $('#bnolift').checked ? '無電梯' : '', bnb_name: $('#bname').value, entry: $('#bentry').value, pay_method: pick('bpay'),
    date: $('#date').value, slot: $('#slot').value, start_time: /^11:00/.test($('#slot').value) ? '11:00' : '', area: REG ? REG.get() : $('#area').value, address: $('#address').value,
    name: $('#name').value, phone: $('#phone').value, line_name: $('#line').value, company: $('#company').value, tax_id: $('#taxid').value, invoice: !!($('#invoice') || {}).checked,
    notes: $('#notes').value, website: $('#website').value, photo_via: 'upload', t: new URLSearchParams(location.search).get('t') || '', r: new URLSearchParams(location.search).get('r') || '', src: new URLSearchParams(location.search).get('src') || '' };
  if (TRASH) return { account: acc, line: LINE.id, service_type: '垃圾代丟', service: pick('tplan'), weekdays: [...document.querySelectorAll('[name=twd]:checked')].map(x => +x.value), date: $('#date').value, start_time: '20:00',
    bags: pick('tbags'), pickup: pick('tpick') === 'other' ? $('#ttime').value : '20:00', rest_days: picks('trest').map(Number), truck_alt: pick('ttruck'),      // 量、時間、休息日、沒垃圾車那天都在表單問
    area: REG ? REG.get() : $('#area').value, address: $('#address').value, name: $('#name').value, phone: $('#phone').value, line_name: $('#line').value,
    company: $('#company').value, tax_id: $('#taxid').value, invoice: !!($('#invoice') || {}).checked,
    notes: [$('#tplace').value.trim() ? `垃圾放在：${$('#tplace').value.trim()}` : '', $('#notes').value].filter(Boolean).join('\n'),
    website: $('#website').value, photo_via: viaPick(), t: new URLSearchParams(location.search).get('t') || '', r: new URLSearchParams(location.search).get('r') || '', src: new URLSearchParams(location.search).get('src') || '' };
  if (HOURLY) return { account: acc, line: LINE.id, service_type: pick('hsvc'), date: $('#hdate').value, start_time: $('#htime').value, hours: $('#hhours').value, people: $('#hpeople').value,
    notes: $('#hnote').value, area: REG ? REG.get() : $('#area').value, address: $('#address').value, name: $('#name').value, phone: $('#phone').value, line_name: $('#line').value,
    company: $('#company').value, tax_id: $('#taxid').value, invoice: !!($('#invoice') || {}).checked, website: $('#website').value, photo_via: viaPick(), t: new URLSearchParams(location.search).get('t') || '', r: new URLSearchParams(location.search).get('r') || '', src: new URLSearchParams(location.search).get('src') || '' };
  return {
    account: acc, line: LINE ? LINE.id : '', space: pick('space'), condition: pick('cond'), freq: pick('freq'), kind: $('#kind').value, size: $('#size').value, rooms: $('#rooms').value,
    baths: $('#baths').value, floors: $('#floors').value, pets: $('#pets').checked, ladder: $('#ladder').checked, lift: $('#nolift').checked ? '無電梯' : '',
    addons: picks('addon'), date: $('#date').value, slot: $('#slot').value, area: REG ? REG.get() : $('#area').value, address: $('#address').value, name: $('#name').value,
    phone: $('#phone').value, line_name: $('#line').value, company: $('#company').value, tax_id: $('#taxid').value, invoice: !!($('#invoice') || {}).checked, notes: $('#notes').value,
    website: $('#website').value, photo_via: viaPick(), t: new URLSearchParams(location.search).get('t') || '', r: new URLSearchParams(location.search).get('r') || '', src: new URLSearchParams(location.search).get('src') || ''
  };
}
function layout() {
  const T = OPT.trash || {};             //  垃圾清收：清潔（示範清潔、小幫手）可以加購；垃圾清收本身另一條業務線
  $('#trashAddBox').hidden = !T.on || HOURLY || BNB || TRASH || (!MAMA && ['community', 'factory'].includes(pick('space'))); $('#taBags').disabled = !$('#trashAdd').checked;
  if (TRASH) { const p = (T.plans || []).find(x => x.name === pick('tplan')) || {}, n = document.querySelectorAll('[name=twd]:checked').length;      //  垃圾代丟
    $('#ttimeBox').hidden = pick('tpick') !== 'other';
    $('#twdBox').hidden = !p.per_week; $('#twdHint').textContent = p.per_week ? `選 ${p.per_week} 天（已選 ${n} 天）` : '';
    $('#trashPath').innerHTML = `💡 ${p.label || ''}：${fmt(p.price || 0)}${p.per_week ? '／月（每月 5 號前付當月）' : ''}；有訂閱定期清潔的會員 ${fmt(p.member || 0)}（用電話自動判斷）。不收${T.no || ''}。<b>實際金額以正式報價單為準</b>。`; return; }
  if (HOURLY) { $('#path').hidden = true; return; }
  if (MAMA) { const s = pick('msvc') || '', mo = OPT.helper || {};
    $('#helperHours').hidden = !s.startsWith('日常');
    const photoOpt = s.startsWith('日常') || s.startsWith('月方案');
    $('#photoBox').querySelector('h3').textContent = photoOpt ? '3. 現況照片（選填）' : '3. 現況照片（請上傳，專人看照片報價）';
    $('label[for=mhours]').textContent = `幾小時（至少 ${mo.min_hours || 3} 小時；填坪數會建議時數）`; $('#mhours').min = mo.min_hours || 3;
    $('#helperPath').innerHTML = s.startsWith('日常') ? `💡 日常清潔每人每小時 ${mo.rate || 450} 元，至少 ${mo.min_hours || 3} 小時，系統會依坪數建議時數；原則上以實際完成時數為準，<b>實際金額以簽收的正式報價單為準</b>。`
      : s.startsWith('月方案') ? '💡 月方案每月固定次數，於每月 5 號前付當月費用；可以先試掃一次再決定。'
      : '📷 這項需要看現場：請上傳每個要清潔區域的照片，專人看過後報價，必要時免費到府估價。'; return; }
  if (BNB) { const s = pick('bsvc'); $('#bnbDetail').hidden = s && s.startsWith('垃圾');
    $('#bnbPath').innerHTML = s === '代管諮詢' ? '🏡 代管方案會由專人聯絡說明，送出後我們會在官方 LINE 跟您約時間。'
      : `💡 日常房務按出勤人數計價（淡季／旺季／國定連假不同），1 位約可完成 4 間雙人房；超時每小時 ${(OPT.bnb || {}).overtime || 250} 元。報價會先由主管確認。`; return; }
  const sp = pick('space'), cond = pick('cond');
  $('#condBox').hidden = sp !== 'home';
  $('#freqBox').hidden = !((sp === 'home' && cond === 'regular') || sp === 'bnb' || sp === 'shop');
  $('#sizeBox').hidden = sp === 'community' || sp === 'factory';
  $('#kindBox').hidden = sp !== 'home'; $('#addonBox').hidden = !['home', 'bnb'].includes(sp);
  $('#roomsL').textContent = sp === 'bnb' ? '要清的房間數' : '房間數';
  // 一選好就先告訴客戶會怎麼估價
  const fee = n => n ? `估價費 ${fmt(n)}` : '免費';
  const low = OPT ? fmt(OPT.low_value) : '';
  $('#path').innerHTML = sp === 'community' ? `🏢 社區・大樓公共區域會由<b>專人到現場估價（${fee(OPT.community_visit_fee)}）</b>。請先拍幾張要清潔的公共區域照片，讓我們了解狀況。`
    : sp === 'factory' ? `🏭 廠房與特殊空間需要<b>專人到現場估價（${fee(OPT.site_visit_fee)}）</b>。請先拍照讓我們了解狀況。`
    : sp === 'home' && ['deep', 'reno', 'move'].includes(cond) ? `📍 這類清潔若單次超過 ${low}（加購不算），會請<b>專人到現場估價（${fee(OPT.site_visit_fee)}）</b>；${low} 以內用照片線上報價。`
    : `📷 一般用<b>照片線上報價</b>（單次超過 ${low}、加購不算，會改由專人現場估價，${fee(OPT.site_visit_fee)}）。`;
}
let timer = null;
function refresh() {
  layout(); $('#picCount').textContent = TRASH ? (PICS.length ? `已選 ${PICS.length} 張` : '至少 1 張') : PICS.length ? `已選 ${PICS.length} 張（至少 ${OPT.min_photos} 張）` : `至少 ${OPT ? OPT.min_photos : 3} 張`;
  clearTimeout(timer); timer = setTimeout(async () => {
    const r = await fetch('/api/public/estimate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form()) });
    const e = EST = await r.json().catch(() => ({})); const box = $('#est');
    const tip = e.advice ? `<div class="advice" role="status" style="background:#FFF7E6;border:1px solid #F0D9A8;border-radius:12px;padding:10px 12px;margin-bottom:12px;color:#5A3A22">💡 <b>${e.advice.text}</b><br><span class="small">${e.advice.why}</span></div>` : '';
    if (e.mode === 'site_visit') {
      box.hidden = false;
      box.innerHTML = tip + `<div class="estt">需要現場估價</div><p style="margin:4px 0">${e.reason || ''}</p><p class="small" style="margin-bottom:0">現場估價費：<b>${e.visit_fee ? fmt(e.visit_fee) : '免費'}</b>。送出後專人會在官方 LINE 跟您約時間；照片請照樣上傳，讓我們先了解狀況。</p>`;
      $('#go').textContent = '送出，預約現場估價'; return;
    }
    $('#go').textContent = '送出，請主管確認報價';
    if (!e.total) { box.hidden = !(OPT.quote_only || MAMA || TRASH || tip); if (OPT.quote_only || MAMA || TRASH || tip) box.innerHTML = tip + '<p class="small" style="margin:0">送出後，<b>專人會看過照片後提供報價</b>，確認後把正式報價單傳到您的 LINE；實際金額以您簽收的正式報價單為準。</p>'; return; }
    box.hidden = false;
    box.innerHTML = tip + `<div class="estt">系統初估（${e.service_type}）</div><div class="estrow total"><span>${e.visits > 1 ? '每月約' : '約'}</span><span>${fmt(e.total)} 起</span></div>`
      + (e.note && MAMA ? `<p class="small" style="margin:6px 0 0">${e.note}</p>` : '') + `<p class="small" style="margin-bottom:0">這只是初估，<b>實際金額以我們確認、您簽收的正式報價單為準</b>。報價會先交給主管確認，確認後把正式報價單傳到您的 LINE，原則上以正式報價單為準。</p>`;
  }, 300);
}
// 照片：手機上先縮到 1600px、轉 JPEG，再上傳（省流量、也避開 HEIC）
function shrink(file) {
  return new Promise((ok, bad) => {
    const img = new Image(), url = URL.createObjectURL(file);
    img.onload = () => {
      const k = Math.min(1, 1600 / Math.max(img.width, img.height)), cv = document.createElement('canvas');
      cv.width = Math.round(img.width * k); cv.height = Math.round(img.height * k); cv.getContext('2d').drawImage(img, 0, 0, cv.width, cv.height);
      URL.revokeObjectURL(url); ok(cv.toDataURL('image/jpeg', 0.82));
    };
    img.onerror = () => { URL.revokeObjectURL(url); bad(new Error('這張照片讀不到，請換一張')); };
    img.src = url;
  });
}
function drawThumbs() {
  $('#thumbs').innerHTML = PICS.map((d, i) => `<div class="thumb"><img src="${d}" alt="照片 ${i + 1}"><button type="button" data-i="${i}" aria-label="移除">×</button></div>`).join('');
  refresh(); DRAFT && DRAFT.save();
}
if ($('#heard')) $('#heard').addEventListener('change', () => { $('#refBox').hidden = $('#heard').value !== '親友推薦'; });
$('#pics').addEventListener('change', async e => {
  $('#err').textContent = '';
  for (const f of [...e.target.files]) {
    if (PICS.length >= OPT.max_photos) { $('#err').textContent = `照片最多 ${OPT.max_photos} 張`; break; }
    try { PICS.push(await shrink(f)); } catch (x) { $('#err').textContent = x.message; }
  }
  e.target.value = ''; drawThumbs();
});
$('#thumbs').addEventListener('click', e => { const b = e.target.closest('button[data-i]'); if (b && +b.dataset.i >= SENT) { PICS.splice(+b.dataset.i, 1); drawThumbs(); } });
const PREVIEW = new URLSearchParams(location.search).get('preview') === '1';      // 群發送審的預覽 → 可以填填看，送出不會建單
if (PREVIEW) { const b = document.createElement('div'); b.className = 'banner warn'; b.textContent = '👀 預覽模式：可以填填看，送出不會建立估價單、也不會通知任何人。'; document.querySelector('main').prepend(b); }
$('#bk').addEventListener('submit', async e => {
  e.preventDefault(); $('#err').textContent = '';
  if (PREVIEW) { $('#err').textContent = '預覽模式：這裡不會真的送出。客戶按送出後，報價會先交給主管確認。'; return; }
  const f = form(); document.querySelectorAll('.lq-bad').forEach(x => x.classList.remove('lq-bad'));
  const bad = (msg, el) => { if (el) { el.classList.add('lq-bad'); el.scrollIntoView({ block: 'center', behavior: 'smooth' }); if (el.focus && /INPUT|TEXTAREA/.test(el.tagName)) setTimeout(() => el.focus({ preventScroll: true }), 300); } $('#err').textContent = msg; };      // 照畫面順序檢查，捲到漏填那格
  if (!String(f.name || '').trim()) return bad('請留下稱呼', $('#name'));
  if (String(f.phone || '').replace(/\D/g, '').length < 8) return bad('請留下手機（我們用來聯絡、確認時間）', $('#phone'));
  if (!f.address.trim()) return bad('請填地址', $('#address'));
  if (!HOURLY && !TRASH && !f.tools) return bad('請選「現場掃具」：清潔當天需要我們自備掃具嗎？', $('#toolsBox'));
  const helperOpt = MAMA && /^(日常|月方案)/.test(f.service || '');
  if (TRASH && f.photo_via === 'upload' && !PICS.length) return bad('請拍一張平常一次的垃圾量（或勾選「我等一下直接在官方 LINE 傳照片」）', $('#photoBox'));
  if (TRASH && f.rest_days.some(d => f.weekdays.includes(d))) return $('#err').textContent = '休息日跟要收的日子重複了，請再確認';
  if (!BNB && !TRASH && !helperOpt && !(HOURLY && $('#photoBox').hidden) && f.photo_via === 'upload' && PICS.length < OPT.min_photos) return bad(`請上傳至少 ${OPT.min_photos} 張現況照片（或勾選「我等一下直接在官方 LINE 傳照片」）`, $('#photoBox'));
  if (!$('#agree').checked) return bad('請勾選同意使用資料', $('#agree').closest('label'));
  const go = $('#go'), label = go.textContent; go.disabled = true;
  try {
    go.textContent = '送出中…';
    const post = async (url, body) => { const r = await postRetry(url, body); const v = await r.json().catch(() => ({})); if (!r.ok) throw new Error(v.error || '送出失敗，請直接在官方 LINE 留言'); return v; };
    const q = CREATED = CREATED || await post('/api/public/quote', f);     // 重試不重複建單
    for (let i = SENT; i < PICS.length; i++) { go.textContent = `上傳照片 ${i + 1}/${PICS.length}…`; await post(`/api/public/quote/${q.token}/photo`, { content: PICS[i] }); SENT = i + 1; }
    const s = await post(`/api/public/quote/${q.token}/submit`, {});
    DRAFT && DRAFT.clear(); $('#bk').hidden = true; $('#ok').hidden = false; scrollTo(0, 0);
    $('#statusLink').href = '/q/' + q.token;
    $('#okText').innerHTML = q.mode === 'site_visit'
      ? `您的需求（${q.service_type}）需要專人到現場估價，現場估價費 <b>${q.visit_fee ? fmt(q.visit_fee) : '免費'}</b>。專人會在官方 LINE 跟您約時間。` + (s.stage === 'photos' ? `<br>也請在官方 LINE 傳現況照片（至少 ${OPT.min_photos} 張）。` : '')
      : s.stage === 'photos' ? `請在官方 LINE 直接傳現況照片（每個要清潔的區域都要拍，至少 ${OPT.min_photos} 張）。照片收齊後，報價會交給主管確認。`
        : `照片已收到。<b>報價會先交給主管確認</b>，確認後正式報價單會傳到您的 LINE，請稍候。`;
    if (q.line) { $('#lineStep').hidden = false; $('#lineCode').textContent = q.line.code; $('#lineGo').outerHTML = lqBlock(q.line.url, '用 LINE 傳送編號'); }
    else lqContact('#okLine', acc, '💬 回到 LINE');      // 已綁定的客戶也有回 LINE 的按鈕
  } catch (err) { $('#err').textContent = err.message; go.disabled = false; go.textContent = label; }
});
init();
