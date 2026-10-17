// 絵の入り方を確認する（タイトルの立ち絵、盤面の3方向、結果画面）。ビルド後の index.html を開く
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const path = require('path');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const errors = [];
  for (const [name, vp] of [['pc', { width: 1100, height: 1000 }], ['m', { width: 390, height: 844 }]]) {
    const p = await (await browser.newContext({ viewport: vp })).newPage();
    p.on('pageerror', e => errors.push(String(e)));
    await p.goto(process.env.GAME_URL || 'http://127.0.0.1:8766/index.html');
    await p.waitForTimeout(600);
    await p.screenshot({ path: path.join(__dirname, 'out', `art_title_${name}.png`), fullPage: true });
    await p.click('#btnStart'); await p.click('#pick-lily'); await p.click('#btnBegin');
    await p.evaluate(() => window.__wanakan.api.beginDefense());
    await p.waitForTimeout(7000);
    // 向きを順に変えて盤面の絵を確かめる
    for (const f of [2, 1, 0, 3]) {
      await p.evaluate(f => { const G = window.__wanakan.G; G.hero.facing = f; }, f);
      await p.waitForTimeout(60);
      const box = await p.evaluate(() => { const G = window.__wanakan.G, r = document.getElementById('cv').getBoundingClientRect(); return { x: r.left + (G.hero.x + .5) * r.width / 15, y: r.top + (G.hero.y + .5) * r.height / 10, s: r.width / 15 }; });
      await p.screenshot({ path: path.join(__dirname, 'out', `art_hero_${name}_${f}.png`), clip: { x: Math.max(0, box.x - box.s * 1.5), y: Math.max(0, box.y - box.s * 2), width: box.s * 3, height: box.s * 3 } });
    }
    await p.screenshot({ path: path.join(__dirname, 'out', `art_play_${name}.png`) });
    await p.evaluate(() => { const G = window.__wanakan.G; G.hp = 1; G.hero.inv = 0; for (const f of G.foes) { f.x = G.hero.x; f.y = G.hero.y; f.stun = 0; } });
    await p.waitForTimeout(1500);
    await p.screenshot({ path: path.join(__dirname, 'out', `art_over_${name}.png`), fullPage: true });
    console.log(name, await p.evaluate(() => ({ state: window.__wanakan.G.state, kvTitle: !document.getElementById('kvTitle').hidden, kvOver: !document.getElementById('kvOver').hidden })));
  }
  console.log('pageerror:', errors.length ? errors : 'なし');
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
