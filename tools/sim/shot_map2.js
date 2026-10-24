// 第6夜で東の書庫に移るか、書庫で遊べるかを確かめる
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const path = require('path');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const errors = [];
  const p = await (await browser.newContext({ locale: 'ja-JP', viewport: { width: 1100, height: 1000 } })).newPage();
  p.on('pageerror', e => errors.push(String(e)));
  await p.goto(process.env.GAME_URL || 'http://127.0.0.1:8766/index.html');
  const r = await p.evaluate(() => {
    const A = window.__wanakan.api; A.startRun('noel', ['bear', 'spring', 'ice', 'warp']); A.setPaused(true);
    let G = window.__wanakan.G;
    G.traps.set('3,4', { type: 'bear', x: 3, y: 4, dir: 1, cd: 0, cdMax: 1, snap: 0, anim: 0, at: 0, bonus: false, paid: 20 });
    A.startWave(6); G = window.__wanakan.G;
    const out = { doors: A.doors(), traps: G.traps.size, hero: [G.hero.tx, G.hero.ty], devices: G.devices.map(d => d.type + '@' + d.x + ',' + d.y), banner: G.bannerSub };
    // 書庫で 40 秒遊ばせる（体力は多め）
    G.hp = 99; A.setPaused(false); A.beginDefense(); A.setPaused(true);
    for (let i = 0; i < 30 * 40; i++) A.update(1 / 30);
    out.after = { state: G.state, phase: G.phase, foes: G.foes.length, hero: [G.hero.tx, G.hero.ty], spawnedFrom: [...new Set(G.foes.map(f => f.door.join(',')))] };
    return out;
  });
  console.log(JSON.stringify(r, null, 1));
  await p.waitForTimeout(300);
  await p.evaluate(() => window.__wanakan.api.setPaused(false));
  await p.waitForTimeout(1500);
  await p.screenshot({ path: path.join(__dirname, 'out', 'map2.png') });
  console.log('pageerror:', errors.length ? errors : 'なし');
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
