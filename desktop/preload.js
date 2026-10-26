// ゲームに渡す窓口 window.trapHost と、セーブの読み書き。ゲームのスクリプトより先に動く
const { contextBridge, ipcRenderer } = require('electron');

const info = ipcRenderer.sendSync('host:info') || {};
// ゲームが localStorage に書くキー（src/game.html の trapoflily-* と wanakan-*）
const ours = k => /^(trapoflily|wanakan)-/.test(k);
const snapshot = () => { const o = {}; for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i); if (ours(k)) o[k] = localStorage.getItem(k); } return o; };

// 起動時: save.json があれば、それをゲームの保存に戻す（Steam クラウドで別の PC から来たセーブも）
try {
  const saved = ipcRenderer.sendSync('save:load');
  if (saved && saved.data && typeof saved.data === 'object') {
    for (const k of Object.keys(snapshot())) if (!(k in saved.data)) localStorage.removeItem(k);
    for (const [k, v] of Object.entries(saved.data)) if (ours(k) && typeof v === 'string') localStorage.setItem(k, v);
  }
} catch (e) {}

// 遊んでいるあいだ: 変わったら書く。閉じる・読み込み直す直前は必ず書く（言語の切り替えで読み込み直すため）
let last = JSON.stringify(snapshot());
const flush = sync => {
  const now = JSON.stringify(snapshot());
  if (now === last) return;
  last = now;
  const payload = { version: 1, savedAt: new Date().toISOString(), data: JSON.parse(now) };
  if (sync) ipcRenderer.sendSync('save:write', payload); else ipcRenderer.send('save:writeAsync', payload);
};
setInterval(() => flush(false), 3000);
addEventListener('beforeunload', () => flush(true));
addEventListener('pagehide', () => flush(true));

contextBridge.exposeInMainWorld('trapHost', {
  lang: info.lang || '',
  steam: !!info.steam,
  achieve: id => { ipcRenderer.send('ach', String(id)); flush(false); },
  board: info.board ? { upload: (score, details) => ipcRenderer.invoke('board:upload', score, details), entries: kind => ipcRenderer.invoke('board:entries', kind) } : null,
  addStats: add => ipcRenderer.send('stats:add', add),
  quit: () => { flush(true); ipcRenderer.send('quit'); },
  toggleFullscreen: () => ipcRenderer.send('fullscreen'),
});
