// すべての画面を4つの大きさで撮り、スクロールが要るか（はみ出し）を調べる
// 使い方: python -m http.server 8766 --bind 127.0.0.1（リポジトリ直下）→ node tools/sim/shot_ui.js
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const path = require('path');
const VPS = [['p', 393, 852, true], ['s', 320, 568, true], ['l', 852, 393, true], ['ls', 667, 375, true], ['pc', 1366, 768, false], ['fhd', 1920, 1080, false]];
(async () => {
  const b = await chromium.launch({ channel: 'chrome', headless: true });
  const errs = [], rows = [];
  for (const [nm, w, h, touch] of VPS) {
    const p = await (await b.newContext({ viewport: { width: w, height: h }, hasTouch: touch, isMobile: touch })).newPage();
    p.on('pageerror', e => errs.push(nm + ': ' + e));
    await p.goto(process.env.GAME_URL || 'http://127.0.0.1:8766/index.html');
    await p.evaluate(() => { localStorage.clear(); localStorage.setItem('trapoflily-stages', JSON.stringify({ open: 7, rec: { 1: { best: 9000, stars: 3 }, 2: { best: 8000, stars: 2 }, 3: { best: 7000, stars: 1 }, 4: { best: 7000, stars: 2 }, 5: { best: 7000, stars: 1 }, 6: { best: 7000, stars: 1 } } })); localStorage.setItem('trapoflily-ach', JSON.stringify({ night1: '2026-10-21', combo10: '2026-10-21', fusion: '2026-10-21' })); });
    await p.reload(); await p.waitForTimeout(400);
    const shot = async (tag) => {
      await p.waitForTimeout(250);
      const r = await p.evaluate(() => {
        const ov = [...document.querySelectorAll('.overlay')].find(o => !o.hidden);
        const panel = ov && ov.querySelector('.panel, .title');
        const over = [], W = innerWidth, H = innerHeight;
        const skip = el => el.tagName === 'IMG' || el.closest('.ph, .cf-ph, .tart, .kv');
        const outside = el => { const rc = el.getBoundingClientRect(); return rc.width && rc.height && (rc.left < -1 || rc.top < -1 || rc.right > W + 1 || rc.bottom > H + 1); };
        if (panel) for (const el of panel.querySelectorAll('*')) { if (skip(el)) continue; const rc = el.getBoundingClientRect(); const pr = panel.getBoundingClientRect(); if (rc.height && el.offsetParent && (rc.bottom > pr.bottom + 1 || rc.right > pr.right + 1)) over.push(el.id || el.className || el.tagName); }
        for (const el of document.querySelectorAll('#trapInfo, #charDetail, #helpText, .lesson, .up, .confirm, .rbig, .result, .medals, .achlist')) { if (el.offsetParent && el.scrollHeight > el.clientHeight + 2 && getComputedStyle(el).overflowY !== 'visible') over.push('切れ:' + (el.id || el.className)); else if (el.offsetParent) for (const c of el.children) { if (c.classList.contains('cf-ph')) continue; if (c.offsetParent && c.scrollHeight > c.clientHeight + 2 && getComputedStyle(c).overflow === 'hidden') over.push('切れ:' + (c.id || c.className)); } }
        for (const box of document.querySelectorAll('.up, .etool, .stg, .slot, .pick')) { if (!box.offsetParent) continue; const br = box.getBoundingClientRect(); for (const c of box.querySelectorAll('*')) { if (!c.offsetParent || c.tagName === 'CANVAS') continue; const cr = c.getBoundingClientRect(); if (cr.width && (cr.top < br.top - 1 || cr.bottom > br.bottom + 1 || (cr.left < br.left - 1 && getComputedStyle(c).textOverflow !== 'ellipsis'))) { over.push('箱の外:' + (box.id || box.className)); break; } } }
        for (const bt of document.querySelectorAll('.back, .btn, .tminor button')) { if (!bt.offsetParent) continue; const lh = parseFloat(getComputedStyle(bt).fontSize) * 1.9; const tx = [...bt.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim()); if (tx.length && bt.querySelectorAll('small, i, span').length === 0 && bt.getBoundingClientRect().height > Math.max(48, lh * 1.6)) over.push('折り返し:' + (bt.id || bt.textContent.trim().slice(0, 6))); }
        if (!ov) for (const el of document.querySelectorAll('#app .hud > .hrow *, #cv, .slot, .go, #editBar *, .dockhead')) { if (el.offsetParent && outside(el)) over.push(el.id || el.className || el.tagName); }
        return { docScroll: document.documentElement.scrollHeight > innerHeight + 1, panelScroll: panel ? panel.scrollHeight > panel.clientHeight + 1 : false, over: [...new Set(over)].slice(0, 4).join(' ') };
      });
      rows.push(`${nm} ${tag.padEnd(8)} ${r.docScroll || r.panelScroll || r.over ? 'はみ出し ' + JSON.stringify(r) : 'OK'}`);
      await p.screenshot({ path: path.join(__dirname, 'out', `ui_${nm}_${tag}.png`) });
    };
    const click = async sel => { await p.evaluate(s => document.querySelector(s).click(), sel); await p.waitForTimeout(150); };
    await shot('title');
    await click('#btnStage'); await shot('stages');
    await click('#stg-7'); await shot('sel1');
    await click('#pick-lily'); await shot('sel1dlg');
    await click('#btnNext1'); await shot('sel2');
    await click('#btnNext2'); await shot('sel3');
    await click('#btnBegin'); await p.waitForTimeout(600);
    await p.evaluate(() => { window.__wanakan.G.intro = null; }); await shot('play');
    await p.evaluate(() => { const W = window.__wanakan; W.api.beginDefense(); W.G.banner = 0; }); await shot('defense');
    await click('#btnPause'); await shot('pause');
    await click('#btnResume');
    await p.evaluate(() => { const W = window.__wanakan, G = W.G; W.api.beginDefense(); G.phase = 3; G.spawnQueue = []; G.foes.length = 0; });
    await p.waitForTimeout(4300); await shot('result');
    await p.evaluate(() => { const W = window.__wanakan; W.api.setRun('challenge', 1); W.api.startRun('lily', ['bear', 'spring', 'rock', 'fire']); const G = W.G; G.intro = null; W.api.beginDefense(); G.phase = 3; G.spawnQueue = []; G.foes.length = 0; G.soul = 120; });
    await p.waitForTimeout(4300); await shot('shop');
    await p.evaluate(() => { window.__wanakan.G.state = 'title'; window.__wanakan.api.showAch(); }); await shot('ach');
    await p.evaluate(() => document.querySelector('#btnAchBack').click()); await click('#btnEdit'); await shot('edit');
    await p.evaluate(() => document.querySelector('#editBack').click()); await click('#btnTrain'); await shot('train');
    await click('#btnTrainBack'); await click('#btnHowto'); await shot('help');
    for (let i = 1; i < 11; i++) { await click('#helpNext'); await shot('help' + (i + 1)); }
  }
  console.log(rows.join('\n'));
  console.log('pageerror:', errs.length ? errs : 'なし');
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
