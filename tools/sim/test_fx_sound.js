// 効果音をすべて鳴らしてエラーが出ないか、絵のエフェクト（火柱・氷・落石・火花・跳ね床）が出るかを確かめる
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const path = require('path');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--autoplay-policy=no-user-gesture-required'] });
  const p = await (await browser.newContext({ locale: 'ja-JP', viewport: { width: 1100, height: 1000 }, deviceScaleFactor: 2 })).newPage();
  const errors = []; p.on('pageerror', e => errors.push(String(e)));
  await p.goto(process.env.GAME_URL || 'http://127.0.0.1:8766/index.html');
  await p.click('#btnStart');
  const r = await p.evaluate(async () => {
    const A = window.__wanakan.api; A.startRun('lily', ['bear', 'spring', 'ice', 'fire']); A.setPaused(true);
    const G = window.__wanakan.G; G.hp = 99;
    // 罠を置いて侵入者に踏ませる
    const place = (type, x, y, dir = 1) => G.traps.set(x + ',' + y, { type, x, y, dir, cd: 0, cdMax: 1, snap: 0, anim: 0, at: 0, bonus: false, paid: 20 });
    place('bear', 2, 3); place('spring', 4, 3); place('ice', 6, 6); place('fire', 9, 6); place('rock', 11, 3);
    const foe = (x, y, nx, ny) => { G.foes.push({ type: 'knight', hp: 400, maxhp: 400, tx: x, ty: y, nx, ny, x, y, z: 0, prog: .95, moving: true, speed: 1.6, stun: 0, slow: 0, poison: 0, ptick: 1, fly: null, face: 1, flash: 0, dead: false, deadT: 0, seed: 0, door: [0, 4], lastDir: 1 }); };
    foe(1, 3, 2, 3); foe(3, 3, 4, 3); foe(5, 6, 6, 6); foe(8, 6, 9, 6); foe(10, 3, 11, 3);
    for (let i = 0; i < 8; i++) A.update(1 / 30);
    const kinds = [...new Set(G.fx.map(f => f.type === 'spr' ? 'spr:' + f.key : f.type))];
    return { kinds };
  });
  await p.waitForTimeout(50);
  await p.screenshot({ path: path.join(__dirname, 'out', 'fx_ingame.png') });
  const snd = await p.evaluate(() => { const S = window.__wanakan.api.sfx; const done = []; for (const k of Object.keys(S)) { try { k === 'combo' ? S[k](5) : S[k](); done.push(k); } catch (e) { done.push(k + ':ERR ' + e.message); } } return done; });
  console.log(JSON.stringify(r)); console.log('鳴らした効果音:', snd.length, snd.filter(s => s.includes('ERR')));
  console.log('pageerror:', errors.length ? errors : 'なし');
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
