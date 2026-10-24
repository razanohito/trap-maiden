"""ゲームで使うフォント（Zen Maru Gothic、SIL OFL）を、
src/game.html と src/lang/*.js（訳）に出てくる文字だけに絞って art/fonts/*.woff2 にする。

ストアに出すアプリはオフラインでも動く必要があるので、Google Fonts から読み込まずに埋め込む。
文言や訳を増やしたら、このスクリプトをもう一度動かす（新しい漢字が入るように）。

元の TTF（1つ 4〜15MB）は art-src/fonts/ に置く。無ければ google/fonts から取ってくる。
必要なもの: pip install fonttools brotli
"""
import urllib.request
from pathlib import Path

from fontTools import subset

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "art-src" / "fonts"
OUT_DIR = ROOT / "art" / "fonts"
BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
FONTS = {  # 新しい絵柄の版は丸ゴシックだけを使う（500・700・900）
    "zenmaru-500": "zenmarugothic/ZenMaruGothic-Medium.ttf",
    "zenmaru-700": "zenmarugothic/ZenMaruGothic-Bold.ttf",
    "zenmaru-900": "zenmarugothic/ZenMaruGothic-Black.ttf",
}
LICENSES = {"OFL-ZenMaruGothic.txt": "zenmarugothic/OFL.txt"}


def fetch(rel: str) -> Path:
    p = SRC_DIR / rel.replace("/", "_")  # OFL.txt は書体ごとに同じ名前なのでフォルダ名を付ける
    if not p.exists():
        SRC_DIR.mkdir(parents=True, exist_ok=True)
        print("取得:", rel)
        urllib.request.urlretrieve(BASE + rel, p)
    return p


text = (ROOT / "src" / "game.html").read_text(encoding="utf-8")
text += "".join(f.read_text(encoding="utf-8") for f in sorted((ROOT / "src" / "lang").glob("*.js")))  # 英語などの訳
chars = set(text)
chars |= {chr(c) for c in range(0x20, 0x7F)}      # 英数字・記号
chars |= {chr(c) for c in range(0x3000, 0x3100)}  # 和文の記号・ひらがな・カタカナ
chars |= {chr(c) for c in range(0xFF01, 0xFF5F)}  # 全角英数字
unicodes = sorted(ord(c) for c in chars if ord(c) >= 0x20)

OUT_DIR.mkdir(parents=True, exist_ok=True)
for name, rel in FONTS.items():
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    font = subset.load_font(str(fetch(rel)), opts)
    sub = subset.Subsetter(opts)
    sub.populate(unicodes=unicodes)
    sub.subset(font)
    out = OUT_DIR / f"{name}.woff2"
    subset.save_font(font, str(out), opts)
    print(out.relative_to(ROOT).as_posix(), out.stat().st_size // 1024, "KB")
for name, rel in LICENSES.items():
    (OUT_DIR / name).write_bytes(fetch(rel).read_bytes())
print("文字数:", len(unicodes))
