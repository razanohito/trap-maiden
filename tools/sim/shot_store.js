// Steam のストア用スクリーンショット（1920x1080）を日本語・英語で撮る → steam/screenshots/
// 使い方: python -m http.server 8766 --bind 127.0.0.1 → node tools/sim/shot_store.js
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const path = require('path');
const OUT = path.join(__dirname, '..', '..', 'steam', 'screenshots');
(async () => {
  const b = await chromium.launch({ channel: 'chrome', headless: true });
  const errs = [];
  for (const lang of ['en', 'ja']) {
    const p = await (await b.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1.5 })).newPage();
    p.on('pageerror', e => errs.push(String(e)));
    await p.goto('http://127.0.0.1:8766/index.html');
    await p.evaluate(l => { localStorage.clear(); localStorage.setItem('trapoflily-lang', l); localStorage.setItem('trapoflily-stages', JSON.stringify({ open: 23, rec: Object.fromEntries(Array.from({ length: 22 }, (_, i) => [i + 1, { stars: 1 + (i * 7) % 3, best: 5000 + i * 900 }])) })); }, lang);
    await p.reload(); await p.waitForTimeout(600);
    const shot = async name => { await p.screenshot({ path: path.join(OUT, `${lang}_${name}.png`) }); };
    await shot('01_title');
    // 支度
    await p.click('#btnStart'); await p.waitForTimeout(300); await shot('02_select');
    // 夜の戦い: 第7夜（東の書庫）相当で、罠を並べて侵入者を呼ぶ
    const night = async (mode, n, ch, traps, plan, wait, name) => {
      await p.evaluate(([mode, n, ch, traps, plan]) => {
        const W = window.__wanakan, A = W.api; A.setRun(mode, n); A.startRun(ch, traps); const G = W.G; G.intro = null; G.mana = 9999;
        for (const [x, y, t, d] of plan) { if (A.canPlace(x, y)) A.placeTrap(x, y, t); const tr = G.traps.get(x + ',' + y); if (tr && d != null) tr.dir = d; }
        A.beginDefense(); G.phase = 2;
      }, [mode, n, ch, traps, plan]);
      await p.evaluate(() => { const G = window.__wanakan.G; G.mana = 9999; });
      for (let i = 0; i < wait; i++) { await p.waitForTimeout(500); await p.evaluate(() => { const G = window.__wanakan.G; G.mana = Math.max(G.mana, 200); G.hp = Math.max(G.hp, 2); }); }
      await shot(name);
    };
    await night('stage', 18, 'mina', ['fire', 'bear', 'rock', 'keg'], [[4, 4, 'bear'], [5, 4, 'fire'], [10, 5, 'rock'], [9, 3, 'keg'], [6, 6, 'fire'], [4, 4, 'rock']], 14, '03_night');
    await night('stage', 33, 'cecil', ['spring', 'rock', 'blade', 'ice'], [[3, 3, 'spring', 1], [11, 6, 'blade', 3], [7, 5, 'ice'], [9, 2, 'rock'], [5, 7, 'rock']], 16, '04_night2');
    await night('challenge', 9, 'noel', ['ice', 'bell', 'caltrop', 'vortex'], [[7, 4, 'bell'], [6, 4, 'vortex'], [8, 5, 'ice'], [5, 3, 'caltrop']], 18, '05_night3');
    // ステージ選択・遊び方
    await p.goto('http://127.0.0.1:8766/index.html'); await p.waitForTimeout(400);
    await p.click('#btnStage'); await p.waitForTimeout(300); await shot('06_stages');
    await p.goto('http://127.0.0.1:8766/index.html'); await p.waitForTimeout(400);
    await p.click('#btnHowto'); await p.click('#helpNext'); await p.click('#helpNext'); await p.click('#helpNext'); await p.waitForTimeout(300); await shot('07_help');
    await p.goto('http://127.0.0.1:8766/index.html'); await p.waitForTimeout(400);
    await p.click('#btnEdit'); await p.waitForTimeout(300); await shot('08_editor');
    await p.context().close();
  }
  console.log('pageerror:', errs.length ? errs : 'なし');
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
