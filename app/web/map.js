'use strict';
/* 地區分布：宜蘭各鄉鎮的客戶分布與可支援夥伴（浮動泡泡地圖；左上小圖是台灣位置）。夥伴少、客戶多的地方標紅，派工前一眼看出缺口。 */
// 示意位置（保持相對地理位置，但把蘭陽平原拉開，泡泡才不會擠在一起）；單位＝畫布百分比
const TOWNS = [['頭城鎮', 70, 9], ['礁溪鄉', 56, 21], ['壯圍鄉', 76, 33], ['宜蘭市', 52, 37], ['員山鄉', 31, 38], ['五結鄉', 75, 53], ['羅東鎮', 52, 55],
  ['三星鄉', 28, 58], ['冬山鄉', 55, 72], ['蘇澳鎮', 79, 73], ['大同鄉', 10, 76], ['南澳鄉', 60, 92]];
const YILAN = [[62, 1], [82, 3], [88, 22], [90, 45], [88, 62], [93, 75], [84, 88], [70, 99], [48, 99], [30, 92], [3, 86], [2, 66], [14, 46], [24, 30], [44, 14]];
const TAIWAN_YILAN = [[121.70, 24.99], [121.86, 24.98], [121.87, 24.86], [121.83, 24.72], [121.90, 24.55], [121.78, 24.35], [121.45, 24.35], [121.28, 24.56], [121.55, 24.78]];
const TAIWAN = [[121.0, 25.3], [121.6, 25.3], [122.0, 25.0], [121.85, 24.6], [121.6, 24.0], [121.4, 23.3], [121.0, 22.6], [120.85, 21.9], [120.6, 22.3], [120.2, 22.6],
  [120.1, 23.0], [120.05, 23.4], [120.2, 23.9], [120.6, 24.5], [120.8, 24.9]];
