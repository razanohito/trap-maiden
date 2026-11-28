// 日本語以外の言語（en・zh-Hans・zh-Hant）で全部の画面を開き、訳の抜け（日本語のまま出ている文字）と、文字のはみ出しを調べる
// 使い方: python -m http.server 8766 --bind 127.0.0.1（リポジトリ直下）→ node tools/sim/test_lang.js [src|index] [en|zh-Hans|zh-Hant]
//   index はビルドした v2/index.html。中国語は漢字が日本語と重なるので、仮名が残っていないかで調べる
//   Chrome が無い環境では CHROMIUM=/path/to/chromium を付ける
// スクリーンショットは tools/sim/out/<言語>_*.png
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const path = require('path');
const page = process.argv[2] === 'index' ? 'v2/index.html' : 'src/game.html';
const LANG = process.argv[3] || 'en';
const JP = LANG === 'en' ? /[぀-ヿ㐀-鿿ｦ-ﾟ]/ : /[぀-ゟ゠-ヺヽ-ヿｦ-ﾟ]/; // 中国語は仮名だけ（・は漢字圏の区切りにも使うので除く）
(async () => {
  const b = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM, headless: true } : { channel: 'chrome', headless: true });
  const result = { 日本語のまま: {}, はみ出し: {} };
  const errs = [];
  for (const [vp, w, h, touch] of [['pc', 1100, 900, false], ['m', 390, 844, true], ['ml', 852, 393, true]]) {
    const p = await (await b.newContext({ viewport: { width: w, height: h }, hasTouch: touch, isMobile: touch })).newPage();
    p.on('pageerror', e => errs.push(vp + ': ' + e));
    await p.goto('http://127.0.0.1:8766/' + page);
    await p.evaluate(l => { localStorage.clear(); localStorage.setItem('trapoflily-lang', l); }, LANG); await p.reload();
    const jclick = async sel => { await p.evaluate(q => { const e = document.querySelector(q); if (!e) throw new Error('no ' + q); e.click(); }, sel); await p.waitForTimeout(120); };
    const shot = async name => {
      await p.waitForTimeout(250);
      await p.screenshot({ path: path.join(__dirname, 'out', `${LANG}_${vp}_${name}.png`) });
      const r = await p.evaluate(JPs => {
        const JP = new RegExp(JPs);
        const vis = el => { for (let e = el; e && e !== document.body; e = e.parentElement) { const s = getComputedStyle(e); if (e.hidden || s.display === 'none' || s.visibility === 'hidden') return false; } return true; };
        const jp = [], over = [];
        const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        for (let n; (n = tw.nextNode());) if (JP.test(n.nodeValue) && n.parentElement.id !== 'btnLang' && !n.parentElement.closest('[translate=no]') && vis(n.parentElement)) jp.push(n.nodeValue.trim().slice(0, 60));
        for (const el of document.querySelectorAll('button, .slot, .chips span, .stats span, h2, h3, .n, .t, .tag, .lv, .c, .d')) if (vis(el) && el.getBoundingClientRect().width > 0 && el.scrollWidth > el.clientWidth + 2 && getComputedStyle(el).overflowX !== 'visible') over.push((el.id || el.className) + ': ' + el.textContent.trim().slice(0, 40));
        for (const el of document.querySelectorAll('body *')) for (const ps of ['::before', '::after']) { const c = getComputedStyle(el, ps).content; if (c && JP.test(c) && vis(el)) jp.push(ps + ' ' + (el.className || el.tagName) + ' ' + c); }
        if (document.documentElement.scrollWidth > innerWidth + 1) over.push('ページの横幅 ' + document.documentElement.scrollWidth);
        return { jp, over };
      }, JP.source);
      if (r.jp.length) result.日本語のまま[`${vp}/${name}`] = r.jp;
      if (r.over.length) result.はみ出し[`${vp}/${name}`] = r.over;
    };
    await shot('title');
    await jclick('#btnLang'); await shot('langmenu'); await jclick('#btnLang');
    // 遊び方の全ページ
    await jclick('#btnHowto');
    for (let i = 0; i < 11; i++) { await shot('help' + (i + 1)); await jclick('#helpNext'); }
    await jclick('#helpClose');
    // ステージ選択・実績
    await jclick('#btnStage'); await shot('stages'); await jclick('#btnStagesBack');
    await jclick('#btnAch'); await shot('ach'); await jclick('#btnAchBack');
    // 設定・クレジット（音量を変えると保存される）
    await jclick('#btnSettings'); await p.fill('#volBgm', '4'); await p.dispatchEvent('#volBgm', 'input'); await shot('settings');
    result.音量の保存 = await p.evaluate(() => localStorage.getItem('trapoflily-vol'));
    await jclick('#btnCredits'); await shot('credits'); await jclick('#btnCreditsBack'); await jclick('#btnSetBack');
    // トレーニング・おはなしの一覧
    await jclick('#btnTrain'); await shot('train'); await jclick('#btnTrainBack');
    await jclick('#btnStory'); await shot('storylist'); await jclick('#btnStoryListBack');
    // おはなし（全部の場面を最後まで送る。文字は一度に出す）
    await p.evaluate(() => localStorage.setItem('trapoflily-textspeed', '3'));
    for (const id of ['intro1', 'intro2', 'dawn1', 'ch1e', 'ch3s', 'ch8e', 'ending', 'truth', 'endA', 'endB']) {
      await p.evaluate(i => window.__wanakan.api.playStory(i, null, { replay: true }), id);
      for (let i = 0; i < 80; i++) {
        const st = await p.evaluate(() => window.__wanakan.api.storyState());
        if (!st) break;
        if (st.wait && await p.$('#storyChoice:not([hidden]) button')) { await shot('story_' + id + '_choice'); await p.evaluate(() => document.querySelector('#storyChoice button').click()); continue; }
        if (i === 3 || i === 12) await shot(`story_${id}_${i}`);
        await p.evaluate(() => document.querySelector('#storyBox').click());
      }
    }
    // 導入マンガ（英語は横書き）
    await p.evaluate(() => document.querySelector('#btnStart').click()); await jclick('#btnComic'); await shot('comic'); await jclick('#comicSkip');
    // 支度（チャレンジ）
    await shot('select1');
    await jclick('#pick-lily'); await shot('select1dlg');
    await jclick('#btnNext1'); await shot('select2');
    await jclick('#btnNext2'); await shot('select3');
    await jclick('#btnBegin'); await p.waitForTimeout(600); await shot('intro');
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
    await p.goto('http://127.0.0.1:8766/' + page); await jclick('#btnEdit'); await shot('edit');
    // 一時停止
    await p.goto('http://127.0.0.1:8766/' + page);
    await p.evaluate(() => { const A = window.__wanakan.api; A.setRun('challenge', 1); A.startRun('noel', ['ice', 'spring', 'blade', 'bell']); window.__wanakan.G.intro = null; });
    await p.keyboard.press('p'); await shot('pause');
    await jclick('#btnPauseSet'); await shot('pausesettings'); await jclick('#btnSetBack'); result.一時停止へ戻る = await p.evaluate(() => !document.getElementById('ovPause').hidden);
    result.訳のない文言 = [...new Set([...(result.訳のない文言 || []), ...await p.evaluate(() => window.__wanakan.missing())])];
    result.言語 = await p.evaluate(() => window.__wanakan.lang + ' / html lang=' + document.documentElement.lang + ' / title=' + document.title);
    await p.context().close();
  }
  console.log(JSON.stringify(result, null, 1));
  console.log('pageerror:', errs.length ? errs : 'なし');
  await b.close();
  process.exit(Object.keys(result.日本語のまま).length || result.訳のない文言.length || errs.length ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
