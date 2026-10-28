"""ゲームの BGM を楽譜（このファイル）から作る。ゴシックの室内楽（チェンバロ・オルガン・オルゴール・弦）。

- 全曲で「館の主題」（THEME_A / THEME_B）を使い回して、統一感を出す
- 楽譜 → MIDI → fluidsynth（FluidR3_GM サウンドフォント）で音にする → 音量を -18 LUFS にそろえて mp3
- ループ曲は「1周ぶん + 1.2秒」の長さで書き出す。ゲームは終わりの 1.2 秒を次の周と重ねるので、つなぎ目が切れない
- 出力: art/bgm/bgm_*.mp3・jingle_*.mp3（ステレオ 80kbps・32kHz（ゲームに埋め込むので軽く））。元の MIDI は art-src/bgm-midi/ に残す

使い方: python tools/compose_bgm.py [曲名 ...]（fluidsynth・ffmpeg・FluidR3_GM.sf2 が必要。
        Ubuntu なら apt install fluidsynth fluid-soundfont-gm）
"""
import random
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "art" / "bgm"
MID = ROOT / "art-src" / "bgm-midi"
SF2 = Path("/usr/share/sounds/sf2/FluidR3_GM.sf2")
XF = 1.2  # ゲーム側のループのつなぎ（BGM_XF）と同じ
RATE = 44100

# ---------- 楽譜の書き方 ----------
# 音: "D5:1"（音名+オクターブ:拍）。和音は "D4+F4+A4:2"、休みは "r:1"。小節は | で区切る（読みやすさのためだけ）
NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi_no(name):
    m = re.fullmatch(r"([A-G])([#b]?)(-?\d)", name)
    n = NOTE[m[1]] + {"#": 1, "b": -1, "": 0}[m[2]]
    return 12 * (int(m[3]) + 1) + n


def parse(src):
    """楽譜の文字列 → [(拍, [音番号...] or [], 長さ)]"""
    out, t = [], 0.0
    for tok in src.replace("|", " ").split():
        p, d = tok.split(":")
        d = float(d)
        out.append((t, [] if p == "r" else [midi_no(x) for x in p.split("+")], d))
        t += d
    return out, t


def shift(seq, semis):
    return [(t, [n + semis for n in ns], d) for t, ns, d in seq]


def to_major(seq, tonic=2):
    """短調の旋律を同主長調へ（3度・6度・7度を半音上げる）。主題の明るい版に使う"""
    up = {(tonic + 3) % 12, (tonic + 8) % 12, (tonic + 10) % 12}
    return [(t, [n + 1 if n % 12 in up else n for n in ns], d) for t, ns, d in seq]


