"""全身の立ち絵から、胸から上（バストアップ）の絵を切り出す → art/bust/<名前>.webp
2026-10-24 の希望「全身の立ち絵はいらない。バストアップぐらいのアイコンで OK」
- 入力: art/portrait_*.webp（4人の表情ちがい）、art/story/baron_*.webp・foe_*.webp
- 横幅はそのまま、上から BOTTOM の割合までを残す。下の端は少しだけ透明にぼかす
- チリン（羽の生えた鍵）は全身でも小さいので切らない
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "art" / "bust"
BOTTOM = {"lily": .42, "mina": .46, "noel": .42, "cecil": .42, "baron": .46, "foe_knight": .46, "foe_thief": .44, "foe_heavy": .46}
FADE = .07  # 下の端をぼかす高さ（切り出した絵に対する割合）


def who(name):
    for k in BOTTOM:
        if name.startswith(k) or name.startswith("portrait_" + k):
            return k
    raise KeyError(name)


def bust(src: Path):
    im = Image.open(src).convert("RGBA")
    h = round(im.height * BOTTOM[who(src.stem)])
    im = im.crop((0, 0, im.width, h))
    a = im.getchannel("A"); px = a.load(); fh = max(1, round(h * FADE))
    for y in range(h - fh, h):
        k = (h - y) / fh
        for x in range(im.width):
            px[x, y] = round(px[x, y] * k)
    im.putalpha(a)
    OUT.mkdir(parents=True, exist_ok=True)
    im.save(OUT / (src.stem + ".webp"), quality=90, method=6)
    return im.size


def main():
    files = sorted((ROOT / "art").glob("portrait_*.webp")) + sorted((ROOT / "art" / "story").glob("baron_*.webp")) + sorted((ROOT / "art" / "story").glob("foe_*.webp"))
    for f in files:
        print(f.stem, bust(f))


if __name__ == "__main__":
    main()