let MAPSEL = '';
const townKey = t => t.replace(/[市鎮鄉]$/, '');
function mapData() {
  const act = (S.workers || []).filter(w => w.status === 'active'), all = {};
  for (const [t] of TOWNS) all[t] = { cust: [], work: [] };
  const custs = (S.customers || []).filter(c => ['active', 'paused'].includes(c.status));
  for (const c of custs) {
    const towns = new Set((IDX.sitesOf[c.id] || []).map(s => TOWNS.find(([t]) => (s.area || '').includes(townKey(t)) || (s.address || '').includes(townKey(t)))?.[0]).filter(Boolean));
    for (const t of towns) all[t].cust.push(c);
  }
  for (const w of act) {      // 新格式「宜蘭縣羅東鎮」「宜蘭縣全區」，也相容舊資料「羅東」「全宜蘭都可以」
    const txt = (w.regions || '') + ' ' + (w.notes || ''), every = /宜蘭縣全區|全宜蘭|都可|遠近/.test(txt) || /宜蘭縣(?![^\s、,，;；]*[市鎮鄉區])/.test(txt);
    const parts = (w.regions || '').split(/[、,，;；\s]+/).filter(Boolean);
    const other = parts.length && parts.every(p => /^(?!宜蘭縣)[^\s]{2}[縣市]/.test(p) && !/^(宜蘭市)/.test(p));     // 只登記外縣市
    for (const [t] of TOWNS) if (!other && (every || parts.some(p => p.replace(/^宜蘭縣/, '').replace(/[市鎮鄉區]$/, '') === townKey(t)) || txt.includes(townKey(t)))) all[t].work.push(w);
  }
  return all;
}
PAGES.map = () => {
  const D = mapData(), W = 760, H = 720;
  const px = x => 60 + x / 100 * (W - 120), py = y => 40 + y / 100 * (H - 90);
  const maxC = Math.max(1, ...Object.values(D).map(v => v.cust.length));
  const tw = (lng, lat) => [10 + (lng - 120) / 2.1 * 120, 10 + (25.4 - lat) / 3.6 * 200];
  const totalC = new Set(Object.values(D).flatMap(v => v.cust.map(c => c.id))).size, act = (S.workers || []).filter(w => w.status === 'active').length;
  let h = phead('地區分布', '哪裡客戶多、哪裡夥伴夠。', `宜蘭 12 個鄉鎮：泡泡大小＝服務中客戶數，綠色外圈＝可支援夥伴（區域含該鄉鎮或全宜蘭），紅色＝客戶多但夥伴少。點泡泡看名單。服務中客戶 ${totalC} 位、可派工夥伴 ${act} 位。`);
  h += `<div class="mapwrap card"><svg viewBox="0 0 ${W} ${H}" class="ymap" role="img" aria-label="宜蘭客戶與夥伴分布">
    <defs><radialGradient id="sea" cx="85%" cy="50%" r="70%"><stop offset="0" stop-color="#dbeafe"/><stop offset="1" stop-color="#f5f5f7"/></radialGradient></defs>
    <rect width="${W}" height="${H}" fill="url(#sea)" rx="18"/>
    <polygon points="${YILAN.map(([a, b]) => px(a) + ',' + py(b)).join(' ')}" fill="#f1ebe3" stroke="#c9bba4" stroke-width="2" stroke-linejoin="round"/>
    <text x="${W - 24}" y="${H / 2}" font-size="13" fill="#7aa0c8" text-anchor="end" writing-mode="tb">太平洋</text>
    <g transform="translate(14,14)"><rect width="140" height="226" rx="12" fill="rgba(255,255,255,.8)"/><polygon points="${TAIWAN.map(([a, b]) => tw(a, b).join(',')).join(' ')}" fill="#e5e5ea" stroke="#c7c7cc"/>
      <polygon points="${TAIWAN_YILAN.map(([a, b]) => tw(a, b).join(',')).join(' ')}" fill="#6B5A4E"/><text x="70" y="218" text-anchor="middle" font-size="12" fill="#6e6e73">台灣・宜蘭</text></g>
    ${TOWNS.map(([t, lng, lat], i) => {
      const d = D[t], r = 16 + 26 * Math.sqrt(d.cust.length / maxC), gap = d.cust.length > 0 && d.work.length < Math.max(1, Math.ceil(d.cust.length / 4));
      const col = gap ? '#ff3b30' : d.cust.length ? '#6B5A4E' : '#aeaeb2';
      return `<g class="bub${MAPSEL === t ? ' on' : ''}" data-act="mapPick" data-t="${t}" style="animation-delay:${(i * 0.37).toFixed(2)}s;cursor:pointer" transform="translate(${px(lng).toFixed(1)},${py(lat).toFixed(1)})">
        <circle r="${(r + 6 + Math.min(14, d.work.length * 1.5)).toFixed(1)}" fill="none" stroke="#34c759" stroke-opacity=".55" stroke-width="${Math.min(10, 2 + d.work.length)}"/>
        <circle r="${r.toFixed(1)}" fill="${col}" fill-opacity=".88"/><text y="-2" text-anchor="middle" font-size="13" font-weight="700" fill="#fff">${d.cust.length}</text>
        <text y="12" text-anchor="middle" font-size="10" fill="#fff">客戶</text><text y="${(r + 24).toFixed(0)}" text-anchor="middle" font-size="13" font-weight="600" fill="#1d1d1f">${t}</text>
        <text y="${(r + 39).toFixed(0)}" text-anchor="middle" font-size="11" fill="#248a3d">夥伴 ${d.work.length}</text></g>`;
    }).join('')}</svg></div>`;
  const rows = TOWNS.map(([t]) => [t, D[t]]).sort((a, b) => b[1].cust.length - a[1].cust.length);
  h += '<div class="card">' + tbl(['鄉鎮', '服務中客戶', '可支援夥伴', '狀況'], rows.map(([t, d]) => `<tr class="click" data-act="mapPick" data-t="${t}">${td('鄉鎮', `<b>${t}</b>`)}${td('客戶', d.cust.length)}${td('夥伴', d.work.length)}
    ${td('狀況', d.cust.length && d.work.length < Math.max(1, Math.ceil(d.cust.length / 4)) ? st('overdue', '夥伴不足') : d.cust.length ? st('completed', '足夠') : '<span class="small">—</span>')}</tr>`)) + '</div>';
  return h;
};
ACT.mapPick = d => {
  const D = mapData()[d.t]; MAPSEL = d.t; route(true);
  sheet(`${d.t}：客戶 ${D.cust.length}・夥伴 ${D.work.length}`, `<h3>可支援夥伴</h3>` + (D.work.map(w => `<div class="item click" data-act="worker" data-id="${w.id}"><div class="t"><div class="n">${esc(w.name)}</div><div class="m">${esc(w.regions || '')}　${esc(w.availability || '')}</div></div></div>`).join('') || '<div class="empty">沒有夥伴登記這一區</div>')
    + `<h3>服務中客戶</h3>` + (D.cust.map(c => `<div class="item click" data-act="customer" data-id="${c.id}"><div class="t"><div class="n">${esc(c.name)} <span class="small">${esc(c.channel || '')}</span></div><div class="m">${esc((IDX.sitesOf[c.id] || []).map(s => s.address || s.name).join('、'))}</div></div></div>`).join('') || '<div class="empty">這一區目前沒有服務中客戶</div>'));
};