def waltz_to_four(seq):
    """3拍子の旋律を4拍子に（各小節の最初の音を1拍のばす）"""
    out, t, bar = [], 0.0, -1
    for st, ns, d in seq:
        b = int(st // 3 + 1e-6)
        if b != bar:
            bar = b
            d = d + 1
        out.append((t, ns, d))
        t += d
    return out


# ---------- 館の主題（ニ短調・3拍子） ----------
THEME_A = """A4:1 D5:1 E5:1 | F5:2 E5:1 | D5:1 C#5:1 D5:1 | A4:3 |
             Bb4:1 D5:1 G5:1 | F5:2 E5:1 | D5:1 E5:1 C#5:1 | D5:3"""
THEME_B = """F5:1 A5:1 G5:1 | F5:2 E5:1 | D5:1 F5:1 E5:1 | C5:3 |
             Bb4:1 D5:1 F5:1 | E5:1.5 D5:.5 C#5:1 | D5:1 E5:1 F5:1 | E5:3"""
CH_A = ["Dm", "Bb C", "Dm A7 Dm", "Dm", "Gm", "Dm A7", "Gm A7", "Dm"]
CH_B = ["F", "F C", "Gm C", "C", "Bb", "A7", "Dm", "A7"]

CH_A_MAJ = ["D", "G A", "D A7 D", "D", "G", "D A7", "G A7", "D"]  # 長調版（お店・結び）
CH_B_MAJ = ["D", "D A", "Bm A", "A", "Bm", "A7", "D", "A7"]
CHORD = {"": (0, 4, 7), "m": (0, 3, 7), "5": (0, 7), "7": (0, 4, 7, 10), "m7": (0, 3, 7, 10), "dim": (0, 3, 6), "sus4": (0, 5, 7)}


def chord_pcs(name):
    m = re.fullmatch(r"([A-G][#b]?)(m7|m|7|dim|sus4|5|)", name)
    root = NOTE[m[1][0]] + {"#": 1, "b": -1}.get(m[1][1:], 0)
    return root % 12, [(root + i) % 12 for i in CHORD[m[2]]]


def bars_to_chords(bars, beats, stretch=False):
    """["Dm", "Gm A7"] → [(拍, 長さ, 和音)]。1小節に2つなら 3拍子は 2+1・4拍子は 2+2、3つなら1拍ずつ。
    stretch=True は3拍子の和音を waltz_to_four に合わせて4拍子に（最初の和音を1拍のばす）"""
    out, t = [], 0.0
    for b in bars:
        names = b.split()
        n = 3 if stretch else beats
        ds = {1: [n], 2: [n - 1, 1] if n == 3 else [2, 2], 3: [1, 1, 1] if n == 3 else [2, 1, 1]}[len(names)]
        if stretch:
            ds[0] += 1
        for name, d in zip(names, ds):
            out.append((t, d, name))
            t += d
    return out


def voice(pcs, low, high):
    return sorted(n for n in range(low, high + 1) if n % 12 in pcs)


def near(pcs, center, count=3):
    """center の近くに和音の音を count 個"""
    cand = sorted(range(center - 7, center + 9), key=lambda n: abs(n - center))
    got = []
    for n in cand:
        if n % 12 in pcs and n % 12 not in [g % 12 for g in got]:
            got.append(n)
        if len(got) == count:
            break
    return sorted(got)


# ---------- 伴奏の型 ----------
def acc_waltz(chs, oct_bass=38, center=57):
    """ズン・チャッ・チャッ"""
    bass, chord = [], []
    for t, d, n in chs:
        r, pcs = chord_pcs(n)
        b = voice([r], oct_bass, oct_bass + 11)[0]
        bass.append((t, [b], 1))
        for k in range(1, int(d)):
            chord.append((t + k, near(pcs, center), .9))
    return bass, chord


def acc_pad(chs, center=55, count=4, open5=False):
    """のばす和音。open5=True は根音と5度だけ（合唱やオルガンの空5度。経過音とぶつからない）"""
    out = []
    for t, d, n in chs:
        r, pcs = chord_pcs(n)
        out.append((t, near([r, (r + 7) % 12] if open5 else pcs, center, min(count, 2) if open5 else count), d))
    return out


def acc_bass(chs, low=33, step=None):
    """根音。step=拍 なら刻む"""
    out = []
    for t, d, n in chs:
        r, _ = chord_pcs(n)
        b = voice([r], low, low + 11)[0]
        if step:
            k = 0.0
            while k < d - 1e-6:
                out.append((t + k, [b], step * .9))
                k += step
        else:
            out.append((t, [b], d))
    return out


def acc_arp(chs, step=.5, center=60, pattern=(0, 1, 2, 1)):
    out = []
    for t, d, n in chs:
        ns = near(chord_pcs(n)[1], center, 3)
        k, i = 0.0, 0
        while k < d - 1e-6:
            out.append((t + k, [ns[pattern[i % len(pattern)]]], step * .95))
            k += step
            i += 1
    return out


def acc_ostinato(chs, step=.5, low=45):
    """ピチカートの「根音・5度・オクターブ・5度」"""
    out = []
    for t, d, n in chs:
        r, pcs = chord_pcs(n)
        b = voice([r], low, low + 11)[0]
        fifth = b + 7 if (b + 7) % 12 in pcs else b + 6
        pat = [b, fifth, b + 12, fifth]
        k, i = 0.0, 0
        while k < d - 1e-6:
            out.append((t + k, [pat[i % 4]], step * .6))
            k += step
            i += 1
    return out


def oompah(chs, low=36, center=55):
    """ブン・チャッ（2拍ずつ）"""
    bass, chord = [], []
    for t, d, n in chs:
        r, pcs = chord_pcs(n)
        b = voice([r], low, low + 11)[0]
        k = 0.0
        while k < d - 1e-6:
            bass.append((t + k, [b if int(k) % 2 == 0 else b + 7 - (0 if (b + 7) % 12 in pcs else 1)], .8))
            chord.append((t + k + 1, near(pcs, center), .7))
            k += 2
    return bass, chord


def cat(*parts):
    """[(seq, 長さ)] を順につなぐ"""
    out, t = [], 0.0
    for seq, length in parts:
        out += [(s + t, ns, d) for s, ns, d in seq]
        t += length
    return out


def drums(pattern, bars, beats, note):
    """打楽器（10ch）。pattern = 1小節内の拍の位置"""
    return [(b * beats + p, [note], .2) for b in range(int(bars)) for p in pattern]


# ---------- MIDI 書き出し ----------
GM = {"harpsichord": 6, "celesta": 8, "glock": 9, "musicbox": 10, "bells": 14, "organ": 19, "reed": 20,
      "violin": 40, "cello": 42, "contrabass": 43, "tremolo": 44, "pizz": 45, "harp": 46, "timpani": 47,
      "strings": 48, "slowstr": 49, "choir": 52, "tuba": 58, "oboe": 68, "bassoon": 70, "clarinet": 71, "flute": 73}


def vlq(n):
    b = [n & 0x7F]
    n >>= 7
    while n:
        b.append(0x80 | (n & 0x7F))
        n >>= 7
    return bytes(reversed(b))


def write_midi(path, tempo, parts, length, seed=1):
    """parts = [(楽器, 音量0-127, パン0-127, seq)]。length 拍の後ろに余韻を足す"""
    rnd = random.Random(seed)
    TPQ = 480
    tracks = []
    head = [(0, bytes([0xFF, 0x51, 3]) + int(60_000_000 / tempo).to_bytes(3, "big"))]
    tracks.append(head + [(int((length + 8) * TPQ), b"\xFF\x2F\x00")])
    ch_free = [c for c in range(16) if c != 9]
    for inst, vel, pan, seq in parts:
        if inst == "drum":
            ch, prog = 9, None
        else:
            ch, prog = ch_free.pop(0), GM[inst]
        ev = [(0, bytes([0xB0 | ch, 7, 100])), (0, bytes([0xB0 | ch, 10, pan])), (0, bytes([0xB0 | ch, 91, 70]))]
        if prog is not None:
            ev.append((0, bytes([0xC0 | ch, prog])))
        for t, ns, d in seq:
            for k, n in enumerate(ns):
                on = max(0, int(t * TPQ) + rnd.randint(0, 6) + k * 3)
                off = max(on + 10, int((t + d) * TPQ) - 8)
                v = max(1, min(127, vel + rnd.randint(-6, 6) + (6 if abs(t % 1) < 1e-6 else 0)))
                ev.append((on, bytes([0x90 | ch, n, v])))
                ev.append((off, bytes([0x80 | ch, n, 0])))
        ev.sort(key=lambda e: (e[0], e[1][0] & 0xF0 == 0x90))
        ev.append((max(e[0] for e in ev), b"\xFF\x2F\x00"))
        tracks.append(ev)
    data = b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks), TPQ)
    for ev in tracks:
        body, last = b"", 0
        for t, msg in ev:
            body += vlq(t - last) + msg
            last = t
        data += b"MTrk" + struct.pack(">I", len(body)) + body
    path.write_bytes(data)


