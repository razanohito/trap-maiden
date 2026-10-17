# 罠館のリリィ（TRAP MAIDEN）

古い館の娘リリィは剣を持てず、夜ごとやって来る侵入者から逃げ回ることしかできません。プレイヤーは館の罠を仕掛けて、リリィを守ります。刻命館のように「主人公は逃げ回るだけ、戦うのは罠」というブラウザゲームです。

## 遊び方

- リリィの移動は CPU まかせです。かしこさが上がるほど上手に逃げ、侵入者を罠の上へ誘うようになります。慌てると混乱して走り回ることもあります。
- プレイヤーは罠（トラバサミ・跳ね床・落石・火柱）を選んでマスに置くだけです。同じ罠をもう一度押すと撤去できます。
- 魔力は時間で溜まります。罠を3秒以内に続けて当てると「連続」になり、得点と魂が増えます。
- 館にはもともと仕掛けがあります。トゲ床、奈落（跳ね床で落とすと一撃）、シャンデリアと槍の石像（押すと発動、魔力不要）。
- 夜は「準備」のあとフェイズ1〜3と進み、フェイズごとに置ける罠が増えます。夜明けまで守るか、侵入者を全滅させればクリアです。
- 夜を越えるたびに、集めた魂で館とリリィを強くできます。

操作: PC は 1〜4 で罠を選んでマスをクリック、Q / E で跳ね床の向き、Enter で準備を終える、P で一時停止。スマホは罠を選んでマスをタップ。

## 構成

| パス | 内容 |
|---|---|
| `src/game.html` | ゲーム本体（HTML 1 枚。外部スクリプトなし、フォントだけ Google Fonts） |
| `tools/build.py` | `src/game.html` から `index.html`（GitHub Pages 用）と `dist-artifact/trap-maiden.html`（claude.ai Artifact 用）を作る |
| `docs/art-brief.html` | ChatGPT に頼むグラフィックと演出の提案 |
| `tools/sim/` | ヘッドレスブラウザでの動作確認（罠を活かす AI の比較、地形と仕掛けの確認） |

## 更新の流れ

1. `src/game.html` を直す
2. `python tools/build.py`
3. 動作確認（下記）
4. コミットして push（GitHub Pages に反映される）。Artifact は `dist-artifact/trap-maiden.html` を publish する

## 動作確認

```bash
python -m http.server 8765 --bind 127.0.0.1
```

別のターミナルで（`playwright-core` と Chrome が必要。`PLAYWRIGHT_CORE` に playwright-core の場所を指定してもよい）:

```bash
node tools/sim/sim_terrain.js
node tools/sim/sim_lure.js
```

127.0.0.1 で開いたときだけ、デバッグ用に `window.__wanakan.G` でゲーム状態を読めます。
