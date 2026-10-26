# Steam で出すまでの手順

ここにあるもの:

| パス | 中身 |
|---|---|
| `store_text.md` | ストアページの文章（日本語・英語）、AI 生成コンテンツの開示文、タグ、システム要件 |
| `achievements.md` | 実績 23 個の API 名・名前・説明（日本語・英語） |
| `leaderboard.md` | 無限の夜のランキング（自動で作られる）と、任意の遊び方の統計 |
| `achievements/` | 実績アイコン（256×256、取った絵と灰色の絵）。`python tools/make_ach_icons.py` で作り直せる |
| `capsules/` | ストアとライブラリの画像（下の表）。`python tools/make_capsules.py` で作り直せる |
| `screenshots/` | スクリーンショット 1920×1080（`en_*` 英語・`ja_*` 日本語、9 枚ずつ。9 枚目はおはなし）。`python tools/build.py` のあと `node tools/sim/shot_store.js` で撮り直せる（ビルドした v2/index.html を撮る） |
| `steampipe/` | ビルドを Steam に上げるスクリプト（`app_build.vdf`・`upload.bat`） |

ゲーム本体の Windows 版は `desktop/`（Electron）。

## 1. Steamworks に登録する（峻さんの作業）

1. [partner.steamgames.com](https://partner.steamgames.com/) で Steamworks に参加する。Steam アカウントでログインし、名前・住所、銀行口座（本人名義、SWIFT コード）、税の情報（日本に住む個人は W-8BEN。マイナンバーを入れると米国の源泉徴収が 0% になる）、本人確認（パスポートか運転免許証）を入れる
2. アプリ登録料（Steam Direct、1 作品 US$100）を払う。**払ってから 30 日たたないと発売できない**
3. App ID が発行される。ストア用の App ID と、ゲームの中身を入れる「デポ」の ID（ふつうは App ID + 1）をメモする

## 2. App ID をゲームに入れる（Claude にも頼める）

1. `desktop/steam.json` を `{ "appId": 1234560 }` のように書き換える（0 のままだと Steam なしで動く）
2. 開発中に Steam を使って試すときは、`desktop/steam_appid.txt` に App ID だけを書いたファイルを置く（Git には入れない）
3. `steampipe/app_build.vdf` の `"AppID"` と `Depots` の番号を書き換える

## 3. Steamworks の設定

- **実績**: 「アプリ管理 → 統計と実績」で `achievements.md` の 23 個を作る。API 名は表のとおり（`ACH_NIGHT1` など）。アイコンは `achievements/`
- **ランキング**: 作業はいらない（ゲームが `ENDLESS_SCORE` を自動で作る）。罠の使われ方を集計したいときだけ、`leaderboard.md` の統計を作る
- **Steam クラウド**: 「アプリ管理 → Steam クラウド」で、1 ユーザーあたり 1 MB・ファイル数 10 にして、Auto-Cloud に次の 1 行を足す
  - ルート: `WinAppDataRoaming`、サブディレクトリ: `TrapOfLily`、パターン: `save.json`、OS: Windows
  - （ゲームは `%APPDATA%\TrapOfLily\save.json` にセーブを書く。`desktop/main.js`）
- **起動オプション**: 実行ファイル `TrapOfLily.exe`、OS は Windows
- **言語**: 日本語と英語の「インターフェース」「字幕」にチェック（音声はなし）。ゲームは Steam の言語設定で始まり、タイトルや設定画面で切り替えられる
- **ストアページ**: 文章は `store_text.md`、画像は下の表、スクリーンショットは `screenshots/`（5 枚以上）
- **AI 生成コンテンツの開示**: 「コンテンツ調査」で「事前生成された AI コンテンツがある」を選び、`store_text.md` の開示文を貼る
- **年齢区分**: 暴力表現は「ファンタジーの軽い暴力（罠で侵入者を倒す、血の表現なし）」

### 画像（`capsules/`）

| Steamworks の欄 | ファイル | 大きさ |
|---|---|---|
| ヘッダーカプセル | `header_capsule_920x430.jpg` | 920×430 |
| 小カプセル | `small_capsule_462x174.jpg` | 462×174 |
| メインカプセル | `main_capsule_1232x706.jpg` | 1232×706 |
| 縦長カプセル | `vertical_capsule_748x896.jpg` | 748×896 |
| ライブラリカプセル | `library_capsule_600x900.jpg` | 600×900 |
| ライブラリヒーロー | `library_hero_3840x1240.jpg` | 3840×1240（文字なし） |
| ライブラリロゴ | `library_logo_1280x720.png` | 1280×720（背景は透明） |

## 4. Windows 版を作って上げる

Windows の PC で（Node.js 22 以上と Python 3 が必要）:

```bat
cd trap-maiden
python tools\build.py
cd desktop
npm install
npm run dist
```

`desktop\dist\win-unpacked\` が Steam に上げる中身（`TrapOfLily.exe` ほか）、`desktop\dist\Trap of Lily-1.0.0-win.zip` は同じものの zip（itch.io などに使える）。

上げる: Steamworks SDK を落として展開し、`steampipe\upload.bat` の `STEAMCMD` を SDK の `steamcmd.exe` に合わせて実行する。上がったビルドは Steamworks の「SteamPipe → ビルド」で `default` ブランチに設定する。

## 5. 発売までの決まり

- 「近日登場」のストアページを、発売の 2 週間以上前に公開する
- ストアページとビルドを Valve の審査に出す（数日かかる）
- 登録料を払ってから 30 日たっていること

## 確かめたこと・まだのこと

- Linux の上で Electron 版を動かし、窓口（trapHost）・セーブの書き出しと復元・言語の切り替え・終了を確かめた（`desktop/test/test_desktop.js`）
- Windows の実機、Steam の実績・クラウド・オーバーレイは、App ID がないのでまだ確かめていない。App ID が出たら Windows で `npm start` して確かめる
- `TrapOfLily.exe` には署名をしていない（Steam で配るなら署名がなくても動く。初回に SmartScreen の警告が出ることはある）
