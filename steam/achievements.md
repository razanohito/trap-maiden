# Steam の実績（23個）

Steamworks の「実績」画面で、下の **API 名** のとおりに作ります（ゲームは `ACH_` + ゲームの id を大文字、で解除します。`desktop/main.js`）。
表示名と説明は日本語と英語の両方を入れます。アイコンは `steam/achievements/<API名>.jpg`（取った）と `<API名>_locked.jpg`（まだ）。256×256。

| API 名 | 名前（日本語） | 説明（日本語） | Name (English) | Description (English) |
| --- | --- | --- | --- | --- |
| ACH_NIGHT1 | 最初の夜明け | 夜を1つ越える | First Dawn | Survive one night |
| ACH_STAGE10 | 館の見習い | ステージ10をクリア | Manor Apprentice | Clear Stage 10 |
| ACH_STAGE20 | 罠の名手 | ステージ20をクリア | Trap Master | Clear Stage 20 |
| ACH_STAGE40 | トラップオブリリー | ステージ40をクリア | Trap of Lily | Clear Stage 40 |
| ACH_CHALLENGE | 十夜の守り手 | チャレンジ（全10夜）をクリア | Guardian of Ten Nights | Clear the Challenge (10 nights) |
| ACH_COMBO10 | 連続10 | 罠を10連続で当てる | Combo 10 | Land a 10-trap combo |
| ACH_COMBO20 | 連続20 | 罠を20連続で当てる | Combo 20 | Land a 20-trap combo |
| ACH_COMBO30 | 止まらない罠 | 罠を30連続で当てる | Unstoppable Traps | Land a 30-trap combo |
| ACH_FUSION | 合成の手ほどき | 罠を初めて合成する | Fusion Lesson | Fuse traps for the first time |
| ACH_FUSION20 | 合成の達人 | 合成した罠を合計20回作動させる | Fusion Master | Trigger fused traps 20 times in total |
| ACH_TRIPLE | まとめて三つ | 1回の罠で3体以上に当てる | Three at Once | Hit 3 or more with one trap |
| ACH_CRASH | 玉突き名人 | 1回の夜で玉突きを5回 | Collision Expert | 5 collisions in one night |
| ACH_PIT | 奈落の番人 | 1回の夜で奈落に5体落とす | Keeper of the Pit | Drop 5 into pits in one night |
| ACH_OIUCHI | 追い打ち | 追い打ちを合計50回 | Follow-ups | 50 follow-up hits in total |
| ACH_WEAK | 弱点を知る者 | 「効いた！」を合計50回 | Knows Their Weakness | Get "Effective!" 50 times in total |
| ACH_ITEMS | 宝物集め | スコアアイテムを合計30個拾う | Treasure Hunter | Pick up 30 score items in total |
| ACH_CROWN | 王冠 | 王冠を拾う | Crown | Pick up a crown |
| ACH_NOHIT | 無傷の夜 | 体力を減らさずに夜を越える（第3夜以降・ステージ3以降・自作の部屋は強さ3以上） | Flawless Night | Survive a night without losing HP (Night 3+, Stage 3+, or a custom room at strength 3+) |
| ACH_EDITOR | 館の設計士 | 自分で作ったステージをクリア | Manor Architect | Clear a stage you built yourself |
| ACH_ENDLESS50 | 終わらない夜 | 無限の夜で50連続 | Night Without End | 50 combo in Endless Night |
| ACH_ALL4 | 4人の守り | 4人全員で、いずれかのステージかチャレンジをクリア | Guarded by Four | Clear any stage or the Challenge with each of the 4 runners |
| ACH_MASTER | 百合の館の主 | 8つの百合の印をすべてともし、おはなしの結びを見る | Mistress of Lily Manor | Light all 8 Lily Seals and see the story's ending |
| ACH_TRUTH | さかさまの夜 | さかさまの夜で、ほんとうの結末を見る | The Upside-Down Night | See the true ending in The Upside-Down Night |
