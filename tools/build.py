"""src/game.html（新しい絵柄「月夜のおかし箱」の版）から公開用の2つを作る。

- v2/index.html                     … GitHub Pages 用（doctype と html 要素を付ける）。…/trap-maiden/v2/ で開く
- dist-artifact/trap-maiden-v2.html … claude.ai Artifact 用（中身だけ。骨組みは Artifact 側が付ける）

前の絵柄の版（index.html と dist-artifact/trap-maiden.html）は別の版として残してあり、このビルドでは書き換えない。

art/ の画像（webp・png）と BGM（mp3）とフォント（woff2）は data URI にして埋め込む。英語の訳（src/lang/en.js）も中に書き込む。

彩度（SAT）: 絵も画面の色も、ここでまとめて同じ割合だけ落とす（ユーザーの希望 2026-10-21「ギャルゲーっぽい」ので少し落ち着かせる）。
src/game.html と art/ の元の色はそのまま。1.0 にすると元の鮮やかさに戻る。
"""
import base64
import io
import re
from pathlib import Path

from PIL import Image, ImageEnhance

SAT = 0.78

ROOT = Path(__file__).resolve().parent.parent
src = (ROOT / "src" / "game.html").read_text(encoding="utf-8")


def mute(rgb):
    """1 色の彩度を落とす（明るさ＝輝度はそのまま。PIL の ImageEnhance.Color と同じ式）"""
    y = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    return [max(0, min(255, round(y + (c - y) * SAT))) for c in rgb]


def mute_hex(m: re.Match) -> str:
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return "#" + "".join(f"{c:02x}" for c in mute([int(h[i:i + 2], 16) for i in (0, 2, 4)]))


def mute_rgb(m: re.Match) -> str:
    r, g, b = mute([int(m.group(i)) for i in (2, 3, 4)])
    return f"{m.group(1)}({r},{g},{b}{m.group(5)}"


def mute_image(data: bytes, ext: str) -> bytes:
    if SAT == 1:
        return data
    im = Image.open(io.BytesIO(data))
    im.load()
    alpha = im.getchannel("A") if "A" in im.getbands() else None
    out = ImageEnhance.Color(im.convert("RGB")).enhance(SAT)
    if alpha is not None:
        out.putalpha(alpha)
    buf = io.BytesIO()
    if ext == "webp":
        out.save(buf, "WEBP", quality=90, method=4)
    else:
        out.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def embed(m: re.Match) -> str:
    """'../art/xxx.webp' や '../art/sprites/xxx.png' を data URI にする（HTML 1 枚で動かすため）"""
    path = ROOT / "art" / m.group(1)
    if not path.exists():  # まだ作っていない絵・曲（部屋の絵・おはなしの曲など）は空にする。ゲームは代わりを使う
        return "''"
    data = path.read_bytes()
    ext = m.group(1).rsplit(".", 1)[1]
    if ext in ("webp", "png"):
        data = mute_image(data, ext)
    mime = {"png": "image/png", "webp": "image/webp", "mp3": "audio/mpeg", "woff2": "font/woff2"}[ext]
    return f"'data:{mime};base64," + base64.b64encode(data).decode() + "'"


# 先に色（#rgb・#rrggbb・rgb()・rgba()）を落としてから、絵を埋め込む（data URI の中を色と間違えないように）
src = re.sub(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", mute_hex, src)
src = re.sub(r"\b(rgba?)\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*([,)])", mute_rgb, src)

# 英語の訳（src/lang/en.js）を中に書き込む
en_js = (ROOT / "src" / "lang" / "en.js").read_text(encoding="utf-8")
src = src.replace('<script src="lang/en.js"></script>', "<script>\n" + en_js.strip() + "\n</script>")

src = re.sub(r"'\.\./art/([\w/-]+\.(?:webp|png|mp3|woff2))'", embed, src)

page = ROOT / "v2" / "index.html"
page.parent.mkdir(exist_ok=True)
page.write_text('<!doctype html>\n<html lang="ja">\n' + src + "\n</html>\n", encoding="utf-8")
out = ROOT / "dist-artifact" / "trap-maiden-v2.html"
out.parent.mkdir(exist_ok=True)
out.write_text(src, encoding="utf-8")
print(page.relative_to(ROOT).as_posix(), "と", out.relative_to(ROOT).as_posix(), "を作りました")