def render(name, tempo, parts, length, loop=True, gain_db=0.0):
    MID.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    sec = length * 60 / tempo
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        if loop:  # 3周ぶん鳴らして、2周目の頭から「1周 + 1.2秒」を切り出す（頭に前の周の余韻が乗る）
            parts3 = [(i, v, p, cat((s, length), (s, length), (s, length))) for i, v, p, s in parts]
            write_midi(td / "x.mid", tempo, parts3, length * 3)
        else:
            write_midi(td / "x.mid", tempo, parts, length)
        write_midi(MID / f"{name}.mid", tempo, parts, length)
        subprocess.run(["fluidsynth", "-ni", "-g", "0.6", "-r", str(RATE), "-R", "1", "-C", "0",
                        "-o", "synth.reverb.room-size=0.75", "-o", "synth.reverb.width=1.0",
                        "-o", "synth.reverb.level=0.6", "-o", "synth.reverb.damp=0.35",
                        "-F", str(td / "x.wav"), str(SF2), str(td / "x.mid")], check=True, capture_output=True)
        if loop:
            cut = ["-ss", f"{sec:.4f}", "-t", f"{sec + XF:.4f}"]
            af = ""
        else:
            cut = []
            af = "areverse,silenceremove=start_periods=1:start_threshold=-60dB,areverse,"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *cut, "-i", str(td / "x.wav"),
                        "-af", af + "anull", str(td / "y.wav")], check=True)
        lufs = loudness(td / "y.wav")
        g = -18 - lufs + gain_db
        out = OUT / f"{name}.mp3"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(td / "y.wav"),
                        "-af", f"volume={g:.2f}dB,alimiter=limit=0.89", "-ac", "2", "-ar", "32000",
                        "-b:a", "80k", str(out)], check=True)
    print(f"{name}: {sec:.1f}s ({lufs:.1f} LUFS → {-18 + gain_db:.0f})", out.stat().st_size // 1024, "KB")


def loudness(wav):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(wav), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])


