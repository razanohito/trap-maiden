"""英語の訳の抜けを調べる。

  python tools/i18n_check.py           … 訳のない文言と、使われていない訳を表示（抜けがあれば終了コード 1）
  python tools/i18n_check.py --add     … 訳のない文言を src/lang/en.js の末尾に null で足す（あとで訳を書く）

ゲームの文言は src/game.html の $t`…`（${} は {0} {1} … になる）と、ページの HTML（tools/i18n_lib.py の html_keys）。
訳は src/lang/en.js（window.TRAP_EN = { "日本語": "English", … }; の JSON）。
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from i18n_lib import JP, cook, html_keys, scan_js, tpl_key  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EN_PATH = ROOT / "src" / "lang" / "en.js"
HEAD = "// 英語の訳。キーは src/game.html の日本語の文言（${} は {0} {1} …）。tools/i18n_check.py で抜けを調べる\nwindow.TRAP_EN = "


def load_en():
    if not EN_PATH.exists():
        return {}
    t = EN_PATH.read_text(encoding="utf-8")
    return json.loads(t[t.index("= {") + 2:t.rindex("}") + 1])


def save_en(d):
    EN_PATH.parent.mkdir(parents=True, exist_ok=True)
    EN_PATH.write_text(HEAD + json.dumps(d, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")


def game_keys():
    s = (ROOT / "src" / "game.html").read_text(encoding="utf-8")
    keys = []
    title = re.search(r"<title>(.*?)</title>", s).group(1)
    keys.append(title)
    body = s[s.index("<body"):] if "<body" in s else s[s.index("</style>") + 8:]
    body = body[:body.index("<script")]
    keys += html_keys(body)
    for m in re.finditer(r"<script>\n(.*?)</script>", s, re.S):
        js = m.group(1)
        for kind, st, en, parts, tag in scan_js(js):
            if kind == "tpl" and tag == "$t":
                keys.append(cook(tpl_key(parts)))
    out, seen = [], set()
    for k in keys:
        if k not in seen and JP.search(k):
            seen.add(k); out.append(k)
    return out


def main():
    keys = game_keys()
    en = load_en()
    miss = [k for k in keys if en.get(k) is None]
    unused = [k for k in en if k not in set(keys)]
    if "--add" in sys.argv:
        for k in miss:
            en.setdefault(k, None)
        save_en(en)
        print(f"{len(miss)} 件を足しました（訳は null。書くまでは日本語のまま出る）")
        return 0
    print(f"文言 {len(keys)} 件・訳 {len(en)} 件")
    for k in miss:
        print("訳がない:", k)
    for k in unused:
        print("使われていない訳:", k)
    for k in keys:
        v = en.get(k)
        if v is not None:
            a = sorted(set(re.findall(r"\{\d+\}", k))); b = sorted(set(re.findall(r"\{\d+\}", v)))
            if a != b:
                print("{n} が合わない:", k, "→", v)
                miss.append(k)
            if JP.search(v):
                print("訳に日本語が残っている:", v)
    return 1 if miss else 0


if __name__ == "__main__":
    sys.exit(main())
