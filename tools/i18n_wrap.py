"""src/game.html の <script> にある日本語の文字列で、まだ $t`…` になっていないものを探す（--write で $t`…` に書き換える）。

  python tools/i18n_wrap.py           … 見つかった文字列を表示するだけ
  python tools/i18n_wrap.py --write   … $t`…` に書き換える（'…' は $t`…` に、`…` は $t`…` に）

文字の判定に使う文字列（縦書きで寝かせる字など）は SKIP に書いて書き換えないようにする。
書き換えたあとは python tools/i18n_check.py --add で訳の抜けを出して src/lang/en.js に訳を書く。
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from i18n_lib import JP, scan_js  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SKIP = {"ー…〜～—―（）「」『』()‥：", "、。", "っゃゅょぁぃぅぇぉッャュョァィゥェォ", "日本語", "、。：（）・ 　"}  # 字の形で分ける文字列と、訳さない言語名


def main():
    path = ROOT / "src" / "game.html"
    s = path.read_text(encoding="utf-8")
    blocks = [(m.start(1), m.group(1)) for m in re.finditer(r"<script>\n(.*?)</script>", s, re.S)]
    edits = []
    for base, js in blocks:
        for kind, st, en, parts, tag in scan_js(js):
            text = "".join(parts)
            if not JP.search(text) or tag == "$t" or text in SKIP:
                continue
            if kind == "str":
                raw = parts[0].replace("\\'", "'").replace('\\"', '"').replace("`", "\\`").replace("${", "\\${")
                edits.append((base + st, base + en, "$t`" + raw + "`", text))
            elif tag is None:
                edits.append((base + st, base + st, "$t", text))
    for a, b, rep, text in edits:
        print(text[:90])
    print(len(edits), "件")
    if "--write" in sys.argv:
        for a, b, rep, _ in sorted(edits, key=lambda e: -e[0]):
            s = s[:a] + rep + s[b:]
        path.write_text(s, encoding="utf-8")
        print("書き換えました")


if __name__ == "__main__":
    main()
