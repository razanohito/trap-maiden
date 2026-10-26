// Steam のランキング（リーダーボード）。steamworks.js にランキングが無いので、同じ steam_api64.dll の flat API を koffi で呼ぶ
// - 先に steamworks.js が SteamAPI を初期化しておくこと（このファイルは初期化しない）
// - 結果は IsAPICallCompleted / GetAPICallResult を 100ms ごとに見て受け取る（コールバックの登録はいらない）
const koffi = require('koffi');

const CB_FIND = 1104, CB_DOWNLOADED = 1105, CB_UPLOADED = 1106; // k_iSteamUserStatsCallbacks + 4/5/6
const SORT_DESC = 2, DISPLAY_NUMERIC = 1, UPLOAD_KEEP_BEST = 1;
const REQUEST = { global: 0, around: 1, friends: 2 };
const MAX_DETAILS = 64;

function open(dllPath) {
  const lib = koffi.load(dllPath);
  // 構造体は Steam の Windows 版と同じ並び（8 バイト境界 = 64bit の自然な並び）
  const FindResult = koffi.struct('LeaderboardFindResult_t', { hLeaderboard: 'uint64_t', found: 'uint8_t' });
  const Downloaded = koffi.struct('LeaderboardScoresDownloaded_t', { hLeaderboard: 'uint64_t', hEntries: 'uint64_t', count: 'int32_t' });
  const Uploaded = koffi.struct('LeaderboardScoreUploaded_t', { success: 'uint8_t', hLeaderboard: 'uint64_t', score: 'int32_t', changed: 'uint8_t', rankNew: 'int32_t', rankPrev: 'int32_t' });
  const Entry = koffi.struct('LeaderboardEntry_t', { steamId: 'uint64_t', rank: 'int32_t', score: 'int32_t', details: 'int32_t', ugc: 'uint64_t' });
  const f = {
    userStats: lib.func('void *SteamAPI_SteamUserStats_v012()'),
    utils: lib.func('void *SteamAPI_SteamUtils_v010()'),
    friends: lib.func('void *SteamAPI_SteamFriends_v017()'),
    user: lib.func('void *SteamAPI_SteamUser_v023()'),
    findOrCreate: lib.func('uint64_t SteamAPI_ISteamUserStats_FindOrCreateLeaderboard(void *self, const char *name, int sort, int display)'),
    upload: lib.func('uint64_t SteamAPI_ISteamUserStats_UploadLeaderboardScore(void *self, uint64_t board, int method, int32_t score, const int32_t *details, int count)'),
    download: lib.func('uint64_t SteamAPI_ISteamUserStats_DownloadLeaderboardEntries(void *self, uint64_t board, int request, int start, int end)'),
    entry: lib.func('bool SteamAPI_ISteamUserStats_GetDownloadedLeaderboardEntry(void *self, uint64_t entries, int index, _Out_ LeaderboardEntry_t *entry, int32_t *details, int max)'),
    done: lib.func('bool SteamAPI_ISteamUtils_IsAPICallCompleted(void *self, uint64_t call, _Out_ bool *failed)'),
    result: lib.func('bool SteamAPI_ISteamUtils_GetAPICallResult(void *self, uint64_t call, void *out, int size, int expected, _Out_ bool *failed)'),
    persona: lib.func('const char *SteamAPI_ISteamFriends_GetFriendPersonaName(void *self, uint64_t id)'),
    myId: lib.func('uint64_t SteamAPI_ISteamUser_GetSteamID(void *self)'),
  };
  const iface = { stats: f.userStats(), utils: f.utils(), friends: f.friends(), user: f.user() };
  if (!iface.stats || !iface.utils) throw new Error('Steam のインターフェースが取れない（SteamAPI が初期化されていない）');

  // 呼び出しの結果を待つ。8 秒で諦める
  const wait = (call, type, cb) => new Promise((resolve, reject) => {
    if (!call || call === 0n) { reject(new Error('Steam の呼び出しに失敗')); return; }
    const t0 = Date.now();
    const tick = () => {
      const failed = [false];
      if (f.done(iface.utils, call, failed)) {
        const buf = Buffer.alloc(koffi.sizeof(type)), bad = [false];
        if (failed[0] || !f.result(iface.utils, call, buf, buf.length, cb, bad) || bad[0]) { reject(new Error('Steam の呼び出しに失敗')); return; }
        resolve(koffi.decode(buf, type)); return;
      }
      if (Date.now() - t0 > 8000) { reject(new Error('Steam の応答がない')); return; }
      setTimeout(tick, 100);
    };
    tick();
  });

  const boards = {};
  async function board(name) { // 無ければ作る（大きい順・数字で表示）
    if (boards[name]) return boards[name];
    const r = await wait(f.findOrCreate(iface.stats, name, SORT_DESC, DISPLAY_NUMERIC), FindResult, CB_FIND);
    if (!r.found || !r.hLeaderboard) throw new Error('ランキングが見つからない');
    return (boards[name] = r.hLeaderboard);
  }
  async function upload(name, score, details = []) {
    const h = await board(name), d = Int32Array.from(details.slice(0, MAX_DETAILS));
    const r = await wait(f.upload(iface.stats, h, UPLOAD_KEEP_BEST, score | 0, d, d.length), Uploaded, CB_UPLOADED);
    return { ok: !!r.success, changed: !!r.changed, rank: r.rankNew, prevRank: r.rankPrev };
  }
  async function entries(name, kind = 'global', start = 1, end = 50) {
    const h = await board(name), req = REQUEST[kind] ?? 0;
    const r = await wait(f.download(iface.stats, h, req, start, end), Downloaded, CB_DOWNLOADED);
    const me = iface.user ? f.myId(iface.user) : 0n, out = [];
    for (let i = 0; i < r.count; i++) {
      const e = {}, det = new Int32Array(MAX_DETAILS);
      if (!f.entry(iface.stats, r.hEntries, i, e, det, MAX_DETAILS)) continue;
      out.push({ rank: e.rank, score: e.score, name: (iface.friends && f.persona(iface.friends, e.steamId)) || '', me: e.steamId === me, details: Array.from(det.subarray(0, Math.min(e.details, MAX_DETAILS))) });
    }
    return out;
  }
  return { upload, entries };
}

module.exports = { open };
