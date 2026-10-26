// leaderboard.js の確かめ: Steam のランキング関数と同じ形の偽物（test/leaderboard_mock.c）を作って呼ぶ
// 使い方（Linux / macOS、gcc が要る）: node test/test_leaderboard.js
// 構造体の大きさが Steam と違うと偽物が結果を返さないので、並びの間違いもここで分かる
const { execFileSync } = require('child_process');
const fs = require('fs'), os = require('os'), path = require('path');
const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'tol-lb-')), so = path.join(dir, 'libmock.so');
execFileSync('gcc', ['-shared', '-fPIC', '-o', so, path.join(__dirname, 'leaderboard_mock.c')]);
const lb = require('../leaderboard.js').open(so);
(async () => {
  const up = await lb.upload('ENDLESS_SCORE', 12345, [1, 22, 2, 5]);
  const list = await lb.entries('ENDLESS_SCORE', 'global', 1, 50);
  const ok = up.ok && up.changed && up.rank === 1 && list.length === 2 && list[1].me && list[1].score === 12345 && list[1].details.join() === '1,22,2,5' && list[0].name === 'Rival' && !list[0].me;
  console.log(JSON.stringify({ up, list }, null, 1));
  console.log(ok ? 'OK' : 'NG'); process.exit(ok ? 0 : 1);
})().catch(e => { console.error('NG', e); process.exit(1); });
