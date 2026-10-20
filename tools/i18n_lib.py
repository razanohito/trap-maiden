"""英語対応の共通処理: src/game.html の <script> を字句に分け、日本語の入った文字列を見つける。

- tools/i18n_check.py が、ゲームに出てくる日本語の文言（$t`…` とページの HTML）と
  src/lang/en.js の訳を突き合わせるのに使う。
- 実行時の訳し方（src/game.html の $t と translateStatic）と同じ規則でキーを作る。
"""
import re
from html.parser import HTMLParser

JP = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uff66-\uff9f]")
REGEX_PREV = set("(,=:[!&|?{};+-*%<>~^")
REGEX_WORDS = {"return", "typeof", "case", "in", "of", "delete", "void", "new", "throw", "else", "do"}


def scan_js(js: str):
    """JS を読み、文字列リテラルとテンプレートの位置を返す。
    戻り値: [(kind, start, end, parts)]  kind は 'str' か 'tpl'。
    parts はテンプレートの静的な部分（${} の外）の生テキストのリスト、str なら中身1つ。
    start は開きの引用符、end は閉じの引用符の次。タグ付きテンプレートなら tag にタグ名。"""
    out = []

    def skip_ws_comments(i):
        while i < len(js):
            if js.startswith("//", i):
                j = js.find("\n", i)
                i = len(js) if j < 0 else j + 1
            elif js.startswith("/*", i):
                i = js.index("*/", i + 2) + 2
            elif js[i].isspace():
                i += 1
            else:
                break
        return i

    def read_str(i):
        q = js[i]
        j = i + 1
        while js[j] != q:
            if js[j] == "\\":
                j += 2
            else:
                if js[j] == "\n":
                    raise ValueError(f"改行を含む文字列 at {i}")
                j += 1
        out.append(("str", i, j + 1, [js[i + 1:j]], None))
        return j + 1

    def read_tpl(i, tag):
        j = i + 1
        parts, cur = [], []
        while True:
            c = js[j]
            if c == "\\":
                cur.append(js[j:j + 2]); j += 2
            elif c == "`":
                parts.append("".join(cur)); j += 1; break
            elif js.startswith("${", j):
                parts.append("".join(cur)); cur = []
                j = read_code(j + 2, "}")
            else:
                cur.append(c); j += 1
        out.append(("tpl", i, j, parts, tag))
        return j

    def read_regex(i):
        j = i + 1
        cls = False
        while True:
            c = js[j]
            if c == "\\":
                j += 2; continue
            if c == "[":
                cls = True
            elif c == "]":
                cls = False
            elif c == "/" and not cls:
                j += 1; break
            elif c == "\n":
                raise ValueError(f"正規表現の途中で改行 at {i}")
            j += 1
        while j < len(js) and js[j].isalpha():
            j += 1
        return j

    def read_code(i, end):
        depth = 0
        prev = "("  # 直前の意味のある文字（正規表現か割り算かの判定用）
        prev_word = ""
        while i < len(js):
            i2 = skip_ws_comments(i)
            if i2 != i:
                i = i2; continue
            c = js[i]
            if end and c == end and depth == 0:
                return i + 1
            if c in "'\"":
                i = read_str(i); prev = "a"; prev_word = ""; continue
            if c == "`":
                tag = prev_word if prev == "w" and prev_word not in REGEX_WORDS else None
                i = read_tpl(i, tag); prev = "a"; prev_word = ""; continue
            if c == "/":
                if prev in REGEX_PREV or (prev == "w" and prev_word in REGEX_WORDS):
                    i = read_regex(i); prev = "a"; continue
                i += 1; prev = "/"; continue
            if c in "{([":
                depth += 1
            elif c in "})]":
                depth -= 1
            m = re.compile(r"[\w$]+").match(js, i)
            if m:
                prev_word = m.group(); prev = "w"; i = m.end(); continue
            prev = c; prev_word = ""; i += 1
        return i

    read_code(0, None)
    return out


def tpl_key(parts):
    """テンプレートの静的部分から訳のキーを作る（実行時の $t と同じ: 部分のあいだに {0} {1} …）"""
    s = parts[0]
    for n, p in enumerate(parts[1:]):
        s += "{" + str(n) + "}" + p
    return s


def cook(raw: str) -> str:
    """テンプレートの生テキストを実行時の文字列にする（よく使うエスケープだけ）"""
    return re.sub(r"\\(u\{[0-9a-fA-F]+\}|u[0-9a-fA-F]{4}|.)", lambda m: {
        "n": "\n", "t": "\t", "\\": "\\", "`": "`", "'": "'", '"': '"', "$": "$",
    }.get(m.group(1), chr(int(m.group(1).strip("u{}"), 16)) if m.group(1).startswith("u") and len(m.group(1)) > 1 else m.group(1)), raw)


# ページの HTML（<body> の中、<script> より前）で訳すところ。実行時の translateStatic と同じ規則:
# 子要素が「id のない b・small・em・i・br・span」だけの要素は innerHTML まるごと、
# それ以外は直下のテキストを1つずつ。属性は aria-label・title・placeholder。translate="no" の要素は訳さない。
INLINE = {"b", "small", "em", "i", "br", "span", "strong"}
VOID = {"br", "img", "input", "meta", "link", "hr"}


class _Node:
    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent = tag, dict(attrs), parent
        self.children = []  # _Node か str


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.root = _Node("#root", [], None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = _Node(tag, attrs, self.cur)
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(_Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not self.root and n.tag != tag:
            n = n.parent
        if n is not self.root:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)

    def handle_entityref(self, name):
        self.cur.children.append(f"&{name};")

    def handle_charref(self, name):
        self.cur.children.append(f"&#{name};")


def _inner(n):
    """ブラウザの innerHTML に近い形で書き戻す（属性は "…" で囲む）"""
    s = []
    for c in n.children:
        if isinstance(c, str):
            s.append(c)
        else:
            a = "".join(f' {k}="{v}"' if v is not None else f" {k}" for k, v in c.attrs.items())
            s.append(f"<{c.tag}{a}>")
            if c.tag not in VOID:
                s.append(_inner(c) + f"</{c.tag}>")
    return "".join(s)


def _text(n):
    return "".join(c if isinstance(c, str) else _text(c) for c in n.children)


def _all_inline(n):
    return all(isinstance(c, str) or (c.tag in INLINE and "id" not in c.attrs and _all_inline(c)) for c in n.children)


def html_keys(html: str):
    """ページの HTML から訳すキーを集める"""
    b = _Builder()
    b.feed(html)
    keys = []

    def walk(n):
        for k in ("aria-label", "title", "placeholder"):
            v = n.attrs.get(k)
            if v and JP.search(v):
                keys.append(v.strip())
        if n.tag in ("script", "style") or n.attrs.get("translate") == "no":
            return
        if n.tag != "#root" and JP.search(_text(n)) and _all_inline(n) and any(not isinstance(c, str) for c in n.children):
            keys.append(" ".join(_inner(n).split()))
            return
        for c in n.children:
            if isinstance(c, str):
                if JP.search(c):
                    keys.append(" ".join(c.split()))
            else:
                walk(c)

    walk(b.root)
    return keys
