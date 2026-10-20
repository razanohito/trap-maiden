// スマホのプレイ中に遊び方を開いて、次へ・閉じるが押せるか（縦の小さい画面と横）
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const path = require('path');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const errors = [];
  for (const [name, vp] of [['320x568', { width: 320, height: 568 }], ['375x667', { width: 375, height: 667 }], ['844x390', { width: 844, height: 390 }]]) {
    const ctx = await browser.newContext({ viewport: vp, isMobile: true, hasTouch: true });
    const p = await ctx.newPage();
    p.on('pageerror', e => errors.push(String(e)));
    await p.goto(process.env.GAME_URL || 'http://127.0.0.1:8766/index.html');
    await p.tap('#btnStart'); await p.tap('#btnNext1'); await p.tap('#btnNext2'); await p.tap('#btnBegin'); await p.waitForTimeout(500);
    await p.tap('#btnPause'); const helpVisible = await p.isVisible('#btnHelp'); // 遊び方はメニューの中
    await p.tap('#btnHelp');
    await p.waitForTimeout(200);
    for (let i = 0; i < 3; i++) { await p.tap('#helpNext'); }
    const page = await p.textContent('#helpTitle');
    await p.screenshot({ path: path.join(__dirname, 'out', `helpm_${name}.png`) });
    await p.tap('#helpClose');
    const st = await p.evaluate(() => ({ helpHidden: document.getElementById('ovHelp').hidden, state: window.__wanakan.G.state }));
    console.log(name, JSON.stringify({ helpVisible, page, ...st }));
    await ctx.close();
  }
  console.log('pageerror:', errors.length ? errors : 'なし');
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
