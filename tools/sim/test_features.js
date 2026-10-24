// 大改修の機能を一通り確かめる: ステージの開放・40番の開始・エディット・実績・宝物・合成・火薬樽・相性・倒れた敵
// 使い方: python -m http.server 8766 --bind 127.0.0.1（リポジトリ直下）→ node tools/sim/test_features.js
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const path = require('path');
(async () => {
  const b = await chromium.launch({ channel: 'chrome', headless: true });
  const p = await (await b.newContext({ locale: 'ja-JP', viewport: { width: 1100, height: 900 } })).newPage();
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto(process.env.GAME_URL || 'http://127.0.0.1:8766/src/game.html');
  await p.evaluate(() => localStorage.clear()); await p.reload();
  const out = {};
  const ok = (k, v) => { out[k] = v; };
  // ステージ選択 → 1 を開始 → クリア扱い → 2 が開く
  await p.click('#btnStage');
  ok('ステージ数', await p.evaluate(() => document.querySelectorAll('.stg').length));
  ok('最初は2が鍵', await p.evaluate(() => document.getElementById('stg-2').disabled));
  await p.screenshot({ path: path.join(__dirname, 'out', 'stages.png') });
  await p.click('#stg-1'); await p.click('#pick-lily'); await p.click('#btnNext1'); await p.click('#btnNext2'); await p.click('#btnBegin');
  ok('ステージ1の状態', await p.evaluate(() => { const G = window.__wanakan.G; return `${G.state} 部屋=${G.wave}夜相当`; }));
  await p.evaluate(() => { const W = window.__wanakan, G = W.G; G.intro = null; W.api.beginDefense(); G.phase = 3; G.spawnQueue = []; G.foes.length = 0; });
  await p.waitForTimeout(4200);
  ok('クリア画面', await p.evaluate(() => document.getElementById('rTitle').textContent));
  ok('2が開いた', await p.evaluate(() => JSON.parse(localStorage.getItem('trapoflily-stages')).open));
  ok('実績（最初の夜明け）', await p.evaluate(() => !!JSON.parse(localStorage.getItem('trapoflily-ach') || '{}').night1));
  ok('トースト', await p.evaluate(() => document.getElementById('toast').textContent));
  // ステージ40を直接開始
  await p.evaluate(() => { const W = window.__wanakan; W.api.setRun('stage', 40); W.api.startRun('cecil', ['bear', 'rock', 'fire', 'keg']); });
  ok('ステージ40', await p.evaluate(() => { const G = window.__wanakan.G; return `${G.state} 相当夜=${G.wave} 部屋=${window.__wanakan.api.mapName()} 罠枠=${window.__wanakan.api.stat.limit()}`; }));
  // 相性・合成・火薬樽・宝物・倒れた敵
  const r = await p.evaluate(() => {
    const W = window.__wanakan, A = W.api; A.setRun('challenge', 1); A.startRun('lily', ['fire', 'rock', 'keg', 'bear']); A.setPaused(true);
    const G = W.G; G.intro = null; G.mana = 999; G.phase = 1; G.foes.length = 0; G.spawnQueue = []; G.phaseBonus = 9;
    const foe = (type, x, y, hp = 300) => ({ type, hp, maxhp: hp, tx: x, ty: y, nx: x, ny: y, x, y, z: 0, prog: 0, moving: false, speed: 1.6, stun: 9, slow: 0, poison: 0, ptick: 1, fly: null, face: 1, flash: 0, dead: false, deadT: 0, seed: 0, door: [0, 4], lastDir: 1 });
    const res = {};
    // 相性: 重装兵に火柱（1.5倍）と落石（0.6倍）
    G.mana = 999; A.placeTrap(2, 1, 'fire'); G.traps.get('2,1').cd = 0; const h1 = foe('heavy', 2, 1); G.foes.push(h1); A.triggerAt(2, 1, h1, false);
    res.相性_火柱 = 300 - h1.hp; res.表示 = G.texts.map(t => t.text).filter(t => /効いた|いまひとつ/.test(t)).join(',');
    // 合成: 火柱の上に落石
    G.mana = 999; A.placeTrap(2, 1, 'rock'); const tr = G.traps.get('2,1'); res.合成 = tr.type + ':' + tr.name + ':' + tr.parts.join('+');
    tr.cd = 0; const h2 = foe('knight', 2, 1); G.foes.push(h2); A.triggerAt(2, 1, h2, false); for (let i = 0; i < 30; i++) A.update(1 / 30);
    res.合成ダメージ = 300 - h2.hp; G.foes.length = 0;
    // 火薬樽: 踏んだ直後は無傷、1秒後に爆発
    G.mana = 999; A.placeTrap(9, 8, 'keg'); G.traps.get('9,8').cd = 0; const t1 = foe('thief', 9, 8); G.foes.push(t1); A.triggerAt(9, 8, t1, false);
    res.樽_直後 = 300 - t1.hp; for (let i = 0; i < 40; i++) A.update(1 / 30); res.樽_1秒後 = 300 - t1.hp; G.foes.length = 0;
    // 宝物: 逃げる子の足もと（拾う）と、罠のマス（罠で取る）
    const h = G.hero; Object.assign(h, { moving: false, x: h.tx, y: h.ty, idle: 9, think: 9 }); G.items.push({ x: h.tx, y: h.ty, kind: 'gem', t: 0, life: 9 }); const s0 = G.score; A.update(1 / 30); res.宝物_拾う = G.score - s0;
    G.mana = 999; A.placeTrap(12, 7, 'bear'); if (!G.traps.get('12,7')) return { 失敗: G.msg, foes: G.foes.map(f => [f.type, Math.round(f.x), Math.round(f.y)]).join(' '), hero: [G.hero.tx, G.hero.ty].join(',') }; G.traps.get('12,7').cd = 0; G.items.push({ x: 12, y: 7, kind: 'coin', t: 0, life: 9 }); const k1 = foe('knight', 12, 7); G.foes.push(k1); A.triggerAt(12, 7, k1, false); res.宝物_罠 = G.itemsGot;
    // 倒れた敵: 歩かない・約1.5秒で消える
    let sx = 0, sy = 0; for (let y = 1; y < 9 && !sx; y++) for (let x = 1; x < 14; x++) if (A.canPlace(x, y) && !G.traps.has(x + ',' + y) && Math.abs(x - G.hero.tx) + Math.abs(y - G.hero.ty) > 2 && x > 3 && x < 8) { sx = x; sy = y; break; }
    G.mana = 999; A.placeTrap(sx, sy, 'fire'); G.traps.get(sx + ',' + sy).cd = 0; const d = foe('knight', sx, sy, 3); d.stun = 0; G.foes.push(d); A.triggerAt(sx, sy, d, false);
    const x0 = Math.round(d.x); for (let i = 0; i < 30; i++) A.update(1 / 30); res.倒れ_1秒後 = `動いた=${Math.abs(d.x - x0) > .5}（false が正しい） 残り=${d.down > 0}`;
    for (let i = 0; i < 45; i++) A.update(1 / 30); res.倒れ_2秒半後 = `消えた=${d.dead}`;
    return res;
  });
  Object.assign(out, r);
  // エディット: 壁を置いて保存して試す
  await p.evaluate(() => { const W = window.__wanakan; W.G.state = 'title'; });
  await p.evaluate(() => document.querySelector('#btnEdit').click());
  await p.waitForTimeout(300);
  ok('エディット状態', await p.evaluate(() => window.__wanakan.G.state));
  await p.evaluate(() => { const A = window.__wanakan.api; A.editTool('O'); A.editAt(4, 4); A.editTool('#'); A.editAt(5, 4); });
  await p.screenshot({ path: path.join(__dirname, 'out', 'editor.png') });
  ok('エディットの置いたマス', await p.evaluate(() => window.__wanakan.api.customRow(4)));
  await p.click('#editTest'); await p.click('#pick-lily'); await p.click('#btnNext1'); await p.click('#btnNext2'); await p.click('#btnBegin');
  ok('自作の部屋で開始', await p.evaluate(() => `${window.__wanakan.G.state} ${window.__wanakan.api.mapName()}`));
  ok('保存', await p.evaluate(() => (JSON.parse(localStorage.getItem('trapoflily-custom')) || {}).rows[4]));
  await p.evaluate(() => { const W = window.__wanakan, G = W.G; G.intro = null; W.api.beginDefense(); G.phase = 3; G.spawnQueue = []; G.foes.length = 0; });
  await p.waitForTimeout(4200);
  ok('自作の部屋クリア', await p.evaluate(() => document.getElementById('rTitle').textContent + ' 実績=' + !!JSON.parse(localStorage.getItem('trapoflily-ach') || '{}').editor));
  // 実績の画面
  await p.evaluate(() => window.__wanakan.api.showAch());
  await p.screenshot({ path: path.join(__dirname, 'out', 'achievements.png') });
  ok('実績の数', await p.evaluate(() => document.getElementById('achCount').textContent));
  console.log(JSON.stringify(out, null, 1));
  console.log('pageerror:', errs.length ? errs : 'なし');
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
