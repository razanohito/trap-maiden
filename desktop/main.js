// トラップオブリリーのストア版（Windows）。ゲーム本体は game/index.html（リポジトリの v2/index.html を prepare.js が写す）。
// - セーブ: ゲームは localStorage に保存する。それを userData/save.json にも書き、起動時に戻す（Steam クラウドはこのファイルを同期する）
// - Steam: steam.json の appId が 0 より大きいときだけ使う（実績・言語・オーバーレイ・ランキング・統計）。Steam が無くてもゲームは動く
const { app, BrowserWindow, ipcMain, Menu, shell } = require('electron');
const fs = require('fs');
const path = require('path');

app.setName('Trap of Lily');
app.setPath('userData', path.join(app.getPath('appData'), 'TrapOfLily')); // %APPDATA%\TrapOfLily（Steam クラウドの場所と合わせる）
const SAVE = () => path.join(app.getPath('userData'), 'save.json');

let steamConf = { appId: 0 };
try { steamConf = JSON.parse(fs.readFileSync(path.join(__dirname, 'steam.json'), 'utf8')); } catch (e) {}
let steam = null, steamworks = null;
if (steamConf.appId > 0) {
  try {
    steamworks = require('steamworks.js');
    // Steam から起動されていなければ Steam 経由で起動し直す（製品版だけ。開発中は steam_appid.txt で動く）
    if (app.isPackaged && steamworks.restartAppIfNecessary(steamConf.appId)) { app.quit(); }
    else { steam = steamworks.init(steamConf.appId); steamworks.electronEnableSteamOverlay(); }
  } catch (e) { console.warn('Steam を使わずに起動します:', e.message); steam = null; }
}

// ランキング（無限の夜）。steamworks.js に無いので leaderboard.js が同じ steam_api64.dll を直接呼ぶ。名前は steam/leaderboard.md
const BOARD = 'ENDLESS_SCORE';
let board = null;
if (steam) {
  const dlls = [path.join(path.dirname(process.execPath), 'steam_api64.dll'), path.join(__dirname, 'node_modules', 'steamworks.js', 'dist', 'win64', 'steam_api64.dll')];
  for (const dll of dlls) { if (board || !fs.existsSync(dll)) continue; try { board = require('./leaderboard.js').open(dll); } catch (e) { console.warn('ランキングを使わずに起動します:', e.message); } }
}

function steamLang() {
  try { return steam ? steam.apps.currentGameLanguage() : ''; } catch (e) { return ''; }
}

// ゲームの実績 id → Steamworks の API 名（Steamworks の管理画面でこの名前で作る。steam/achievements.md）
const achApiName = id => 'ACH_' + String(id).toUpperCase();

ipcMain.on('host:info', e => { e.returnValue = { lang: steamLang(), steam: !!steam, board: !!board, version: app.getVersion() }; });
ipcMain.handle('board:upload', (e, score, details) => board ? board.upload(BOARD, Number(score) | 0, Array.isArray(details) ? details.map(n => Number(n) | 0) : []) : null);
ipcMain.handle('board:entries', (e, kind) => !board ? [] : kind === 'around' ? board.entries(BOARD, 'around', -4, 5) : board.entries(BOARD, kind === 'friends' ? 'friends' : 'global', 1, 50));
// 遊び方の統計を足す（Steamworks で作ってある統計だけ。無い名前は getInt が null になるので飛ばす）
ipcMain.on('stats:add', (e, add) => {
  if (!steam || !add || typeof add !== 'object') return;
  try { let n = 0; for (const [k, v] of Object.entries(add)) { if (!/^[A-Z_]{1,40}$/.test(k)) continue; const cur = steam.stats.getInt(k); if (cur == null) continue; steam.stats.setInt(k, cur + (Number(v) | 0)); n++; } if (n) steam.stats.store(); } catch (err) {}
});
ipcMain.on('save:load', e => {
  try { e.returnValue = JSON.parse(fs.readFileSync(SAVE(), 'utf8')); } catch (err) { e.returnValue = null; }
});
function writeSave(data) {
  // 書きかけで落ちても壊れないように、別名に書いてから置き換える
  const file = SAVE(), tmp = file + '.tmp';
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(tmp, JSON.stringify(data));
  fs.renameSync(tmp, file);
}
ipcMain.on('save:write', (e, data) => { try { writeSave(data); e.returnValue = true; } catch (err) { e.returnValue = false; } });
ipcMain.on('save:writeAsync', (e, data) => { try { writeSave(data); } catch (err) {} });
ipcMain.on('ach', (e, id) => { try { if (steam && !steam.achievement.isActivated(achApiName(id))) steam.achievement.activate(achApiName(id)); } catch (err) {} });
ipcMain.on('quit', () => app.quit());
ipcMain.on('fullscreen', e => { const w = BrowserWindow.fromWebContents(e.sender); if (w) w.setFullScreen(!w.isFullScreen()); });

function createWindow() {
  const win = new BrowserWindow({
    width: 1280, height: 860, minWidth: 900, minHeight: 600,
    backgroundColor: '#151017', title: 'Trap of Lily', show: false, autoHideMenuBar: true,
    icon: path.join(__dirname, 'game', 'icon.png'),
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false, sandbox: true, spellcheck: false },
  });
  win.once('ready-to-show', () => win.show());
  // F11 / Alt+Enter で全画面、Esc で全画面を抜ける
  win.webContents.on('before-input-event', (e, input) => {
    if (input.type !== 'keyDown') return;
    if (input.key === 'F11' || (input.key === 'Enter' && input.alt)) { win.setFullScreen(!win.isFullScreen()); e.preventDefault(); }
    else if (input.key === 'Escape' && win.isFullScreen()) win.setFullScreen(false);
  });
  // ゲームの外へは移動しない（リンクは既定のブラウザで開く）
  win.webContents.on('will-navigate', (e, url) => { if (!url.startsWith('file:')) { e.preventDefault(); shell.openExternal(url); } });
  win.webContents.setWindowOpenHandler(({ url }) => { if (/^https?:/.test(url)) shell.openExternal(url); return { action: 'deny' }; });
  win.loadFile(path.join(__dirname, 'game', 'index.html'));
}

Menu.setApplicationMenu(null);
app.whenReady().then(createWindow);
app.on('window-all-closed', () => app.quit());
