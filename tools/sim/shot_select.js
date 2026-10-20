// 支度の画面とプレイ中の画面のスクリーンショット（PC とスマホ縦・横・小さいスマホ）
// 支度は 1 逃げる子（押すと詳しく→決める） 2 罠（アイコンを押すと詳しく→持っていく／外す／入れ替える）
// どの画面でも支度の枠が画面からはみ出さないことも確かめる
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const path = require('path');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const errors = [], bad = [];
  const fits = async (p, name, what) => {
    const r = await p.evaluate(() => {
      const pn = document.querySelector('#ovSelect .panel'), rc = pn.getBoundingClientRect();
      const sh = [...document.querySelectorAll('.sheetcard')].find(e => e.offsetParent), sr = sh && sh.getBoundingClientRect();
      return { out: rc.top < -1 || rc.bottom > innerHeight + 1 || (sr && (sr.top < -1 || sr.bottom > innerHeight + 1)), sw: document.documentElement.scrollWidth - innerWidth };
    });
    if (r.out || r.sw > 0) bad.push(`${name} ${what} ${JSON.stringify(r)}`);
  };
  for (const [name, vp] of [['pc', { width: 1100, height: 1000 }], ['pcl', { width: 1366, height: 600 }], ['m', { width: 390, height: 844 }], ['ml', { width: 852, height: 393 }], ['se', { width: 375, height: 667 }]]) {
    const mob = vp.width < 1000 || vp.height < 500;
    const p = await (await browser.newContext({ viewport: vp, isMobile: mob, hasTouch: mob })).newPage();
    p.on('pageerror', e => errors.push(String(e)));
    await p.goto(process.env.GAME_URL || 'http://127.0.0.1:8766/src/game.html');
    await p.evaluate(() => localStorage.clear()); await p.reload();
    await p.click('#btnStart');
    await p.screenshot({ path: path.join(__dirname, 'out', `select_${name}.png`) }); await fits(p, name, '逃げる子');
    await p.click('#pick-cecil');
    await p.screenshot({ path: path.join(__dirname, 'out', `select_${name}_char.png`) }); await fits(p, name, '逃げる子の説明');
    await p.click('#btnNext1');
    // いま持っている4つを外して、跳ね床・振り子刃・トラバサミ・落石を選び直す
    for (let i = 0; i < 4; i++) { await p.click('#loadSlots .lslot:not(.empty) >> nth=0'); await p.click('#tsToggle'); }
    const empty = await p.evaluate(() => ({ count: document.getElementById('pickCount').textContent, disabled: document.getElementById('btnBegin').disabled }));
    for (const t of ['spring', 'blade', 'bear']) { await p.click('#pickt-' + t); await p.click('#tsToggle'); }
    await p.click('#pickt-rock');
    await p.screenshot({ path: path.join(__dirname, 'out', `select_${name}_trap.png`) }); await fits(p, name, '罠の説明');
    await p.click('#tsToggle');
    await p.screenshot({ path: path.join(__dirname, 'out', `select_${name}_traps.png`) }); await fits(p, name, '罠');
    // 5つ目は入れ替え: 火柱を選ぶと「どれと入れ替える？」が出る。振り子刃と入れ替える
    await p.click('#pickt-fire');
    const swap = await p.evaluate(() => ({ swap: !document.getElementById('tsSwap').hidden, toggle: !document.getElementById('tsToggle').hidden }));
    await p.click('#tsSwapSlots .lslot[data-t="blade"]');
    const st = await p.evaluate(() => ({ count: document.getElementById('pickCount').textContent, disabled: document.getElementById('btnBegin').disabled, fav: document.querySelector('#pickt-rock').classList.contains('favt') }));
    console.log(name, JSON.stringify({ empty, swap, st }));
    if (empty.count !== '0/4' || !empty.disabled || !swap.swap || swap.toggle || st.count !== '4/4' || st.disabled || !st.fav) bad.push(`${name} 支度の動き ${JSON.stringify({ empty, swap, st })}`);
    await p.click('#btnBegin');
    await p.waitForTimeout(500);
    await p.evaluate(() => { const A = window.__wanakan.api; A.beginDefense(); });
    await p.waitForTimeout(6000);
    await p.mouse.move(vp.width / 2, 300);
    await p.waitForTimeout(300);
    await p.screenshot({ path: path.join(__dirname, 'out', `play_${name}.png`), fullPage: true });
    const g = await p.evaluate(() => { const G = window.__wanakan.G; return { char: G.char, loadout: G.loadout, fav: [...document.querySelectorAll('.slot.fav .n')].map(n => n.textContent), slots: [...document.querySelectorAll('.slot .n')].map(n => n.textContent) }; });
    console.log(name, JSON.stringify(g));
    if (g.char !== 'cecil' || g.loadout.join() !== 'bear,spring,rock,fire') bad.push(`${name} 始めた支度 ${JSON.stringify(g)}`);
  }
  console.log('pageerror:', errors.length ? errors : 'なし');
  console.log('不合格:', bad.length ? bad : 'なし');
  await browser.close();
  if (errors.length || bad.length) process.exit(1);
})().catch(e => { console.error(e); process.exit(1); });
