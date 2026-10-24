// 盤面のドット絵の確認: 部屋ごとに侵入者を歩かせて盤面を撮る → tools/sim/out/pixel_<部屋の番号>.png
// 使い方: python -m http.server 8766 --bind 127.0.0.1 → node tools/sim/shot_pixel.js [src|index] [部屋の番号 0〜7 ...]
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const path = require('path');
const OUT = path.join(__dirname, 'out');
const which = process.argv[2] || 'src';
const URL = which === 'index' ? 'http://127.0.0.1:8766/v2/index.html' : 'http://127.0.0.1:8766/src/game.html';
const rooms = (process.argv.slice(3).length ? process.argv.slice(3) : ['0', '1', '2', '3', '4', '5', '6', '7']).map(Number);
const GIRLS = ['lily', 'mina', 'noel', 'cecil'];
(async () => {
  const b = await chromium.launch({ channel: 'chrome', headless: true });
  const errs = [];
  const p = await (await b.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 2 })).newPage();
  p.on('pageerror', e => errs.push(String(e)));
  await p.goto(URL);
  await p.evaluate(() => { localStorage.clear(); localStorage.setItem('trapoflily-lang', 'ja'); localStorage.setItem('trapoflily-stages', JSON.stringify({ open: 40, rec: {} })); });
  await p.reload(); await p.waitForTimeout(800);
  for (const r of rooms) {
    const name = await p.evaluate(([r, ch]) => {
      const W = window.__wanakan, A = W.api; A.setRun('endless', 1); A.startRun(ch, ['bear', 'fire', 'keg', 'ice']); const G = W.G; G.intro = null; G.mana = 9999;
      A.setMap(r);
      let k = 0; const want = ['bear', 'fire', 'keg', 'ice'];
      for (const [x, y] of [[4, 3], [10, 6], [5, 7], [11, 2], [3, 5], [9, 4]]) if (k < 4 && A.canPlace(x, y)) A.placeTrap(x, y, want[k++]);
      A.beginDefense(); G.phase = 2; G.wave = 3;
      return A.mapName();
    }, [r, GIRLS[r % 4]]);
    for (let i = 0; i < 12; i++) { await p.waitForTimeout(400); await p.evaluate(() => { const G = window.__wanakan.G; G.mana = 9999; G.hp = Math.max(G.hp, 2); }); }
    await (await p.$('#cv')).screenshot({ path: path.join(OUT, `pixel_${r}.png`) });
    console.log('撮影', r, name);
  }
  console.log('pageerror:', errs.length ? errs : 'なし');
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
