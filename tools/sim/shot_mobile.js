// スマホの縦・横でプレイ画面が1画面に収まり、スクロールしないかを確かめる
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const path = require('path');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const errors = [];
  for (const [name, vp] of [['portrait', { width: 390, height: 844 }], ['landscape', { width: 844, height: 390 }]]) {
    const ctx = await browser.newContext({ viewport: vp, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
    const p = await ctx.newPage();
    p.on('pageerror', e => errors.push(String(e)));
    await p.goto(process.env.GAME_URL || 'http://127.0.0.1:8766/index.html');
    await p.tap('#btnStart'); await p.tap('#btnBegin');
    await p.waitForTimeout(800);
    await p.screenshot({ path: path.join(__dirname, 'out', `mobile_prep_${name}.png`) });
    await p.evaluate(() => window.__wanakan.api.beginDefense());
    await p.waitForTimeout(5000);
    // 盤面の中央付近をタップして罠を置く
    const r = await p.evaluate(() => { const b = document.getElementById('cv').getBoundingClientRect(); return { x: b.left, y: b.top, w: b.width, h: b.height }; });
    await p.touchscreen.tap(r.x + r.w * (5.5 / 15), r.y + r.h * (3.5 / 10));
    await p.waitForTimeout(400);
    await p.screenshot({ path: path.join(__dirname, 'out', `mobile_play_${name}.png`) });
    const m = await p.evaluate(() => {
      const de = document.documentElement, cv = document.getElementById('cv').getBoundingClientRect(), pal = document.getElementById('palette').getBoundingClientRect();
      return { scrollH: de.scrollHeight, innerH: innerHeight, scrollW: de.scrollWidth, canvas: [Math.round(cv.width), Math.round(cv.height), Math.round(cv.bottom)], paletteTop: Math.round(pal.top), paletteBottom: Math.round(pal.bottom), traps: window.__wanakan.G.traps.size, playing: document.body.classList.contains('playing') };
    });
    console.log(name, JSON.stringify(m));
    await ctx.close();
  }
  console.log('pageerror:', errors.length ? errors : 'なし');
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
