// 支度の画面とプレイ中の画面のスクリーンショット（PC とスマホ）
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const path = require('path');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const errors = [];
  for (const [name, vp] of [['pc', { width: 1100, height: 1000 }], ['m', { width: 390, height: 844 }], ['ml', { width: 852, height: 393 }]]) {
    const p = await (await browser.newContext({ viewport: vp })).newPage();
    p.on('pageerror', e => errors.push(String(e)));
    await p.goto(process.env.GAME_URL || 'http://127.0.0.1:8766/src/game.html');
    await p.click('#btnStart');
    await p.click('#pick-cecil');
    await p.screenshot({ path: path.join(__dirname, 'out', `select_${name}.png`), fullPage: true });
    await p.screenshot({ path: path.join(__dirname, 'out', `select_${name}_view.png`) });
    await p.click('#btnNext1');
    await p.click('#pickt-spring'); await p.click('#pickt-blade');
    await p.screenshot({ path: path.join(__dirname, 'out', `select_${name}_traps.png`), fullPage: true });
    await p.click('#btnNext2');
    await p.screenshot({ path: path.join(__dirname, 'out', `select_${name}_confirm.png`), fullPage: true });
    const st = await p.evaluate(() => ({ count: document.getElementById('pickCount').textContent, disabled: document.getElementById('btnNext2').disabled, step3: !document.getElementById('selStep3').hidden, sw: document.documentElement.scrollWidth }));
    console.log(name, JSON.stringify(st));
    await p.click('#btnBegin');
    await p.waitForTimeout(500);
    await p.evaluate(() => { const A = window.__wanakan.api; A.beginDefense(); });
    await p.waitForTimeout(6000);
    await p.mouse.move(vp.width / 2, 300);
    await p.waitForTimeout(300);
    await p.screenshot({ path: path.join(__dirname, 'out', `play_${name}.png`), fullPage: true });
    console.log(name, JSON.stringify(await p.evaluate(() => { const G = window.__wanakan.G; return { char: G.char, loadout: G.loadout, fav: [...document.querySelectorAll('.slot.fav .n')].map(n => n.textContent), slots: [...document.querySelectorAll('.slot .n')].map(n => n.textContent) }; })));
  }
  console.log('pageerror:', errors.length ? errors : 'なし');
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
