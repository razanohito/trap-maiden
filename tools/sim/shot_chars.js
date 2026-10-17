// 4人の絵の入り方を確かめる（支度の画面、盤面の正面・横、結果画面の立ち絵）
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const path = require('path');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const errors = [];
  const p = await (await browser.newContext({ viewport: { width: 1100, height: 1000 } })).newPage();
  p.on('pageerror', e => errors.push(String(e)));
  await p.goto(process.env.GAME_URL || 'http://127.0.0.1:8766/index.html');
  await p.click('#btnStart');
  await p.waitForTimeout(500);
  await p.screenshot({ path: path.join(__dirname, 'out', 'chars_select.png'), fullPage: true });
  for (const c of ['lily', 'mina', 'noel', 'cecil']) {
    await p.evaluate(c => { window.__wanakan.api.startRun(c, ['bear', 'spring', 'rock', 'fire']); }, c);
    await p.waitForTimeout(400);
    for (const f of [2, 1]) {
      await p.evaluate(f => { const G = window.__wanakan.G; G.hero.facing = f; G.hero.idle = 9; }, f);
      await p.waitForTimeout(80);
      const b = await p.evaluate(() => { const G = window.__wanakan.G, r = document.getElementById('cv').getBoundingClientRect(); return { x: r.left + (G.hero.x + .5) * r.width / 15, y: r.top + (G.hero.y + .5) * r.height / 10, s: r.width / 15 }; });
      await p.screenshot({ path: path.join(__dirname, 'out', `chars_${c}_${f}.png`), clip: { x: b.x - b.s * 1.2, y: b.y - b.s * 1.8, width: b.s * 2.4, height: b.s * 2.6 } });
    }
  }
  console.log('pageerror:', errors.length ? errors : 'なし');
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