# ---------- 曲 ----------
def theme3():
    a, la = parse(THEME_A)
    b, lb = parse(THEME_B)
    return a, la, b, lb


def song_title():
    """タイトル：オルゴールと弦のワルツ。A（オルゴール）B（バイオリン）A（チェンバロ+チェレスタ）B' A"""
    a, la, b, lb = theme3()
    ca, cb = bars_to_chords(CH_A, 3), bars_to_chords(CH_B, 3)
    intro = bars_to_chords(["Dm", "Dm", "Bb", "A7"], 3)
    form = [("i", intro, 12), ("a", ca, la), ("b", cb, lb), ("a", ca, la), ("b", cb, lb), ("a", ca, la)]
    mel_box, mel_vln, mel_hpd, bass, chord, pad = [], [], [], [], [], []
    t = 0.0
    for k, (sec, ch, ln) in enumerate(form):
        bs, cd = acc_waltz(ch)
        bass += [(s + t, n, d) for s, n, d in bs]
        chord += [(s + t, n, d) for s, n, d in cd]
        if k >= 2:
            pad += [(s + t, n, d) for s, n, d in acc_pad(ch, 50, 3)]
        mel = a if sec == "a" else b if sec == "b" else []
        tgt = {1: mel_box, 2: mel_vln, 3: mel_hpd, 4: mel_vln, 5: mel_box}.get(k)
        if tgt is not None:
            tgt += [(s + t, n, d) for s, n, d in mel]
            if k == 3:
                mel_box += [(s + t, [x + 12 for x in n], d) for s, n, d in mel]
        t += ln
    return 100, [("musicbox", 92, 64, mel_box), ("violin", 86, 70, mel_vln), ("harpsichord", 80, 54, mel_hpd),
                 ("pizz", 82, 48, bass), ("harpsichord", 58, 80, chord), ("slowstr", 52, 64, pad)], t


