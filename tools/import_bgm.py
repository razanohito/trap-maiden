"""Gemini に作ってもらった BGM を、ゲーム用にそろえて art/bgm/ に入れる。

- 入力: art-src/bgm/bgm_*.mp3・jingle_*.mp3
- 音量を -18 LUFS にそろえ（曲ごとの大小をなくす）、モノラル 64kbps の mp3 にして軽くする
- ジングルは最後の無音を切る
- 出力: art/bgm/<同じ名前>.mp3（ビルドで data URI に埋め込む）

使い方: python tools/import_bgm.py（ffmpeg が必要）
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "art-src" / "bgm"
OUT = ROOT / "art" / "bgm"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for p in sorted(SRC.glob("*.mp3")):
        af = "loudnorm=I=-18:TP=-1.5:LRA=11"
        if p.name.startswith("jingle_"):  # 最後の無音を切る（前後を反転して先頭の無音を取る）
            af = "areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse," + af
        out = OUT / p.name
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(p), "-af", af,
                        "-ac", "1", "-ar", "44100", "-b:a", "64k", str(out)], check=True)
        print(p.name, f"{p.stat().st_size // 1024}KB →", f"{out.stat().st_size // 1024}KB")


if __name__ == "__main__":
    main()
