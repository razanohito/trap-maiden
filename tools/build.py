"""src/game.html から公開用の2つを作る。

- index.html                     … GitHub Pages 用（doctype と html 要素を付ける）
- dist-artifact/trap-maiden.html … claude.ai Artifact 用（中身だけ。骨組みは Artifact 側が付ける）

art/ の画像（webp・png）と BGM（mp3）とフォント（woff2）は data URI にして埋め込む。
"""
import base64
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = (ROOT / "src" / "game.html").read_text(encoding="utf-8")


def embed(m: re.Match) -> str:
    """'../art/xxx.webp' や '../art/sprites/xxx.png' を data URI にする（HTML 1 枚で動かすため）"""
    data = (ROOT / "art" / m.group(1)).read_bytes()
    ext = m.group(1).rsplit(".", 1)[1]
    mime = {"png": "image/png", "webp": "image/webp", "mp3": "audio/mpeg", "woff2": "font/woff2"}[ext]
    return f"'data:{mime};base64," + base64.b64encode(data).decode() + "'"


src = re.sub(r"'\.\./art/([\w/-]+\.(?:webp|png|mp3|woff2))'", embed, src)

(ROOT / "index.html").write_text('<!doctype html>\n<html lang="ja">\n' + src + "\n</html>\n", encoding="utf-8")
out = ROOT / "dist-artifact" / "trap-maiden.html"
out.parent.mkdir(exist_ok=True)
out.write_text(src, encoding="utf-8")
print("index.html と", out.relative_to(ROOT).as_posix(), "を作りました")
