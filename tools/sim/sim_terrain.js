// 地形（トゲ・奈落）と館の仕掛け（シャンデリア・石像）の動作確認
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1100, height: 950 } });
  const p = await ctx.newPage();
  const errors = [];
  p.on('pageerror', e => errors.push(String(e)));
  await p.route('**/game.html', async route => {
    const res = await route.fetch(); let body = await res.text();
    body = body.replace("if (location.hostname === '127.0.0.1') window.__wanakan", "window.__sim = { update, startWave, beginDefense, activateDevice, setP: v => paused = v, get G(){return G}, set G(v){G=v}, makeRun }; window.__wanakan");
    route.fulfill({ response: res, body, headers: { ...res.headers(), 'content-type': 'text/html; charset=utf-8' } });
  });
  await p.goto((process.env.GAME_URL || 'http://127.0.0.1:8765/src/game.html'));
  await p.click('#btnStart');
  const R = await p.evaluate(() => {
    const S = window.__sim; S.setP(true);
    const out = {};
    const foe = (G, type, x, y) => { G.foes.push({ type, hp: 40, maxhp: 40, tx:x, ty:y, nx:x, ny:y, x, y, z:0, prog:0, moving:false, speed:1.6, stun:0, fly:null, face:1, flash:0, dead:false, deadT:0, seed:0 }); return G.foes[G.foes.length - 1]; };
    const run = (G, sec) => { for (let i = 0; i < sec * 60; i++) S.update(1 / 60); };
    // 1. 奈落: (9,7) の左 (7,7) に右向き跳ね床、敵を (6,7) から歩かせる
    let G = S.makeRun('play'); S.G = G; S.startWave(1); G.hp = 99; G.phase = 1; G.spawnQueue = []; G.phaseQ = [[], [], []];
    G.traps.set('7,7', { type:'spring', x:7, y:7, dir:1, cd:0, cdMax:1, snap:0, anim:0, at:0, bonus:false });
    let f = foe(G, 'knight', 7, 7); f.tx = 6; f.x = 6; f.nx = 7; f.moving = true; f.prog = .9;
    G.hero.tx = 12; G.hero.ty = 1;
    run(G, 1); out.pit = { dead: f.dead, kills: G.kills, at: [f.tx, f.ty], soul: G.soul };
    // 2. トゲ: (2,4) を踏ませる
    G = S.makeRun('play'); S.G = G; S.startWave(1); G.hp = 99; G.phase = 1; G.spawnQueue = []; G.phaseQ = [[], [], []]; G.nightT = 999;
    f = foe(G, 'knight', 2, 4); f.tx = 1; f.x = 1; f.nx = 2; f.moving = true; f.prog = .95;
    run(G, .3); out.spike = { hp: f.hp };
    // 3. シャンデリア (10,4): 隣 (11,5) の敵
    G = S.makeRun('play'); S.G = G; S.startWave(1); G.hp = 99; G.phase = 1; G.spawnQueue = []; G.phaseQ = [[], [], []]; G.nightT = 999;
    f = foe(G, 'knight', 11, 5); f.stun = 5;
    const ch = G.devices.find(d => d.type === 'chandelier' && d.x === 10);
    S.activateDevice(ch); run(G, .8); out.chandelier = { hp: f.hp, cd: Math.round(ch.cd), combo: G.combo };
    S.activateDevice(ch); out.chandelierAgain = G.msg;
    // 4. 石像 (3,2): 下 (3,3) の敵
    const f2 = foe(G, 'thief', 3, 3); f2.hp = 24; f2.stun = 5;
    const st = G.devices.find(d => d.type === 'statue' && d.x === 3);
    S.activateDevice(st); run(G, .1); out.statue = { hp: f2.hp, combo: G.combo };
    out.devices = G.devices.map(d => d.type + '@' + d.x + ',' + d.y);
    return out;
  });
  console.log(JSON.stringify(R, null, 1));
  // 画面: 実際に夜を進めた状態
  await p.evaluate(() => { const S = window.__sim; const G = S.makeRun('play'); S.G = G; S.startWave(3); G.up.smart = 3; G.traps.set('7,7', { type:'spring', x:7, y:7, dir:1, cd:0, cdMax:1, snap:0, anim:0, at:0, bonus:false }); G.traps.set('4,4', { type:'bear', x:4, y:4, dir:1, cd:0, cdMax:1, snap:0, anim:0, at:0, bonus:false }); S.setP(false); S.beginDefense(); });
  await p.waitForTimeout(9000);
  await p.screenshot({ path: require('path').join(__dirname, 'out', 'terrain.png') });
  await p.setViewportSize({ width: 390, height: 844 });
  await p.waitForTimeout(800);
  await p.screenshot({ path: require('path').join(__dirname, 'out', 'terrain_mobile.png'), fullPage: true });
  console.log('scrollWidth', await p.evaluate(() => document.documentElement.scrollWidth));
  console.log('pageerror:', errors.length ? errors : 'なし');
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
