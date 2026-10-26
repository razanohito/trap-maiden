# Steam ランキングと遊び方の集計

## ランキング（無限の夜）— Steamworks での作業はいらない

- ゲームが初めて送るときに、リーダーボード `ENDLESS_SCORE` を自動で作ります（大きい順・数字表示・自己ベストを残す）。
- 自分で作っておく場合は、Steamworks の「Stats & Achievements」→「Leaderboards」で、同じ名前・`Descending`・`Numeric` にします。
- 「Trusted」にはしないでください（ゲームから書き込めなくなります）。
- 不正なスコアは、同じ画面の「Show entries」から消せます。

### 一緒に送る詳細（details、int32 の並び）

| 位置 | 中身 |
| --- | --- |
| 0 | 並びの版（今は 1） |
| 1 | 最大連続 |
| 2 | 逃げる子（0 リリィ / 1 ミーナ / 2 ノエル / 3 セシル） |
| 3〜7 | 撃退・奈落・玉突き・連鎖・ダブルヒットの回数 |
| 8 | 遊んだ秒数 |
| 9 | 持っていった罠（ビット。下の罠の順で 1, 2, 4, …） |
| 10〜21 | 罠ごとの作動回数: bear, spring, rock, fire, ice, warp, blade, bell, caltrop, vortex, keg, cage |

## 遊び方の集計（Steam の統計）— 使うなら作る

夜が終わるたびに（ステージ・チャレンジ・無限の夜。トレーニングは除く）、次の統計に足します。作っていない名前は無視されるので、作らなくてもゲームは動きます。

- 「Stats & Achievements」→「Stats」→「New Stat」で、Type `INT`、Set By `Client`、**Aggregated にチェック**、Default 0 で作ります。
- `RUNS_LILY` `RUNS_MINA` `RUNS_NOEL` `RUNS_CECIL`（その子で遊んだ回数）
- `PICKED_<罠>`（その罠を持っていった回数）と `FIRED_<罠>`（その罠が作動した回数）。`<罠>` は BEAR SPRING ROCK FIRE ICE WARP BLADE BELL CALTROP VORTEX KEG CAGE
- 作ったら「Publish」タブで公開します。
- 全員の合計は、ブラウザで次を開くと見られます（`<APPID>` を置き換え）：
  `https://api.steampowered.com/ISteamUserStats/GetGlobalStatsForGame/v1/?appid=<APPID>&count=2&name[0]=FIRED_FIRE&name[1]=PICKED_FIRE`

## 仕組み

- `desktop/leaderboard.js` が、steamworks.js と同じ `steam_api64.dll` のランキング関数を koffi で呼びます（steamworks.js 0.4.0 にランキングが無いため）。
- 偽の Steam（同じ関数を持つ共有ライブラリ）で、構造体の並びと呼び出しを確かめてあります。本物の Steam ではまだ試していません。
