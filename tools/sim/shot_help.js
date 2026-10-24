// 遊び方の全ページを撮る
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const path = require('path');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const errors = [];
  const p = await (await browser.newContext({ locale: 'ja-JP', viewport: { width: 1100, height: 1000 } })).newPage();
  p.on('pageerror', e => errors.push(String(e)));
  await p.goto(process.env.GAME_URL || 'http://127.0.0.1:8766/index.html');
  await p.click('#btnHowto');
  for (let i = 0; i < 9; i++) {
    const el = await p.$('#ovHelp .panel');
    await el.screenshot({ path: path.join(__dirname, 'out', `help_${i + 1}.png`) });
    await p.click('#helpNext');
  }
  await p.click('#helpClose');
  console.log('title back:', await p.evaluate(() => !document.getElementById('ovTitle').hidden));
  console.log('pageerror:', errors.length ? errors : 'なし');
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
