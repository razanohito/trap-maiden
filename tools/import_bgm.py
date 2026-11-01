"""BGM の元の曲（art-src/bgm/）を、ゲームに埋め込む形にそろえて art/bgm/ に入れる。

- 元の曲は yuruge/trap-of-lily の asseets/audio から選んで、ゲームでの名前に付け替えたもの（2026-11-01）
    bgm_title   … おやすみ、夜明けの館（タイトル・結び・お店）
    bgm_story   … はじめての夜（おはなし）
    bgm_room0〜7 … 部屋ごとの曲（インディー2D風）。番号は MAPS の順（大広間・東の書庫・回廊・温室・地下牢・礼拝堂・屋根裏・大時計の間）
    jingle_dawn … 今夜はここまで（2つ目）。夜明け
    jingle_over … 今夜はここまで。つかまったとき
- 頭と終わりの無音を切り、音量を -18 LUFS にそろえる（曲ごとの大小をなくす）
- ジングルの終わりは 0.6 秒で消す（ぶつ切りで終わる曲があるため）
- ステレオ 64kbps・32kHz の mp3（ビルドで data URI に埋め込むので、全曲で HTML が 16MB を超えない重さにする）

使い方: python tools/import_bgm.py のあと python tools/build.py（ffmpeg が必要）
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "art-src" / "bgm"
OUT = ROOT / "art" / "bgm"
TRIM = "silenceremove=start_periods=1:start_threshold=-50dB,areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse"


def duration(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    return float(r.stdout)


def loudness(p, af):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(p), "-af", af + ",ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for p in sorted(SRC.glob("*.mp3")):
        af = TRIM
        if p.name.startswith("jingle_"):
            af += f",afade=t=out:st={duration(p) - 1.2:.2f}:d=0.6"
        g = -18 - loudness(p, af)
        out = OUT / p.name
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(p),
                        "-af", f"{af},volume={g:.2f}dB,alimiter=limit=0.89", "-ac", "2", "-ar", "32000",
                        "-b:a", "64k", str(out)], check=True)
        print(p.name, f"{p.stat().st_size // 1024}KB →", f"{out.stat().st_size // 1024}KB", f"{duration(out):.1f}s")


if __name__ == "__main__":
    main()
