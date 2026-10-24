// リポジトリの v2/index.html（新しい絵柄の版。python tools/build.py で作る）とライセンス文を、アプリに入れる場所へ写す
const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..');
const game = path.join(__dirname, 'game'), lic = path.join(__dirname, 'licenses');
fs.mkdirSync(game, { recursive: true }); fs.mkdirSync(lic, { recursive: true });
const src = path.join(root, 'v2', 'index.html');
if (!fs.existsSync(src)) throw new Error('v2/index.html がありません。先に python tools/build.py を実行してください');
fs.copyFileSync(src, path.join(game, 'index.html'));
fs.copyFileSync(path.join(__dirname, 'build', 'icon.png'), path.join(game, 'icon.png'));
for (const f of fs.readdirSync(path.join(root, 'art', 'fonts'))) if (f.endsWith('.txt')) fs.copyFileSync(path.join(root, 'art', 'fonts', f), path.join(lic, f));
fs.copyFileSync(path.join(__dirname, 'node_modules', 'steamworks.js', 'LICENSE'), path.join(lic, 'steamworks.js-LICENSE.txt'));
fs.writeFileSync(path.join(lic, 'README.txt'), [
  'Trap of Lily - third-party notices',
  '',
  'Font: Zen Maru Gothic, SIL Open Font License 1.1 (OFL-ZenMaruGothic.txt).',
  'Electron / Chromium: see LICENSE.electron.txt and LICENSES.chromium.html in the game folder.',
  'steamworks.js: MIT License (steamworks.js-LICENSE.txt). Steamworks SDK (steam_api64.dll) (c) Valve Corporation.',
  '',
].join('\r\n'));
console.log('game/index.html と licenses/ を用意しました');