def song_story():
    """おはなし：オルゴールとチェロだけで主題を静かに"""
    a, la, b, lb = theme3()
    mel = cat((a, la), (b, lb), (shift(a, -12), la), (b, lb))
    names = CH_A + CH_B + CH_A + CH_B
    allch = bars_to_chords(names, 3)
    cello = [(t, [voice([chord_pcs(n)[0]], 38, 49)[0]], d) for t, d, n in allch]
    arp = acc_arp(allch, step=1, center=62, pattern=(0, 1, 2))
    box = [x for x in mel if x[0] < la + lb or x[0] >= 2 * la + lb]
    cel = [x for x in mel if la + lb <= x[0] < 2 * la + lb]
    return 76, [("musicbox", 88, 60, box), ("cello", 84, 70, cello), ("cello", 70, 40, [(s, [n[0] + 12], d) for s, n, d in cel]),
                ("harp", 50, 84, arp), ("slowstr", 34, 64, acc_pad(allch, 55, 3))], 2 * (la + lb)


def song_prep():
    """今夜の支度：チェンバロのメヌエット。時計の刻みを伴奏に"""
    a, la, b, lb = theme3()
    names = CH_A + CH_B
    allch = bars_to_chords(names, 3)
    mel = cat((a, la), (b, lb))
    hpd_r = acc_arp(allch, step=.5, center=55, pattern=(0, 2, 1, 2, 0, 2))
    bass = acc_bass(allch, low=38, step=1)
    flute = [(s + la + lb, [n[0] + 12 if n else 0], d) for s, n, d in mel if n]
    hpd_mel = mel + [(s + la + lb, n, d) for s, n, d in mel]
    tick = drums([0, 1, 2], 32, 3, 76) + drums([0], 32, 3, 77)
    L = 2 * (la + lb)
    return 112, [("harpsichord", 86, 52, hpd_mel), ("harpsichord", 66, 78, cat((hpd_r, la + lb), (hpd_r, la + lb))),
                 ("bassoon", 70, 40, cat((bass, la + lb), (bass, la + lb))), ("flute", 70, 72, flute),
                 ("drum", 34, 64, tick)], L


NIGHT_MEL = """D4:.5 r:.5 F4:.5 E4:.5 D4:.5 r:.5 A3:1 | Bb3:.5 A3:.5 G3:.5 A3:.5 r:2 |
               D4:.5 r:.5 F4:.5 G4:.5 A4:.5 r:.5 Bb4:.5 A4:.5 | G#4:1.5 E4:.5 A4:2 |
               F4:.5 r:.5 A4:.5 G4:.5 F4:.5 r:.5 D4:1 | E4:.5 F4:.5 G4:.5 E4:.5 C#4:2 |
               D4:.5 E4:.5 F4:.5 G4:.5 A4:.5 Bb4:.5 C#5:.5 D5:.5 | A4:1 r:.5 C#4:.5 D4:2"""
NIGHT_CH = ["Dm", "Gm A7", "Dm Gm", "E7 A7", "Dm", "Gm A7", "Gm A7", "Dm"]


