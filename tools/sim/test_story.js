// おはなしの流れを通しで確かめる（初回: マンガ→導入→操作の練習→続き→ステージ1、クリア後の夜明け、章の終わり、結び→さかさまの夜）
// 使い方: python -m http.server 8766 --bind 127.0.0.1（リポジトリ直下）→ node tools/sim/test_story.js [src|index]
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const page = process.argv[2] === 'index' ? 'v2/index.html' : 'src/game.html';
(async () => {
  const b = await chromium.launch({ channel: 'chrome', headless: true });
  const p = await (await b.newContext({ locale: 'ja-JP', viewport: { width: 1100, height: 800 } })).newPage();
  const errs = [], log = [];
  p.on('pageerror', e => errs.push(String(e)));
  await p.goto(`http://127.0.0.1:8766/${page}?story`);
  await p.evaluate(() => { localStorage.clear(); localStorage.setItem('trapoflily-textspeed', '3'); }); await p.reload();
  const st = () => p.evaluate(() => window.__wanakan.api.storyState());
  const waitStory = async () => { for (let i = 0; i < 100 && !(await st()); i++) await p.waitForTimeout(100); };
  const visible = sel => p.evaluate(s => { const e = document.querySelector(s); return !!e && !e.hidden; }, sel);
  // おはなしを最後まで送る（選択肢は n 番目）
  const readAll = async (pick = 0) => { let n = 0; for (let i = 0; i < 300; i++) { const s = await st(); if (!s) return n; if (s.wait) await p.evaluate(k => document.querySelectorAll('#storyChoice button')[k].click(), pick); else await p.evaluate(() => document.querySelector('#storyBox').click()); n++; await p.waitForTimeout(20); } return -1; };
  // 1. 初回はステージを押すとマンガから
  await p.click('#btnStage'); await p.waitForTimeout(300);
  log.push('マンガ=' + await visible('#ovComic'));
  await p.click('#comicSkip'); await p.waitForTimeout(200);
  log.push('導入1=' + JSON.stringify(await st()));
  log.push('導入1の行数=' + await readAll());
  await p.waitForTimeout(500);
  log.push('練習中=' + await p.evaluate(() => window.__wanakan.G.state + ' storyTut=' + !document.getElementById('btnSkipTut').hidden));
  // 2. 一時停止から練習を飛ばす → 導入2 → ステージ1の支度
  await p.keyboard.press('p'); await p.waitForTimeout(200);
  log.push('飛ばすボタン=' + await visible('#btnSkipTut'));
  await p.click('#btnSkipTut'); await p.waitForTimeout(200);
  log.push('導入2=' + JSON.stringify(await st()));
  log.push('導入2の行数=' + await readAll());
  await p.waitForTimeout(300);
  log.push('支度=' + await visible('#ovSelect'));
  // 3. ステージ1をクリア → 夜明けの場面 → 結果
  await p.evaluate(() => { const W = window.__wanakan, A = W.api; A.setRun('stage', 1); A.startRun('lily', ['bear', 'rock', 'fire', 'keg']); W.G.intro = null; A.beginDefense(); W.G.phase = 3; W.G.spawnQueue = []; W.G.foes.length = 0; });
  await waitStory(); // 夜明けの場面が始まるまで待つ
  log.push('クリア後=' + JSON.stringify(await st()));
  log.push('夜明けの行数=' + await readAll());
  await p.waitForTimeout(300);
  log.push('結果=' + await visible('#ovOver'));
  // 4. 結び → さかさまの夜（両方の結末）→ 実績
  await p.evaluate(() => window.__wanakan.api.playStory('ending'));
  log.push('結びの行数=' + await readAll());
  for (const k of [0, 1]) { await p.evaluate(() => window.__wanakan.api.playStory('truth', null, { replay: true })); log.push(`さかさま(選択${k})の行数=` + await readAll(k)); }
  log.push('見た場面=' + Object.keys(await p.evaluate(() => window.__wanakan.api.storySeen())).join(','));
  log.push('実績=' + await p.evaluate(() => Object.keys(JSON.parse(localStorage.getItem('trapoflily-ach') || '{}')).join(',')));
  // 5. 一覧
  await p.evaluate(() => window.__wanakan.api.openStoryList()); await p.waitForTimeout(200);
  log.push('一覧で開いている数=' + await p.evaluate(() => document.querySelectorAll('#storyList button:not([disabled])').length + '/' + document.querySelectorAll('#storyList button').length));
  // 6. スキップは選択肢の手前で止まる
  await p.evaluate(() => { window.__wanakan.api.playStory('truth', null, { replay: true }); window.__wanakan.api.storySkip(); });
  log.push('スキップ後=' + JSON.stringify(await st()));
  console.log(log.join('\n'));
  console.log('pageerror:', errs.length ? errs : 'なし');
  await b.close();
  process.exit(errs.length ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
