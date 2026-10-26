// ストア版（Electron）の動作確認: 窓口 trapHost・セーブの書き出しと復元・言語の切り替え・終了
// 使い方（Linux / Windows どちらでも）: npm install → node prepare.js → node test/test_desktop.js
// 画面の無い Linux では Xvfb を立ててから（DISPLAY=:99）
const { _electron: electron } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const fs = require('fs'), os = require('os'), path = require('path');
const home = fs.mkdtempSync(path.join(os.tmpdir(), 'tol-'));
const env = { ...process.env, HOME: home, APPDATA: path.join(home, 'AppData'), XDG_CONFIG_HOME: path.join(home, '.config') };
const saveFile = () => {
  const dirs = [path.join(home, '.config', 'TrapOfLily'), path.join(home, 'AppData', 'TrapOfLily'), path.join(home, 'Library', 'Application Support', 'TrapOfLily')];
  return dirs.map(d => path.join(d, 'save.json')).find(f => fs.existsSync(f));
};
const launch = () => electron.launch({ args: [path.join(__dirname, '..'), '--no-sandbox', '--lang=ja'], env, executablePath: require('electron') });
(async () => {
  const r = {};
  let app = await launch(); let w = await app.firstWindow(); await w.waitForLoadState('load');
  r.窓口 = await w.evaluate(() => ({ host: !!window.trapHost, keys: Object.keys(window.trapHost || {}) }));
  r.タイトル = await w.title();
  // 設定で音量を変える → 数秒で save.json に出る
  await w.click('#btnSettings');
  r.終了ボタンが見える = await w.evaluate(() => !document.getElementById('setExitRow').hidden);
  await w.fill('#volSfx', '3'); await w.dispatchEvent('#volSfx', 'input');
  await w.waitForTimeout(3600);
  const f = saveFile(); r.セーブの場所 = f && f.replace(home, '~');
  r.セーブに音量 = f && JSON.parse(fs.readFileSync(f, 'utf8')).data['trapoflily-vol'];
  // 言語を切り替える（読み込み直す直前に必ず書く）
  await w.click('#btnSetBack'); await Promise.all([w.waitForEvent('load'), w.click('#btnLang')]);
  r.切り替え後の言語 = await w.evaluate(() => document.documentElement.lang);
  r.セーブに言語 = JSON.parse(fs.readFileSync(saveFile(), 'utf8')).data['trapoflily-lang'];
  await app.close();
  // 別の PC から来たセーブ（Steam クラウド）を想定: save.json だけ書き換え、ブラウザ側の保存は消す
  const s = JSON.parse(fs.readFileSync(saveFile(), 'utf8'));
  s.data['trapoflily-lang'] = 'ja'; s.data['trapoflily-ach'] = JSON.stringify({ night1: '2026-10-20' });
  fs.writeFileSync(saveFile(), JSON.stringify(s));
  for (const d of ['Local Storage', 'Session Storage']) fs.rmSync(path.join(path.dirname(saveFile()), d), { recursive: true, force: true });
  app = await launch(); w = await app.firstWindow(); await w.waitForLoadState('load');
  r.復元した言語 = await w.evaluate(() => document.documentElement.lang);
  r.復元した実績 = await w.evaluate(() => localStorage.getItem('trapoflily-ach'));
  r.復元した音量 = await w.evaluate(() => localStorage.getItem('trapoflily-vol'));
  // 終了ボタン
  await w.click('#btnSettings');
  const closed = new Promise(res => app.process().on('exit', () => res(true)));
  await w.click('#btnExit');
  r.終了した = await Promise.race([closed, new Promise(res => setTimeout(() => res(false), 5000))]);
  console.log(JSON.stringify(r, null, 1));
  fs.rmSync(home, { recursive: true, force: true });
  const ok = r.窓口.host && r.セーブに音量 && r.切り替え後の言語 === 'en' && r.セーブに言語 === 'en' && r.復元した言語 === 'ja' && /night1/.test(r.復元した実績 || '') && r.終了した;
  console.log(ok ? 'OK' : 'NG'); process.exit(ok ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
