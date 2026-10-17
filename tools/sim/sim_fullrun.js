// 全10夜を通しで遊んだときの時間と、最後の終わり方（館を守り抜いた！）を確かめる
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const p = await (await browser.newContext({ viewport: { width: 1100, height: 950 } })).newPage();
  const errors = [];
  p.on('pageerror', e => errors.push(String(e)));
  await p.route('**/game.html', async route => {
    const res = await route.fetch(); let body = await res.text();
    body = body.replace("if (location.hostname === '127.0.0.1') window.__wanakan", "window.__sim = { update, startWave, beginDefense, setP: v => paused = v, get G(){return G}, set G(v){G=v}, makeRun }; window.__wanakan");
    route.fulfill({ response: res, body, headers: { ...res.headers(), 'content-type': 'text/html; charset=utf-8' } });
  });
  await p.goto(process.env.GAME_URL || 'http://127.0.0.1:8766/src/game.html');
  await p.click('#btnStart');
  const R = await p.evaluate(() => {
    const S = window.__sim; S.setP(true);
    const G = S.G; G.hp = 999; G.up.smart = 3; G.up.limit = 3;
    const layout = [['bear', 3, 4, 1], ['rock', 4, 3, 1], ['spring', 11, 5, 1], ['fire', 10, 3, 1], ['bear', 7, 2, 1], ['spring', 7, 7, 1], ['bear', 12, 6, 1]];
    for (const [type, x, y, dir] of layout) G.traps.set(x + ',' + y, { type, x, y, dir, cd: 0, cdMax: 1, snap: 0, anim: 0, at: 0, bonus: false });
    const nights = [];
    for (let n = 1; n <= 10; n++) {
      if (n > 1) { S.startWave(n); }
      G.hp = 999; // ショップで最大体力に戻るので毎夜もどす（時間を測るため）
      const t0 = G.time;
      // 準備はプレイヤーが 10 秒で終える想定
      for (let i = 0; i < 60 * 10; i++) S.update(1 / 60);
      S.setP(false); S.beginDefense(); S.setP(true);
      let guard = 0;
      while (G.state === 'play' && guard++ < 60 * 200) { S.update(1 / 60); if (G.clearT >= 0 && G.clearT < .05) break; }
      nights.push({ n, sec: Math.round(G.time - t0), result: G.bannerTitle });
      // 夜明け後の処理を進める（最後の夜は gameOver(true)、それ以外はショップ）
      for (let i = 0; i < 60 * 3 && G.state === 'play'; i++) S.update(1 / 60);
      if (G.state === 'shop') G.state = 'play';
    }
    return { nights, total: Math.round(G.time), state: G.state, score: G.score };
  });
  await p.waitForTimeout(800);
  const over = await p.evaluate(() => ({ title: document.getElementById('rTitle').textContent, wave: document.getElementById('rWave').textContent, time: document.getElementById('rTime').textContent, best: document.getElementById('rBest').textContent, shown: !document.getElementById('ovOver').hidden }));
  console.log(JSON.stringify(R, null, 1));
  console.log(JSON.stringify(over, null, 1));
  console.log('pageerror:', errors.length ? errors : 'なし');
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
