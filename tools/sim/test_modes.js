// トレーニングと「無限の夜」（全40クリアで開く）を確かめる
// 使い方: python -m http.server 8766 --bind 127.0.0.1（リポジトリ直下）→ node tools/sim/test_modes.js
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const path = require('path');
(async () => {
  const b = await chromium.launch({ channel: 'chrome', headless: true });
  const p = await (await b.newContext({ viewport: { width: 393, height: 852 }, hasTouch: true, isMobile: true })).newPage();
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto(process.env.GAME_URL || 'http://127.0.0.1:8766/index.html');
  await p.evaluate(() => localStorage.clear()); await p.reload(); await p.waitForTimeout(300);
  const out = {};
  const click = async s => { await p.evaluate(q => document.querySelector(q).click(), s); await p.waitForTimeout(150); };
  out.最初は無限の夜が隠れている = await p.evaluate(() => document.getElementById('btnEndless').hidden);
  // トレーニング: 練習の一覧 → 全部の練習が始まるか → 1つを目標達成で一覧へ戻るか
  await click('#btnTrain');
  out.練習の数 = await p.evaluate(() => document.querySelectorAll('.lesson').length);
  await p.screenshot({ path: path.join(__dirname, 'out', 'mode_lessons.png') });
  out.練習の開始 = await p.evaluate(() => { const r = []; document.querySelectorAll('.lesson[data-i]').forEach((b, i) => { b.click(); const G = window.__wanakan.G; r.push(`${G.state}:${G.loadout.length}`); document.querySelector('#btnTrain'); window.__wanakan.api.showTrain(); }); return r.join(' '); });
  await p.evaluate(() => document.querySelector('.lesson[data-i="0"]').click()); await p.waitForTimeout(200);
  out.練習中の目標 = await p.evaluate(() => { const W = window.__wanakan, G = W.G; G.intro = null; document.getElementById('btnGo').click(); G.bestCombo = 3; W.api.update(1 / 30); return document.getElementById('dockHint').textContent; });
  await p.waitForTimeout(3200);
  out.達成後 = await p.evaluate(() => [...document.querySelectorAll('.overlay')].filter(o => !o.hidden).map(o => o.id).join() + ' ' + localStorage.getItem('trapoflily-lessons'));
  await p.evaluate(() => document.querySelector('#lessonFree').click()); await p.waitForTimeout(150);
  await click('#btnNext1'); await click('#btnNext2'); await click('#btnBegin'); await p.waitForTimeout(400);
  await p.evaluate(() => { window.__wanakan.G.intro = null; });
  await click('#btnGo'); await click('#btnGo');
  out.トレーニング = await p.evaluate(() => { const G = window.__wanakan.G; return `状態=${G.state} 侵入者=${G.foes.length} 魔力=${Math.round(G.mana)}/${window.__wanakan.api.stat.maxMana()} ボタン=${document.getElementById('goText').textContent}`; });
  await p.evaluate(() => { const G = window.__wanakan.G; G.mana = 0; for (let i = 0; i < 300; i++) window.__wanakan.api.update(1 / 30); });
  out.トレーニング_10秒後 = await p.evaluate(() => { const G = window.__wanakan.G; return `体力=${G.hp} 魔力=${Math.round(G.mana)} 状態=${G.state}`; });
  await p.screenshot({ path: path.join(__dirname, 'out', 'mode_training.png') });
  await click('#btnPause');
  out.部屋を変えるボタン = await p.evaluate(() => !document.getElementById('btnRoom').hidden);
  await click('#btnRoom'); out.部屋が変わった = await p.evaluate(() => window.__wanakan.api.mapName());
  // 全40クリア → 無限の夜が開く
  await p.evaluate(() => { const rec = {}; for (let i = 1; i <= 40; i++) rec[i] = { best: 1000, stars: 1 }; localStorage.setItem('trapoflily-stages', JSON.stringify({ open: 40, rec })); });
  await p.reload(); await p.waitForTimeout(300);
  out.全クリ後に無限の夜 = await p.evaluate(() => !document.getElementById('btnEndless').hidden);
  await p.screenshot({ path: path.join(__dirname, 'out', 'mode_title_endless.png') });
  await click('#btnEndless'); await click('#btnNext1'); await click('#btnNext2'); await click('#btnBegin'); await p.waitForTimeout(400);
  out.無限の夜 = await p.evaluate(() => { const W = window.__wanakan, A = W.api, G = W.G; G.intro = null; A.beginDefense(); A.setPaused(true);
    for (let i = 0; i < 90; i++) A.update(1 / 30);
    const f = G.foes[0]; const hp0 = f.hp; A.triggerAt(Math.round(f.x), Math.round(f.y), f, false); G.mana = 999;
    f.hp; // 体力は減らない
    return `部屋=${A.mapName()} 侵入者=${G.foes.length} 体力そのまま=${f.hp === hp0} 残り=${Math.round(G.nightT)}秒`; });
  out.無限の夜_終わり = await p.evaluate(() => { const W = window.__wanakan, A = W.api, G = W.G; G.hp = 99; G.bestCombo = 12; for (let i = 0; i < 30 * 125; i++) { A.update(1 / 30); if (G.state !== 'play') break; } return `状態=${G.state}`; });
  await p.waitForTimeout(600);
  out.結果 = await p.evaluate(() => `${document.getElementById('rTitle').textContent} / ${document.getElementById('rWaveL').textContent} ${document.getElementById('rWave').textContent} / 記録=${localStorage.getItem('trapoflily-endless')}`);
  await p.screenshot({ path: path.join(__dirname, 'out', 'mode_endless_result.png') });
  console.log(JSON.stringify(out, null, 1));
  console.log('pageerror:', errs.length ? errs : 'なし');
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
