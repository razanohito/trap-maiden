// 英語版で全部の画面を開き、訳の抜け（日本語のまま出ている文字）と、文字のはみ出しを調べる
// 使い方: python -m http.server 8766 --bind 127.0.0.1（リポジトリ直下）→ node tools/sim/test_english.js [src|index]
// スクリーンショットは tools/sim/out/en_*.png
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const path = require('path');
const page = process.argv[2] === 'index' ? 'index.html' : 'src/game.html';
const JP = /[぀-ヿ㐀-鿿ｦ-ﾟ]/;
(async () => {
  const b = await chromium.launch({ channel: 'chrome', headless: true });
  const result = { 日本語のまま: {}, はみ出し: {} };
  const errs = [];
  for (const [vp, w, h, touch] of [['pc', 1100, 900, false], ['m', 390, 844, true], ['ml', 852, 393, true]]) {
    const p = await (await b.newContext({ viewport: { width: w, height: h }, hasTouch: touch, isMobile: touch })).newPage();
    p.on('pageerror', e => errs.push(vp + ': ' + e));
    await p.goto('http://127.0.0.1:8766/' + page);
    await p.evaluate(() => { localStorage.clear(); localStorage.setItem('trapoflily-lang', 'en'); }); await p.reload();
    const shot = async name => {
      await p.waitForTimeout(250);
      await p.screenshot({ path: path.join(__dirname, 'out', `en_${vp}_${name}.png`) });
      const r = await p.evaluate(JPs => {
        const JP = new RegExp(JPs);
        const vis = el => { for (let e = el; e && e !== document.body; e = e.parentElement) { const s = getComputedStyle(e); if (e.hidden || s.display === 'none' || s.visibility === 'hidden') return false; } return true; };
        const jp = [], over = [];
        const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        for (let n; (n = tw.nextNode());) if (JP.test(n.nodeValue) && n.parentElement.id !== 'btnLang' && vis(n.parentElement)) jp.push(n.nodeValue.trim().slice(0, 60));
        for (const el of document.querySelectorAll('button, .slot, .chips span, .stats span, h2, h3, .n, .t, .tag, .lv, .c, .d')) if (vis(el) && el.getBoundingClientRect().width > 0 && el.scrollWidth > el.clientWidth + 2 && getComputedStyle(el).overflowX !== 'visible') over.push((el.id || el.className) + ': ' + el.textContent.trim().slice(0, 40));
        for (const el of document.querySelectorAll('body *')) for (const ps of ['::before', '::after']) { const c = getComputedStyle(el, ps).content; if (c && JP.test(c) && vis(el)) jp.push(ps + ' ' + (el.className || el.tagName) + ' ' + c); }
        if (document.documentElement.scrollWidth > innerWidth + 1) over.push('ページの横幅 ' + document.documentElement.scrollWidth);
        return { jp, over };
      }, JP.source);
      if (r.jp.length) result.日本語のまま[`${vp}/${name}`] = r.jp;
      if (r.over.length) result.はみ出し[`${vp}/${name}`] = r.over;
    };
    await shot('title');
    // 遊び方の全ページ
    await p.click('#btnHowto');
    for (let i = 0; i < 11; i++) { await shot('help' + (i + 1)); await p.click('#helpNext'); }
    await p.click('#helpClose');
    // ステージ選択・実績
    await p.click('#btnStage'); await shot('stages'); await p.click('#btnStagesBack');
    await p.click('#btnAch'); await shot('ach'); await p.click('#btnAchBack');
    // 支度（チャレンジ）
    await p.click('#btnStart'); await shot('select1');
    await p.click('#btnNext1'); await shot('select2');
    await p.click('#btnNext2'); await shot('select3');
    await p.click('#btnBegin'); await p.waitForTimeout(600); await shot('intro');
    await p.evaluate(() => { const W = window.__wanakan; W.G.intro = null; }); await p.waitForTimeout(300); await shot('prep');
    // 罠を置いて、文言を出す
    await p.evaluate(() => { const W = window.__wanakan, A = W.api, G = W.G; G.mana = 999; for (let y = 2; y < 8; y++) for (let x = 3; x < 12; x++) if (A.canPlace(x, y) && !G.traps.size) A.placeTrap(x, y, G.loadout[0]); });
    await p.evaluate(() => { const W = window.__wanakan; W.api.beginDefense(); }); await p.waitForTimeout(1500); await shot('phase1');
    // 夜明け → ショップ
    await p.evaluate(() => { const W = window.__wanakan, G = W.G; G.phase = 3; G.spawnQueue = []; G.foes.length = 0; });
    await p.waitForTimeout(4500); await shot('shop');
    // 捕まった結果
    await p.evaluate(() => window.__wanakan.api.gameOver(false)); await p.waitForTimeout(500); await shot('over');
    await p.evaluate(() => window.__wanakan.api.gameOver(true)); await p.waitForTimeout(500); await shot('won');
    // ステージ 1 をクリア
    await p.evaluate(() => { const W = window.__wanakan, A = W.api; A.setRun('stage', 1); A.startRun('mina', ['bear', 'rock', 'fire', 'keg']); W.G.intro = null; A.beginDefense(); W.G.phase = 3; W.G.spawnQueue = []; W.G.foes.length = 0; });
    await p.waitForTimeout(4500); await shot('stageclear');
    // エディット
    await p.goto('http://127.0.0.1:8766/' + page); await p.click('#btnEdit'); await shot('edit');
    // 一時停止
    await p.goto('http://127.0.0.1:8766/' + page);
    await p.evaluate(() => { const A = window.__wanakan.api; A.setRun('challenge', 1); A.startRun('noel', ['ice', 'spring', 'blade', 'bell']); window.__wanakan.G.intro = null; });
    await p.keyboard.press('p'); await shot('pause');
    result.訳のない文言 = [...new Set([...(result.訳のない文言 || []), ...await p.evaluate(() => window.__wanakan.missing())])];
    result.言語 = await p.evaluate(() => window.__wanakan.lang + ' / html lang=' + document.documentElement.lang + ' / title=' + document.title);
    await p.context().close();
  }
  console.log(JSON.stringify(result, null, 1));
  console.log('pageerror:', errs.length ? errs : 'なし');
  await b.close();
  process.exit(Object.keys(result.日本語のまま).length || result.訳のない文言.length || errs.length ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
