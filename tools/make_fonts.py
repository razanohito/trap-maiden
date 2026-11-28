"""ゲームで使うフォント（Zen Maru Gothic、SIL OFL）を、
src/game.html と src/lang/en.js（英語の訳）に出てくる文字だけに絞って art/fonts/*.woff2 にする。
中国語は丸ゴシックに簡体字・繁体字が無いので、Noto Sans SC / TC（SIL OFL）を
src/lang/zh-Hans.js・zh-Hant.js に出てくる文字だけに絞って zh-hans-*.woff2・zh-hant-*.woff2 にする（太さ 500・700・900）。

ストアに出すアプリはオフラインでも動く必要があるので、Google Fonts から読み込まずに埋め込む。
文言や訳を増やしたら、このスクリプトをもう一度動かす（新しい漢字が入るように）。

元の TTF（1つ 4〜15MB）は art-src/fonts/ に置く。無ければ google/fonts から取ってくる。
必要なもの: pip install fonttools brotli
"""
import json
import urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "art-src" / "fonts"
OUT_DIR = ROOT / "art" / "fonts"
BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
FONTS = {  # 新しい絵柄の版は丸ゴシックだけを使う（500・700・900）
    "zenmaru-500": "zenmarugothic/ZenMaruGothic-Medium.ttf",
    "zenmaru-700": "zenmarugothic/ZenMaruGothic-Bold.ttf",
    "zenmaru-900": "zenmarugothic/ZenMaruGothic-Black.ttf",
}
LICENSES = {"OFL-ZenMaruGothic.txt": "zenmarugothic/OFL.txt", "OFL-NotoSansSC.txt": "notosanssc/OFL.txt", "OFL-CinzelDecorative.txt": "cinzeldecorative/OFL.txt",
            "OFL-ShipporiMinchoB1.txt": "shipporiminchob1/OFL.txt"}
LOGO = {  # タイトル画面のロゴだけに使う書体（ロゴの字だけに絞るので小さい）
    "logo-latin": ("cinzeldecorative/CinzelDecorative-Bold.ttf", None),  # 名前を予約した書体（RFN）なので絞らずにそのまま woff2 にする
    "logo-mincho": ("shipporiminchob1/ShipporiMinchoB1-ExtraBold.ttf", "トラップオブリリー"),
}


def fetch(rel: str) -> Path:
    p = SRC_DIR / rel.replace("/", "_")  # OFL.txt は書体ごとに同じ名前なのでフォルダ名を付ける
    if not p.exists():
        SRC_DIR.mkdir(parents=True, exist_ok=True)
        print("取得:", rel)
        urllib.request.urlretrieve(BASE + rel, p)
    return p


text = (ROOT / "src" / "game.html").read_text(encoding="utf-8")
text += (ROOT / "src" / "lang" / "en.js").read_text(encoding="utf-8")  # 英語の訳（中国語の字は下の Noto に入れる）
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
for name, (rel, logo_chars) in LOGO.items():
    if logo_chars is None:
        font = TTFont(str(fetch(rel)))
        font.flavor = "woff2"
        out = OUT_DIR / f"{name}.woff2"
        font.save(str(out))
        print(out.relative_to(ROOT).as_posix(), out.stat().st_size // 1024, "KB")
        continue
    opts = subset.Options()
    opts.flavor = "woff2"
    font = subset.load_font(str(fetch(rel)), opts)
    sub = subset.Subsetter(opts)
    sub.populate(unicodes=sorted({ord(c) for c in logo_chars}))
    sub.subset(font)
    out = OUT_DIR / f"{name}.woff2"
    subset.save_font(font, str(out), opts)
    print(out.relative_to(ROOT).as_posix(), out.stat().st_size // 1024, "KB")
# 中国語（簡体字・繁体字）: 可変フォントから太さを取り出し、訳に出てくる字だけに絞る
from fontTools.varLib import instancer  # noqa: E402
ZH = {"zh-hans": ("notosanssc/NotoSansSC[wght].ttf", "zh-Hans.js"), "zh-hant": ("notosanstc/NotoSansTC[wght].ttf", "zh-Hant.js")}
for name, (rel, js) in ZH.items():
    zt = (ROOT / "src" / "lang" / js).read_text(encoding="utf-8")
    zch = set("".join(v for v in json.loads(zt[zt.index("= {") + 2:zt.rindex("}") + 1]).values() if v))  # 訳の字だけ（キーの日本語は入れない）
    zch |= {chr(c) for c in range(0x20, 0x7F)} | {chr(c) for c in range(0xFF01, 0xFF5F)}
    zch |= set("简体中文繁體中文")  # 言語ボタンの名前（どの言語のときも出る）
    zch |= set("　、。，．・：；？！「」『』（）〔〕［］【】〈〉《》“”‘’…‥―─～→←↑↓★☆♪♛⚑✎❦·×／〜")
    zuni = sorted(ord(c) for c in zch if ord(c) >= 0x20)
    for w in (500, 700, 900):
        font = instancer.instantiateVariableFont(TTFont(str(fetch(rel))), {"wght": w})
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.layout_features = ["*"]
        sub = subset.Subsetter(opts)
        sub.populate(unicodes=zuni)
        sub.subset(font)
        out = OUT_DIR / f"{name}-{w}.woff2"
        subset.save_font(font, str(out), opts)
        print(out.relative_to(ROOT).as_posix(), out.stat().st_size // 1024, "KB")
for name, rel in LICENSES.items():
    (OUT_DIR / name).write_bytes(fetch(rel).read_bytes())
print("文字数:", len(unicodes))
