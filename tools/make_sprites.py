"""逃げる子4人の歩行スプライト（ドット絵）を作る。

- 1コマ 48x48px、透過 PNG。アンチエイリアスなし（1ピクセル単位で部品を置く）
- art/sprites/<名前>_walk.png … 4列×4行。行は 下・左・右・上、列は歩く順
  （接地A → 通過 → 接地B → 通過）
- art/sprites/<名前>_idle.png … 4列×1行。待機姿勢（下・左・右・上）
- 背の高さはタイル（48px）の約6割、幅は約3〜4割。足もとは y=44 にそろえる
- 体の上下は通過コマで 1px だけ。ツインテール（髪）と持ち物は 1 コマ遅れて揺れる
- 色は ChatGPT に描いてもらった設定画から取った

使い方: python tools/make_sprites.py （確認用の拡大 GIF と一覧を tools/sim/out/ に出す）
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "art" / "sprites"
PREVIEW = ROOT / "tools" / "sim" / "out"
F = 48
OUTLINE = (46, 28, 30, 255)

CHARS = {
    "lily": dict(hair=(243, 184, 200), hair2=(217, 143, 171), tip=(185, 165, 220), style="twintails", acc=(184, 48, 60),
                 dress=(140, 42, 55), dress2=(106, 29, 41), apron=(239, 226, 198), apron2=(205, 187, 152),
                 eye=(91, 61, 120), legs=(42, 32, 39), shoes=(163, 49, 59), item="lantern"),
    "mina": dict(hair=(199, 180, 230), hair2=(156, 134, 200), tip=(199, 180, 230), style="braids_hat", acc=(201, 162, 74),
                 hat=(63, 43, 82), hat2=(44, 29, 58), dress=(75, 50, 96), dress2=(51, 34, 63), apron=None, panel=(230, 220, 196),
                 cape=(58, 38, 75), eye=(47, 111, 104), legs=(42, 32, 39), shoes=(106, 65, 40), item="wand"),
    "noel": dict(hair=(168, 106, 66), hair2=(125, 74, 43), tip=(168, 106, 66), style="bun", acc=(244, 239, 230),
                 dress=(47, 86, 64), dress2=(32, 61, 45), apron=(239, 232, 218), apron2=(205, 196, 176),
                 eye=(75, 106, 58), legs=(52, 38, 34), shoes=(106, 65, 40), item="broom"),
    "cecil": dict(hair=(239, 207, 122), hair2=(201, 162, 74), tip=(239, 207, 122), style="short", acc=(63, 143, 138),
                  dress=(106, 70, 48), dress2=(76, 50, 34), apron=None, blouse=(239, 227, 207), vest=(185, 138, 58),
                  eye=(74, 111, 154), legs=(42, 32, 39), shoes=(106, 65, 40), item="flask"),
}
SKIN, SKIN2, BLUSH = (247, 220, 203), (226, 190, 170), (240, 160, 168)
GOLD, GOLD2, FLAME = (201, 162, 74), (140, 106, 40), (255, 215, 106)


class Pix:
    def __init__(self):
        self.im = Image.new("RGBA", (F, F), (0, 0, 0, 0)); self.px = self.im.load()

    def p(self, x, y, c):
        if 0 <= x < F and 0 <= y < F:
            self.px[x, y] = tuple(c) + (255,) if len(c) == 3 else c

    def r(self, x0, y0, x1, y1, c):  # 端を含む長方形
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for x in range(min(x0, x1), max(x0, x1) + 1):
                self.p(x, y, c)

    def outline(self):
        src = self.im.copy().load()
        for y in range(F):
            for x in range(F):
                if src[x, y][3]:
                    continue
                if any(0 <= x + dx < F and 0 <= y + dy < F and src[x + dx, y + dy][3] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    self.px[x, y] = OUTLINE


def legs_front(g, c, phase, bob):
    """正面・後ろ向きの脚。接地コマは後ろ足（もう片方）を 1〜2px 持ち上げる"""
    lift_l = 2 if phase == 2 else 0
    lift_r = 2 if phase == 0 else 0
    for x0, lift in ((21, lift_l), (25, lift_r)):
        top, foot = 38 + bob, 42 - lift
        g.r(x0, top, x0 + 1, foot, c["legs"])
        g.r(x0 - (1 if x0 == 21 else 0), foot + 1, x0 + 1 + (1 if x0 == 25 else 0), foot + 2, c["shoes"])


def legs_side(g, c, phase, bob):
    """横向き（左向き）の脚。手前の脚は明るく、奥の脚は暗くして交互に見せる"""
    far = tuple(max(0, v - 18) for v in c["legs"])
    pos = {0: (19, 26, 0, 1), 1: (23, 23, 1, 0), 2: (26, 19, 1, 0), 3: (23, 23, 0, 1)}[phase]
    near_x, far_x, near_lift, far_lift = pos
    for x0, lift, col in ((far_x, far_lift, far), (near_x, near_lift, c["legs"])):
        g.r(x0, 38 + bob, x0 + 1, 42 - lift, col)
        g.r(x0 - 1, 43 - lift, x0 + 1, 44 - lift, c["shoes"] if col == c["legs"] else tuple(max(0, v - 25) for v in c["shoes"]))


def skirt(g, c, view, phase, bob):
    sway = {0: -1, 2: 1}.get(phase, 0)
    rows = [(30, 20, 27), (31, 19, 28), (32, 19, 28), (33, 18, 29), (34, 18, 29), (35, 18, 29), (36, 17, 30), (37, 17, 30)]
    for y, x0, x1 in rows:
        s = sway if y >= 35 else 0
        g.r(x0 + s, y + bob, x1 + s, y + bob, c["dress"])
        g.p(x1 + s, y + bob, c["dress2"])
    hem = c["panel"] if c.get("panel") else (c["apron"] or (239, 227, 207))
    for x in range(17, 31):  # 裾のフリル（1px おきに凹凸）
        g.p(x + sway, 38 + bob, hem if (x % 2 == 0) else tuple(max(0, v - 30) for v in hem))
    if c.get("panel") and view == "down":
        g.r(23, 31 + bob, 24, 37 + bob, c["panel"])
    if c["style"] == "short" and view != "up":  # セシルのスカートのポケット
        g.r(19, 33 + bob, 20, 34 + bob, c["dress2"]); g.r(27, 33 + bob, 28, 34 + bob, c["dress2"])


def torso(g, c, view, bob):
    body = c.get("vest") or c["dress"]
    if view == "side":
        g.r(21, 24 + bob, 26, 29 + bob, body)
    else:
        g.r(20, 24 + bob, 27, 29 + bob, body); g.p(27, 25 + bob, c["dress2"])
    if c.get("cape"):  # ミーナのケープ
        g.r(19 if view != "side" else 20, 25 + bob, 28 if view != "side" else 27, 28 + bob, c["cape"])
        g.r(19 if view != "side" else 20, 28 + bob, 28 if view != "side" else 27, 28 + bob, GOLD2)
    if view == "down":
        collar = c.get("blouse") or (239, 230, 210)
        g.r(22, 24 + bob, 25, 24 + bob, collar)
        g.r(23, 25 + bob, 24, 25 + bob, c["acc"] if c["style"] != "bun" else c["dress2"])
        if c["apron"]:
            g.r(21, 28 + bob, 26, 36 + bob, c["apron"]); g.r(26, 29 + bob, 26, 36 + bob, c["apron2"])
            g.r(22, 26 + bob, 25, 27 + bob, c["apron"])
        if c["style"] == "short":  # ベルトと小瓶
            g.r(20, 30 + bob, 27, 30 + bob, (90, 58, 40)); g.p(21, 31 + bob, (111, 201, 192)); g.p(26, 31 + bob, (111, 201, 192))
    elif view == "up":
        if c["apron"]:  # エプロンの紐と後ろのリボン
            g.p(21, 24 + bob, c["apron"]); g.p(26, 24 + bob, c["apron"]); g.r(21, 25 + bob, 21, 29 + bob, c["apron"]); g.r(26, 25 + bob, 26, 29 + bob, c["apron"])
            g.r(20, 29 + bob, 27, 30 + bob, c["apron"]); g.p(23, 30 + bob, c["apron2"]); g.p(24, 30 + bob, c["apron2"])
            g.r(22, 31 + bob, 22, 35 + bob, c["apron"]); g.r(25, 31 + bob, 25, 35 + bob, c["apron"])
        if c["style"] == "short":
            g.r(22, 25 + bob, 22, 29 + bob, (90, 58, 40)); g.r(25, 25 + bob, 25, 29 + bob, (90, 58, 40))
    else:
        if c["apron"]:
            g.r(19, 28 + bob, 20, 36 + bob, c["apron"]); g.r(21, 25 + bob, 21, 28 + bob, c["apron"])
        if c["style"] == "short":
            g.r(21, 30 + bob, 26, 30 + bob, (90, 58, 40))


def arms_front(g, c, phase, bob, view):
    sleeve = c.get("blouse") or c["dress"]
    swing = {0: (0, 1), 2: (1, 0)}.get(phase, (0, 0))  # 手の上下（足と反対）
    hold = item_side(c, view)
    for i, x0 in enumerate((18, 28)):
        dy = 0 if (i == hold) else swing[i]  # 持ち物を持つ腕は振らない
        g.r(x0, 25 + bob, x0 + 1, 30 + bob, sleeve)
        g.p(x0 + (0 if i == 0 else 1), 26 + bob, sleeve if c.get("blouse") else c["dress2"])
        g.r(x0, 31 + bob + dy, x0 + 1, 31 + bob + dy, SKIN)


def item_side(c, view):
    """持ち物を持つ側（0=画面の左、1=画面の右）。右手に持つので、正面では画面の左、後ろ向きでは画面の右"""
    return 0 if view == "down" else 1


def draw_item(g, c, view, hx, hy, lag):
    it = c["item"]
    if it == "lantern":
        x, y = hx - 1 + lag, hy + 1
        g.r(x + 1, y, x + 2, y, GOLD2)
        g.r(x, y + 1, x + 3, y + 5, GOLD); g.r(x + 1, y + 2, x + 2, y + 4, FLAME); g.p(x + 1, y + 2, (255, 245, 200))
        g.r(x, y + 5, x + 3, y + 5, GOLD2)
    elif it == "wand":
        x, y = hx + lag, hy
        for k in range(5):
            g.p(x - k // 2, y - k, (110, 80, 50))
        g.r(x - 3, y - 7, x - 2, y - 6, (127, 224, 138)); g.p(x - 3, y - 7, (210, 255, 210))
    elif it == "broom":
        x = hx + lag
        g.r(x, 22, x, 38, (138, 106, 58))
        g.r(x - 2, 38, x + 2, 39, (190, 160, 80)); g.r(x - 3, 40, x + 3, 44, (201, 166, 90))
        for k in range(-3, 4, 2):
            g.p(x + k, 44, (150, 120, 60))
    elif it == "flask":
        x, y = hx - 1 + lag, hy - 1
        g.p(x + 1, y, (200, 200, 190)); g.r(x, y + 1, x + 2, y + 3, (111, 201, 192)); g.p(x, y + 1, (200, 240, 235))


def head(g, c, view, bob, tail_dx):
    y0 = 14 + bob
    hair, hair2 = c["hair"], c["hair2"]
    st = c["style"]
    # 後ろ髪（ツインテール・三つ編み）
    if st == "twintails":
        for side in (0, 1) if view != "side" else (1,):
            bx = 16 if side == 0 else 30
            if view == "side":
                bx = 28
            for k, y in enumerate(range(y0 + 3, y0 + 17)):
                wob = (0, 0, -1, -1, 0, 0, 1, 1, 0, 0, -1, -1, 0, 0)[k] * (1 if side == 0 else -1)
                dx = tail_dx if k > 6 else 0
                col = c["tip"] if k >= 11 else (hair if k % 4 else hair2)
                g.r(bx + wob + dx, y, bx + 2 + wob + dx, y, col)
    elif st == "braids_hat":
        for side in (0, 1) if view != "side" else (1,):
            bx = 18 if side == 0 else 28
            if view == "side":
                bx = 26
            for k, y in enumerate(range(y0 + 6, y0 + 18)):
                dx = tail_dx if k > 5 else 0
                g.r(bx + dx, y, bx + 1 + dx, y, hair if (k % 2) else hair2)
            g.p(bx + (tail_dx), y0 + 18, c["acc"])
    # 顔と髪
    if view == "up":
        g.r(20, y0 + 1, 27, y0 + 9, hair); g.r(19, y0 + 2, 28, y0 + 8, hair)
        g.r(23, y0 + 1, 24, y0 + 9, hair2)
    elif view == "side":
        g.r(19, y0 + 4, 24, y0 + 9, SKIN); g.p(18, y0 + 6, SKIN); g.p(24, y0 + 9, SKIN2)
        g.r(21, y0, 27, y0 + 4, hair); g.r(22, y0 + 4, 28, y0 + 9, hair); g.r(20, y0 + 1, 26, y0 + 3, hair)
        g.r(19, y0 + 2, 21, y0 + 4, hair); g.p(19, y0 + 5, hair2)
        g.r(20, y0 + 6, 20, y0 + 7, c["eye"]); g.p(21, y0 + 8, BLUSH)
    else:
        g.r(20, y0 + 4, 27, y0 + 10, SKIN); g.r(21, y0 + 11, 26, y0 + 11, SKIN2)
        g.r(20, y0, 27, y0 + 3, hair); g.r(19, y0 + 1, 28, y0 + 4, hair)
        g.r(19, y0 + 5, 19, y0 + 9, hair); g.r(28, y0 + 5, 28, y0 + 9, hair)
        for x in (21, 23, 24, 26):  # 前髪
            g.p(x, y0 + 5, hair)
        g.p(22, y0 + 4, hair2); g.p(25, y0 + 4, hair2)
        g.r(21, y0 + 6, 21, y0 + 7, c["eye"]); g.r(26, y0 + 6, 26, y0 + 7, c["eye"])
        g.p(20, y0 + 8, BLUSH); g.p(27, y0 + 8, BLUSH)
    # 頭の飾り
    if st == "twintails":
        for bx in ((16, 29) if view != "side" else (26,)):
            g.r(bx, y0, bx + 2, y0 + 2, c["acc"]); g.p(bx + 1, y0 + 1, tuple(max(0, v - 40) for v in c["acc"]))
    elif st == "braids_hat":
        hat, hat2 = c["hat"], c["hat2"]
        g.r(15, y0 + 2, 32, y0 + 3, hat2 if view == "up" else hat); g.r(16, y0 + 3, 31, y0 + 3, hat2)
        g.r(20, y0 - 2, 27, y0 + 1, hat); g.r(21, y0 - 4, 26, y0 - 2, hat); g.r(23, y0 - 6, 25, y0 - 4, hat); g.r(25, y0 - 7, 27, y0 - 6, hat2)
        g.r(20, y0 + 1, 27, y0 + 1, c["acc"])
    elif st == "bun":
        g.r(21, y0 - 3, 26, y0 - 1, c["hair2"] if view == "up" else hair); g.r(22, y0 - 4, 25, y0 - 4, hair)
        g.r(19, y0 + 1, 28, y0 + 1, c["acc"]); g.p(19, y0, c["acc"]); g.p(28, y0, c["acc"])
    elif st == "short":
        g.r(18, y0 + 3, 18, y0 + 9, hair); g.r(29, y0 + 3, 29, y0 + 9, hair)
        if view != "side":
            g.r(19, y0 + 10, 19, y0 + 11, hair); g.r(28, y0 + 10, 28, y0 + 11, hair)
        if view != "up":
            g.r(19, y0 + 2, 28, y0 + 2, (176, 138, 74))  # ゴーグル
            if view == "down":
                g.r(21, y0 + 1, 22, y0 + 3, (210, 180, 110)); g.r(25, y0 + 1, 26, y0 + 3, (210, 180, 110))
            else:
                g.r(20, y0 + 1, 21, y0 + 3, (210, 180, 110))
        g.r(28 if view != "side" else 26, y0, 30 if view != "side" else 28, y0 + 2, c["acc"])  # リボン


def frame(c, view, phase, idle=False):
    """view: down / side（左向き） / up。phase 0〜3（idle は立ち姿）"""
    g = Pix()
    if idle:
        phase = 1
    bob = -1 if (phase in (1, 3) and not idle) else 0
    lag_phase = (phase + 3) % 4  # 1 コマ遅れ
    tail_dx = 0 if idle else (0, -1, 0, 1)[lag_phase]
    item_lag = 0 if idle else (0, 1, 0, -1)[lag_phase] if c["item"] != "broom" else 0
    if idle:
        phase_legs = 1
    else:
        phase_legs = phase
    # 奥から手前へ: 後ろ髪 → 持ち物（後ろ向きのとき）→ 脚 → スカート → 胴 → 腕 → 頭 → 持ち物
    if view == "side":
        legs_side(g, c, phase_legs, bob)
    else:
        if idle:
            legs_front(g, c, 1, 0)
        else:
            legs_front(g, c, phase_legs if view == "down" else (phase_legs + 2) % 4, bob)
    skirt(g, c, view, phase, bob)
    torso(g, c, view, bob)
    if view == "side":
        swing = 0 if idle else {0: 2, 2: -1}.get(phase, 0)
        if c["item"] in ("lantern", "flask"):
            swing = max(-1, min(1, swing))  # 持ち物の腕は振り幅を抑える
        sleeve = c.get("blouse") or c["dress"]
        g.r(23 + swing // 2, 25 + bob, 25 + swing // 2, 30 + bob, sleeve)
        hx, hy = 23 + swing, 31 + bob
        g.r(hx, hy, hx + 1, hy, SKIN)
        head(g, c, view, bob, tail_dx)
        draw_item(g, c, view, hx - (2 if c["item"] == "broom" else 0), hy, item_lag)
    else:
        arms_front(g, c, phase if not idle else 1, bob, view)
        head(g, c, view, bob, tail_dx)
        side = item_side(c, view)
        hx = 18 if side == 0 else 29
        draw_item(g, c, view, hx - (1 if side == 0 else -1) * (1 if c["item"] == "broom" else 0), 31 + bob, item_lag)
    g.outline()
    return g.im


def sheet(c):
    walk = Image.new("RGBA", (F * 4, F * 4), (0, 0, 0, 0))
    idle = Image.new("RGBA", (F * 4, F), (0, 0, 0, 0))
    views = [("down", False), ("side", False), ("side", True), ("up", False)]  # 行: 下・左・右（左の反転）・上
    for row, (view, mirror) in enumerate(views):
        for col in range(4):
            im = frame(c, view, col)
            if mirror:
                im = im.transpose(Image.FLIP_LEFT_RIGHT)
            walk.paste(im, (col * F, row * F))
        im = frame(c, view, 1, idle=True)
        if mirror:
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        idle.paste(im, (row * F, 0))
    return walk, idle


def main():
    OUT.mkdir(parents=True, exist_ok=True); PREVIEW.mkdir(parents=True, exist_ok=True)
    for name, c in CHARS.items():
        walk, idle = sheet(c)
        walk.save(OUT / f"{name}_walk.png"); idle.save(OUT / f"{name}_idle.png")
        # 確認用: 6倍に拡大した歩行 GIF（4方向を横に並べる）と一覧
        S = 6
        frames = []
        for col in range(4):
            fr = Image.new("RGBA", (F * 4 * S, F * S), (58, 50, 64, 255))
            for row in range(4):
                cell = walk.crop((col * F, row * F, col * F + F, row * F + F)).resize((F * S, F * S), Image.NEAREST)
                fr.alpha_composite(cell, (row * F * S, 0))
            frames.append(fr.convert("P", palette=Image.ADAPTIVE))
        frames[0].save(PREVIEW / f"walk_{name}.gif", save_all=True, append_images=frames[1:], duration=100, loop=0, disposal=2)
        big = Image.new("RGBA", (F * 5 * S, F * 4 * S), (58, 50, 64, 255))
        big.alpha_composite(walk.resize((F * 4 * S, F * 4 * S), Image.NEAREST), (0, 0))
        for row in range(4):
            big.alpha_composite(idle.crop((row * F, 0, row * F + F, F)).resize((F * S, F * S), Image.NEAREST), (F * 4 * S, row * F * S))
        big.save(PREVIEW / f"sprites_{name}.png")
        print(name, "ok")


if __name__ == "__main__":
    main()
