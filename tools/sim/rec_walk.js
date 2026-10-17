// 盤面で歩く様子を撮って GIF にする（歩行・停止・方向転換）。止まったときにマスの中心にいるかも確かめる
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const path = require('path');
const { execFileSync } = require('child_process');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const p = await (await browser.newContext({ viewport: { width: 1100, height: 1000 }, deviceScaleFactor: 2 })).newPage();
  const errors = []; p.on('pageerror', e => errors.push(String(e)));
  await p.goto(process.env.GAME_URL || 'http://127.0.0.1:8766/index.html');
  const who = process.argv[2] || 'lily';
  await p.evaluate(who => { window.__wanakan.api.startRun(who, ['bear', 'spring', 'rock', 'fire']); }, who);
  await p.evaluate(() => window.__wanakan.api.beginDefense());
  await p.waitForTimeout(3000);
  const dir = path.join(__dirname, 'out', 'rec'); require('fs').mkdirSync(dir, { recursive: true });
  const log = []; let off = 0;
  for (let i = 0; i < 60; i++) {
    const s = await p.evaluate(() => { const G = window.__wanakan.G, h = G.hero, r = document.getElementById('cv').getBoundingClientRect(); return { x: r.left + h.x * r.width / 14, y: r.top + h.y * r.height / 9, s: r.width / 14, moving: h.moving, facing: h.facing, walk: h.walk || 0, onCenter: !h.moving ? (h.x === h.tx && h.y === h.ty) : null }; });
    log.push(`${s.moving ? 'walk' : 'stop'} f${s.facing} frame${Math.floor(s.walk / .34) % 4}${s.onCenter === false ? ' OFF-CENTER' : ''}`);
    if (s.onCenter === false) off++;
    await p.screenshot({ path: path.join(dir, `f${String(i).padStart(3, '0')}.png`), clip: { x: s.x - s.s * 2, y: s.y - s.s * 2, width: s.s * 4, height: s.s * 3.2 } });
    await p.waitForTimeout(90);
  }
  console.log(log.join(' | '));
  console.log('止まったときに中心からずれた回数:', off);
  console.log('pageerror:', errors.length ? errors : 'なし');
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
