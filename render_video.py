"""Render and verify the Saint Francis of Assisi devotional short."""

import argparse
from array import array
from fractions import Fraction
import json
from math import exp, sin, tau
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import wave

from illustrations import HEIGHT, WIDTH, illustration

FPS = 30
DURATION = 30
DISSOLVE = Fraction(4, 5)
SAMPLE_RATE = 48_000
DEFAULT_OUTPUT = Path("Saint_Francis_Test.mp4")

# Artwork starts at four-second intervals. Captions change at the midpoint
# of each dissolve, with enough time to read both languages together.
CUES = (
    (0, 440, "Saint Francis of Assisi", "அசிசியின் புனித பிரான்சிஸ்"),
    (440, 840, "He chose a life of simplicity.", "அவர் எளிமையான வாழ்வைத் தேர்ந்தெடுத்தார்."),
    (840, 1240, "He prayed in the little chapel.", "சிறிய ஆலயத்தில் அவர் செபித்தார்."),
    (1240, 1640, "He greeted the birds with joy.", "பறவைகளை மகிழ்ச்சியுடன் வாழ்த்தினார்."),
    (1640, 2040, "He praised God for all creation.", "படைப்புகள் அனைத்திற்காகவும் இறைவனைப் போற்றினார்."),
    (2040, 2500, "May we be instruments of peace.", "நாம் அமைதியின் கருவிகளாக இருப்போமாக."),
    (2500, 3000, "Like, Hype, Share and Subscribe", "விரும்புங்கள், உற்சாகப்படுத்துங்கள், பகிருங்கள், குழுசேருங்கள்"),
)


def ass_time(centiseconds: int) -> str:
    minutes, remainder = divmod(centiseconds, 6000)
    seconds, fraction = divmod(remainder, 100)
    return f"0:{minutes:02}:{seconds:02}.{fraction:02}"


