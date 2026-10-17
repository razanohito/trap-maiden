"""src/game.html から公開用の2つを作る。

- index.html                     … GitHub Pages 用（doctype と html 要素を付ける）
- dist-artifact/trap-maiden.html … claude.ai Artifact 用（中身だけ。骨組みは Artifact 側が付ける）
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = (ROOT / "src" / "game.html").read_text(encoding="utf-8")

(ROOT / "index.html").write_text('<!doctype html>\n<html lang="ja">\n' + src + "\n</html>\n", encoding="utf-8")
out = ROOT / "dist-artifact" / "trap-maiden.html"
out.parent.mkdir(exist_ok=True)
out.write_text(src, encoding="utf-8")
print("index.html と", out.relative_to(ROOT).as_posix(), "を作りました")
