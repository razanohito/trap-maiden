// チュートリアル「はじめての夜」を、実際のタップで最後まで進められるか確かめる（縦持ち・横持ち）
// 使い方: python -m http.server 8766 --bind 127.0.0.1（リポジトリ直下）→ node tools/sim/test_guide.js
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const path = require('path');
(async () => {
  const b = await chromium.launch({ channel: 'chrome', headless: true });
  const errs = [];
  for (const [nm, w, h] of [['p', 393, 852], ['l', 852, 393]]) {
    const p = await (await b.newContext({ locale: 'ja-JP', viewport: { width: w, height: h }, hasTouch: true, isMobile: true })).newPage();
    p.on('pageerror', e => errs.push(nm + ': ' + e));
    await p.goto(process.env.GAME_URL || 'http://127.0.0.1:8766/index.html');
    await p.evaluate(() => localStorage.clear()); await p.reload(); await p.waitForTimeout(300);
    const log = [];
    log.push('タイトルの印=' + await p.evaluate(() => document.getElementById('btnTrain').classList.contains('new')));
    await p.tap('#btnTrain'); await p.waitForTimeout(200);
    await p.tap('.lesson[data-i="0"]'); await p.waitForTimeout(500);
    const step = () => p.evaluate(() => window.__wanakan.G.guide ? window.__wanakan.G.guide.i : -1);
    const tapTile = async key => { const r = await p.evaluate(k => { const g = window.__wanakan.G.guide, [x, y] = g[k], cv = document.getElementById('cv').getBoundingClientRect(); const s = cv.width / window.__wanakan.api.view().VW; return [cv.left + (x * 48 + 24 - window.__wanakan.api.view().VX) * s, cv.top + (y * 48 + 24 - window.__wanakan.api.view().VY) * s]; }, key); await p.touchscreen.tap(r[0], r[1]); await p.waitForTimeout(250); };
    log.push('始め=' + await step());
    await p.tap('.slot[data-type="bear"]'); await p.waitForTimeout(250); log.push('トラバサミを選ぶ→' + await step());
    await tapTile('bear'); log.push('置く→' + await step());
    await p.tap('.slot[data-type="rock"]'); await p.waitForTimeout(150); await tapTile('rock'); log.push('落石→' + await step());
    await p.screenshot({ path: path.join(__dirname, 'out', `guide_${nm}.png`) });
    await p.tap('#btnGo'); await p.waitForTimeout(300); log.push('迎える→' + await step());
    for (let i = 0; i < 40 && await step() === 4; i++) await p.waitForTimeout(500);
    log.push('連続→' + await step() + ' 最大連続=' + await p.evaluate(() => window.__wanakan.G.bestCombo));
    await tapTile('ch'); log.push('シャンデリア→' + await step());
    await p.waitForTimeout(7000);
    log.push('終わり: ' + await p.evaluate(() => [...document.querySelectorAll('.overlay')].filter(o => !o.hidden).map(o => o.id).join() + ' 記録=' + localStorage.getItem('trapoflily-lessons')));
    console.log(nm, log.join(' | '));
  }
  console.log('pageerror:', errs.length ? errs : 'なし');
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