def write_captions(path: Path) -> None:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: English,DejaVu Serif,38,&H00F7F5F0,&H00FFFFFF,&H20302521,&H00000000,0,0,0,0,100,100,0,0,1,2,1,2,48,48,78,1
Style: Tamil,Noto Sans Tamil,32,&H00C2E6FF,&H00FFFFFF,&H20302521,&H00000000,0,0,0,0,100,100,0,0,1,2,1,2,48,48,32,1
Style: Title,DejaVu Serif,62,&H00F7F5F0,&H00FFFFFF,&H20302521,&H00000000,0,0,0,0,100,100,0,0,1,2,1,8,48,48,78,1
Style: TitleTamil,Noto Sans Tamil,38,&H00C2E6FF,&H00FFFFFF,&H20302521,&H00000000,0,0,0,0,100,100,0,0,1,2,1,8,48,48,158,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    events = []
    for start, end, english, tamil in CUES:
        opening = start == 0
        ending = end == 3000
        fade = r"{\fad(150,150)}" if not (opening or ending) else ""
        for style, caption in (
            ("Title" if opening else "English", english),
            ("TitleTamil" if opening else "Tamil", tamil),
        ):
            events.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},{style},,0,0,0,,{fade}{caption}")
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def write_score(path: Path) -> None:
    """Synthesize a quiet stereo score with a plucked, bell-like timbre."""
    chords = ((48, 55, 60, 64, 67), (45, 52, 60, 64, 69),
              (41, 53, 57, 60, 65), (43, 55, 59, 62, 67),
              (45, 52, 57, 60, 64), (41, 53, 60, 65, 69),
              (43, 55, 62, 67, 71), (48, 55, 60, 64, 72))
    sample_count = DURATION * SAMPLE_RATE
    left = array("f", [0]) * sample_count
    right = array("f", [0]) * sample_count
    for measure, chord in enumerate(chords):
        notes = zip((0, .63, 1.26, 1.9, 2.53, 3.18), (0, 2, 3, 1, 4, 2))
        for beat, (offset, note) in enumerate(notes):
            start = round((measure * 3.6 + offset) * SAMPLE_RATE)
            if start >= sample_count:
                break
            pitch = tau * 440 * 2 ** ((chord[note] - 69) / 12)
            pan = .35 + .30 * (beat % 2)
            echo = round(.17 * SAMPLE_RATE)
            for i in range(min(2 * SAMPLE_RATE, sample_count - start)):
                t = i / SAMPLE_RATE
                envelope = min(1, t / .026) * exp(-2.6 * t) * min(1, (2 - t) / .16)
                tone = sin(pitch * t) + .22 * exp(-1.6 * t) * sin(2 * pitch * t)
                value = .125 * envelope * tone
                left[start + i] += value * (1 - pan)
                right[start + i] += value * pan
                if start + i + echo < sample_count:
                    right[start + i + echo] += .16 * value
    pcm = array("h")
    for i, (l_sample, r_sample) in enumerate(zip(left, right)):
        t = i / SAMPLE_RATE
        fade = max(0, min(1, t / .65, (DURATION - t) / 1.9))
        pcm.extend(round(32767 * fade * max(-1, min(1, sample)))
                   for sample in (l_sample, r_sample))
    if sys.byteorder == "big":
        pcm.byteswap()
    with wave.open(str(path), "wb") as output:
        output.setparams((2, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
        output.writeframes(pcm.tobytes())


def validate(path: Path) -> None:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format",
         "-of", "json", str(path.resolve())],
        check=True, capture_output=True, text=True,
    )
    report = json.loads(result.stdout)
    streams = report["streams"]
    by_type = {stream["codec_type"]: stream for stream in streams}
    if len(streams) != 2 or set(by_type) != {"video", "audio"}:
        raise ValueError("Expected exactly one video stream and one audio stream.")
    video, audio = by_type["video"], by_type["audio"]
    checks = {
        "MP4 container": "mp4" in report["format"]["format_name"].split(","),
        "30-second container duration": Fraction(report["format"]["duration"]) == DURATION,
        "30-second video duration": Fraction(video["duration"]) == DURATION,
        "30-second audio duration": Fraction(audio["duration"]) == DURATION,
        "1280×720 square-pixel 16:9 video": (video["width"], video["height"]) == (WIDTH, HEIGHT)
        and video.get("sample_aspect_ratio") == "1:1",
        "30 fps video": all(Fraction(video[key]) == FPS for key in ("avg_frame_rate", "r_frame_rate")),
        "900 decoded frames": int(video["nb_read_frames"]) == DURATION * FPS,
        "H.264 video": video["codec_name"] == "h264",
        "AAC audio": audio["codec_name"] == "aac",
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("FFprobe validation failed: " + ", ".join(failed))
    print(f"Verified {path.name} | 30.000 s | 1280×720 | 30 fps | H.264 + AAC", flush=True)


def render(path: Path) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep the final replacement atomic, including when rendering over an old file.
    with TemporaryDirectory(prefix=".saint-francis-", dir=path.parent) as directory:
        work = Path(directory)
        inputs = []
        filters = []
        for index in range(6):
            plate = f"plate-{index}.png"
            illustration(index).save(work / plate)
            length = float(4 + DISSOLVE) if index < 5 else DURATION - 20
            inputs.extend(["-loop", "1", "-framerate", str(FPS), "-t", str(length), "-i", plate])
            filters.append(f"[{index}:v]setsar=1,format=yuv444p[plate{index}]")
        previous = "plate0"
        for index in range(1, 6):
            output = f"mix{index}"
            filters.append(
                f"[{previous}][plate{index}]xfade=transition=fade:"
                f"duration={float(DISSOLVE)}:offset={4 * index}[{output}]"
            )
            previous = output
        write_captions(work / "captions.ass")
        write_score(work / "score.wav")
        filters.append(f"[{previous}]ass=captions.ass:shaping=complex,format=yuv420p[video]")
        temporary_video = work / "render.mp4"
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "warning", "-nostdin",
             "-filter_complex_threads", "1", *inputs, "-i", "score.wav",
             "-filter_complex", ";".join(filters), "-map", "[video]", "-map", "6:a",
             "-t", str(DURATION), "-c:v", "libx264", "-preset", "fast", "-crf", "19",
             "-threads", "4", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
             temporary_video.name],
            cwd=work, check=True,
        )
        validate(temporary_video)
        temporary_video.replace(path)
    print(f"Rendered {path}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="output MP4 path")
    parser.add_argument("--verify-only", action="store_true", help="validate an existing MP4")
    args = parser.parse_args()
    required = ("ffprobe",) if args.verify_only else ("ffmpeg", "ffprobe")
    for executable in required:
        if shutil.which(executable) is None:
            parser.error(f"{executable} is required and was not found on PATH")
    try:
        if args.verify_only:
            validate(args.output)
        else:
            render(args.output)
    except (OSError, subprocess.CalledProcessError, ValueError, KeyError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
