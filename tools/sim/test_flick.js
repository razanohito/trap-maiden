// スマホのフリックで矢印のある罠の向きを決められるか（指で払う操作を CDP で再現）
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const path = require('path');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 844, height: 390 }, isMobile: true, hasTouch: true });
  const p = await ctx.newPage();
  const errors = []; p.on('pageerror', e => errors.push(String(e)));
  await p.goto(process.env.GAME_URL || 'http://127.0.0.1:8766/index.html');
  await p.evaluate(() => window.__wanakan.api.startRun('lily', ['bear', 'spring', 'rock', 'blade']));
  await p.waitForTimeout(300);
  const cdp = await ctx.newCDPSession(p);
  const tile = async (x, y) => p.evaluate(([x, y]) => { const b = document.getElementById('cv').getBoundingClientRect(); return [b.left + (x + .5) * b.width / 15, b.top + (y + .5) * b.height / 10]; }, [x, y]);
  const swipe = async (x, y, dx, dy, shot) => {
    const [sx, sy] = await tile(x, y);
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: sx, y: sy }] });
    for (let i = 1; i <= 5; i++) await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: sx + dx * i / 5, y: sy + dy * i / 5 }] });
    if (shot) { await p.waitForTimeout(60); await p.screenshot({ path: path.join(__dirname, 'out', 'flick_drag.png') }); }
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    await p.waitForTimeout(80);
  };
  const st = () => p.evaluate(() => [...window.__wanakan.G.traps.values()].map(t => `${t.type}@${t.x},${t.y}:dir${t.dir}`));
  await p.evaluate(() => { window.__wanakan.G.selected = 'spring'; });
  await swipe(3, 3, 0, -40, true);      // 上へ払う → 跳ね床 上向き
  await swipe(5, 3, -40, 0);            // 左へ払う → 跳ね床 左向き
  await swipe(5, 3, 0, 40);             // 置いた跳ね床の上で下へ払う → 向きだけ下に（撤去しない）
  await p.evaluate(() => { window.__wanakan.G.selected = 'blade'; });
  await swipe(9, 6, 40, 0);             // 振り子刃 右向き
  const [tx, ty] = await tile(11, 6); await p.touchscreen.tap(tx, ty); await p.waitForTimeout(80); // タップは今の向き（右）で置く
  console.log(JSON.stringify(await st()));
  await p.evaluate(() => { window.__wanakan.G.selected = 'spring'; });
  const [ux, uy] = await tile(5, 3); await p.touchscreen.tap(ux, uy); await p.waitForTimeout(80); // 同じ向きでタップ → 撤去
  console.log('after tap on spring(5,3):', JSON.stringify(await st()));
  console.log('pageerror:', errors.length ? errors : 'なし');
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