def song_night():
    """夜の守り：ピチカートの忍び足とファゴット、チェンバロ。後半で館の主題（4拍子）"""
    m, lm = parse(NIGHT_MEL)
    ch = bars_to_chords(NIGHT_CH, 4)
    a, la, b, lb = theme3()
    a4, b4 = waltz_to_four(a), waltz_to_four(b)
    ca, cb = bars_to_chords(CH_A, 4, stretch=True), bars_to_chords(CH_B, 4, stretch=True)
    L = lm * 2 + 64
    pizz = cat((acc_ostinato(ch), lm), (acc_ostinato(ch), lm), (acc_ostinato(ca), 32), (acc_ostinato(cb), 32))
    bsn = cat((m, lm), ([], lm), (shift(a4, -12), 32), ([], 32))
    clar = cat(([], lm), (m, lm), ([], 32), (shift(b4, -12), 32))
    hpd = cat(([], lm), (shift(m, 12), lm), (acc_arp(ca, step=.5, center=60), 32), (acc_arp(cb, step=.5, center=60), 32))
    pad = cat((acc_pad(ch, 52, 3, open5=True), lm), (acc_pad(ch, 52, 3, open5=True), lm),
              (acc_pad(ca, 55, 3, open5=True), 32), (acc_pad(cb, 55, 3, open5=True), 32))
    tick = drums([1, 3], L // 4, 4, 76)
    return 132, [("pizz", 96, 56, pizz), ("bassoon", 92, 44, bsn), ("harpsichord", 74, 80, hpd),
                 ("clarinet", 76, 70, clar), ("strings", 44, 64, pad), ("drum", 30, 64, tick)], L


def song_phase3():
    """夜の終盤：night の旋律を速く、弦の刻みとティンパニ。後半で館の主題"""
    m, lm = parse(NIGHT_MEL)
    ch = bars_to_chords(NIGHT_CH, 4)
    a, la, b, lb = theme3()
    a4, b4 = waltz_to_four(a), waltz_to_four(b)
    ca, cb = bars_to_chords(CH_A, 4, stretch=True), bars_to_chords(CH_B, 4, stretch=True)
    L = lm * 2 + 64
    secs = [ch, ch, ca, cb]
    lens = [lm, lm, 32, 32]
    trem = cat(*[(acc_bass(c, low=45, step=.25), n) for c, n in zip(secs, lens)])
    vln = cat((shift(m, 12), lm), (shift(m, 12), lm), (a4, 32), (b4, 32))
    hpd = cat(*[(acc_arp(c, step=.25, center=64), n) for c, n in zip(secs, lens)])
    timp = [(t, n, .4) for t, n, d in cat(*[(acc_bass(c, low=38, step=1 if i < 2 else 2), n) for i, (c, n) in enumerate(zip(secs, lens))])]
    brass = cat(([], lm), (acc_pad(ch, 50, 3, open5=True), lm), (acc_pad(ca, 50, 3, open5=True), 32), (acc_pad(cb, 50, 3, open5=True), 32))
    return 152, [("strings", 72, 60, trem), ("violin", 92, 70, vln), ("harpsichord", 66, 84, hpd),
                 ("timpani", 90, 50, timp), ("tremolo", 60, 40, brass), ("drum", 40, 64, drums([0, 2], L // 4, 4, 77))], L


def song_library():
    """書庫・礼拝堂：オルガンと弦のゆっくりした短調。チェレスタが主題をなぞる"""
    a, la, b, lb = theme3()
    a4, b4 = waltz_to_four(a), waltz_to_four(b)
    ca, cb = bars_to_chords(CH_A, 4, stretch=True), bars_to_chords(CH_B, 4, stretch=True)
    L = 32 * 3
    organ = cat((acc_pad(ca, 55, 4), 32), (acc_pad(cb, 55, 4), 32), (acc_pad(ca, 55, 4), 32))
    bass = cat((acc_bass(ca, 26), 32), (acc_bass(cb, 26), 32), (acc_bass(ca, 26), 32))
    cel = cat((a4, 32), ([], 32), (shift(a4, 12), 32))
    cello = cat(([], 32), (shift(b4, -12), 32), ([], 32))
    harp = cat(([], 32), (acc_arp(cb, step=1, center=64, pattern=(0, 1, 2, 1)), 32), (acc_arp(ca, step=1, center=64), 32))
    return 72, [("reed", 58, 64, organ), ("contrabass", 72, 50, bass), ("celesta", 92, 76, cel),
                ("cello", 86, 46, cello), ("harp", 56, 84, harp), ("choir", 36, 64, cat(([], 64), (acc_pad(ca, 60, 3, open5=True), 32)))], L


def song_lastnight():
    """大時計の間：パイプオルガンと合唱、主題を重く"""
    a, la, b, lb = theme3()
    a4, b4 = waltz_to_four(a), waltz_to_four(b)
    ca, cb = bars_to_chords(CH_A, 4, stretch=True), bars_to_chords(CH_B, 4, stretch=True)
    L = 96
    organ_mel = cat((shift(a4, -12), 32), (shift(b4, -12), 32), (a4, 32))
    organ_ch = cat((acc_pad(ca, 52, 3), 32), (acc_pad(cb, 52, 3), 32), (acc_pad(ca, 55, 4), 32))
    ped = cat((acc_bass(ca, 26, step=2), 32), (acc_bass(cb, 26, step=2), 32), (acc_bass(ca, 26, step=1), 32))
    choir = cat((acc_pad(ca, 62, 3, open5=True), 32), (acc_pad(cb, 62, 3, open5=True), 32), (acc_pad(ca, 64, 3, open5=True), 32))
    strings = cat((acc_bass(ca, 50, step=.5), 32), (acc_bass(cb, 50, step=.5), 32), (acc_bass(ca, 50, step=.25), 32))
    timp = [(t, n, .3) for t, n, d in cat((acc_bass(ca, 38, step=4), 32), (acc_bass(cb, 38, step=2), 32), (acc_bass(ca, 38, step=1), 32))]
    bells = [(t, [74], 2) for t in (0, 16, 32, 48, 64, 80)]
    return 92, [("organ", 84, 64, organ_mel + organ_ch), ("contrabass", 84, 56, ped), ("choir", 66, 70, choir),
                ("strings", 66, 46, strings), ("timpani", 92, 54, timp), ("bells", 66, 80, bells)], L


BARON_MEL = """G4:1 r:.5 D4:.5 G4:.5 A4:.5 Bb4:1 | A4:.5 G4:.5 F#4:.5 G4:.5 D4:2 |
               Eb4:1 r:.5 C4:.5 Eb4:.5 F4:.5 G4:1 | F#4:.5 G4:.5 A4:.5 F#4:.5 D4:2 |
               G4:1 r:.5 D4:.5 G4:.5 A4:.5 Bb4:1 | C5:.5 Bb4:.5 A4:.5 Bb4:.5 G4:1 Eb4:1 |
               D4:.5 F#4:.5 A4:.5 C5:.5 Bb4:.5 A4:.5 G4:.5 F#4:.5 | G4:1 D4:1 G3:2"""
BARON_CH = ["Gm", "D7", "Cm", "D7", "Gm", "Cm Eb", "D7", "Gm"]


def song_baron():
    """ガメツ男爵：ファゴットとチューバのどっしり短調マーチ。中間はハ短調でオーボエ"""
    m, lm = parse(BARON_MEL)
    ch = bars_to_chords(BARON_CH, 4)
    ch2 = bars_to_chords(["Cm", "G7", "Fm", "G7", "Cm", "Fm Ab", "G7", "Cm"], 4)
    bs, cd = oompah(ch, low=31, center=55)
    bs2, cd2 = oompah(ch2, low=31, center=55)
    L = lm * 3
    bsn = cat((m, lm), (shift(m, 5), lm), (m, lm))
    oboe = cat(([], lm), (shift(m, 17), lm), (shift(m, 12), lm))
    tuba = cat((bs, lm), (bs2, lm), (bs, lm))
    pz = cat((cd, lm), (cd2, lm), (cd, lm))
    snare = drums([0, 1, 2, 3], L // 4, 4, 38) + drums([0], L // 4, 4, 36)
    return 116, [("bassoon", 100, 50, bsn), ("oboe", 76, 76, oboe), ("tuba", 96, 40, tuba),
                 ("pizz", 70, 84, pz), ("drum", 40, 64, snare), ("timpani", 70, 60, [(t, n, .3) for t, n, d in tuba if int(t) % 4 == 0])], L


def song_shop():
    """育成・お店：チェンバロとフルートの軽い長調。主題の明るい版を3回（フルート → チェンバロ → フルート+グロッケン）"""
    a, la, b, lb = theme3()
    am, bm = to_major(a), to_major(b)
    ca = bars_to_chords(CH_A_MAJ, 3)
    cb = bars_to_chords(CH_B_MAJ, 3)
    allch = ca + [(t + la, d, n) for t, d, n in cb]
    n = la + lb
    mel = cat((am, la), (bm, lb))
    L = n * 3
    flute = cat((mel, n), ([], n), (mel, n))
    hpd_mel = cat(([], n), (mel, n), ([], n))
    glock = cat(([], n), ([], n), (shift(mel, 12), n))
    hpd = cat(*[(acc_arp(allch, step=.5, center=60 if i != 1 else 55, pattern=(0, 1, 2, 1, 2, 1)), n) for i in range(3)])
    bass = cat(*[(acc_bass(allch, 38, step=1), n) for _ in range(3)])
    return 120, [("flute", 88, 70, flute), ("harpsichord", 86, 60, hpd_mel), ("glock", 54, 84, glock),
                 ("harpsichord", 66, 48, hpd), ("pizz", 78, 44, bass), ("drum", 28, 64, drums([0], L // 3, 3, 76))], L


def song_ending():
    """結び：主題を長調で、弦とオルゴール、ハープ"""
    a, la, b, lb = theme3()
    am = to_major(a)
    bm = to_major(b)
    ca = bars_to_chords(CH_A_MAJ, 3)
    cb = bars_to_chords(CH_B_MAJ, 3)
    allch = ca + [(t + la, d, n) for t, d, n in cb]
    L = 2 * (la + lb)
    box = cat((am, la), (bm, lb), ([], la + lb))
    vln = cat(([], la + lb), (am, la), (bm, lb))
    harp = cat((acc_arp(allch, step=1, center=60, pattern=(0, 1, 2)), la + lb), (acc_arp(allch, step=.5, center=62, pattern=(0, 1, 2, 1, 2, 1)), la + lb))
    pad = cat((acc_pad(allch, 52, 3), la + lb), (acc_pad(allch, 55, 4), la + lb))
    bass = cat((acc_bass(allch, 38), la + lb), (acc_bass(allch, 38), la + lb))
    return 84, [("musicbox", 90, 60, box), ("violin", 88, 70, vln), ("harp", 66, 84, harp),
                ("slowstr", 54, 50, pad), ("cello", 70, 44, bass)], L


def jingle_dawn():
    mel, lm = parse("A4:.5 D5:.5 F#5:.5 A5:1.5 G5:.5 F#5:.5 E5:.5 D5:3")
    bells = [(0, [62], 1.8), (4, [74], 4)]
    pad = [(0, [50, 57, 62, 66], 2), (2, [45, 55, 61, 64], 2), (4, [38, 50, 57, 62, 66], 4)]
    return 96, [("musicbox", 96, 60, mel), ("bells", 80, 80, bells), ("strings", 66, 50, pad),
                ("harp", 60, 70, acc_arp([(4, 4, "D")], step=.25, center=62, pattern=(0, 1, 2)))], 8


def jingle_over():
    mel, lm = parse("A4:1 G4:.5 F4:.5 E4:1 D4:1 C#4:1.5 D4:3")
    bells = [(0, [50], 2.8), (5, [38], 4)]
    pad = [(0, [50, 53, 57], 2), (2, [46, 50, 53], 1), (3, [45, 49, 52], 2), (5, [38, 45, 50, 53], 4)]
    return 72, [("celesta", 90, 60, mel), ("bells", 76, 80, bells), ("cello", 76, 50, pad),
                ("organ", 40, 64, [(5, [26, 38], 4)])], 9


SONGS = {
    "bgm_title": (song_title, True, 0), "bgm_story": (song_story, True, -1), "bgm_prep": (song_prep, True, 0),
    "bgm_night": (song_night, True, 0), "bgm_phase3": (song_phase3, True, 0), "bgm_library": (song_library, True, -1),
    "bgm_lastnight": (song_lastnight, True, 0), "bgm_baron": (song_baron, True, 0), "bgm_shop": (song_shop, True, 0),
    "bgm_ending": (song_ending, True, 0), "jingle_dawn": (jingle_dawn, False, 0), "jingle_over": (jingle_over, False, 0),
}


def main():
    want = sys.argv[1:] or list(SONGS)
    for name in want:
        fn, loop, gain = SONGS[name]
        tempo, parts, length = fn()
        render(name, tempo, parts, length, loop, gain)


if __name__ == "__main__":
    main()
