"""Render the Saint Francis documentary and independently verify its MP4."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image, ImageDraw, ImageFont, features

from .art import H, W, draw_plate
from .score import RATE, write_score

FPS = 30
SHOT_SECONDS = 10
SHOTS = 60
TOTAL = SHOT_SECONDS * SHOTS
DISSOLVE = 1
ENDING = TOTAL - 5
OUT = Path("Saint_Francis_10_Minute.mp4")
STORY = Path(__file__).with_name("story.psv")
TITLE = ("Saint Francis of Assisi", "அசிசியின் புனித பிரான்சிஸ்")
PROMO = ("Like, Hype, Share and Subscribe",
         "விரும்புங்கள், உற்சாகப்படுத்துங்கள், பகிருங்கள், குழுசேருங்கள்")
FONTS = ("DejaVu Serif", "Noto Sans Tamil")
TEXT_COLORS = ("#fff4df", "#ffe3ae")


@dataclass(frozen=True)
class Shot:
    setting: str
    palette: str
    elements: tuple
    captions: tuple[str, str]


@dataclass(frozen=True)
class Cue:
    start: int
    end: int
    captions: tuple[str, str]


def load_story() -> list[Shot]:
    shots = []
    for row in STORY.read_text(encoding="utf-8").splitlines():
        setting, palette, composition, en, ta = row.split("|")
        elements = []
        for spec in composition.split(";"):
            name, coordinates = spec.split("@")
            x, y, scale = map(float, coordinates.split(","))
            if not 0 < x < W or not 0 < y < H or scale <= 0:
                raise ValueError(f"Invalid position or size for {spec}")
            elements.append((name, x, y, scale))
        if not en.strip() or not re.search(r"[\u0B80-\u0BFF]", ta):
            raise ValueError(f"Missing bilingual caption in shot {len(shots) + 1}")
        shots.append(Shot(setting, palette, tuple(elements), (en, ta)))
    if len(shots) != SHOTS or len({shot.elements for shot in shots}) != SHOTS:
        raise ValueError(f"Expected {SHOTS} individually composed shots")
    if len({shot.captions for shot in shots}) != SHOTS:
        raise ValueError(f"Expected {SHOTS} distinct bilingual story captions")
    return shots


def cues(shots: list[Shot]) -> list[Cue]:
    return [
        Cue(index*SHOT_SECONDS, min((index+1)*SHOT_SECONDS,ENDING), shot.captions)
        for index, shot in enumerate(shots)
    ] + [Cue(ENDING,TOTAL,PROMO)]


def srt_time(time: int) -> str:
    minutes, seconds = divmod(time,60)
    return f"00:{minutes:02}:{seconds:02},000"


def srt_text(timeline: list[Cue], language: int) -> str:
    return "\n".join(
        f"{index}\n{srt_time(cue.start)} --> {srt_time(cue.end)}\n{cue.captions[language]}\n"
        for index, cue in enumerate(timeline,1)
    )


@lru_cache
def font(language: int, size: int) -> ImageFont.FreeTypeFont:
    if not features.check_feature("raqm"):
        raise ValueError("Pillow with RAQM is required for correct Tamil shaping")
    match = subprocess.check_output(
        ["fc-match","--format=%{family}\n%{file}",FONTS[language]],text=True,
    ).splitlines()
    if len(match) != 2 or FONTS[language] not in match[0].split(","):
        raise ValueError(f"Install the {FONTS[language]} font to render captions")
    return ImageFont.truetype(match[1],size,layout_engine=ImageFont.Layout.RAQM)


def caption_overlay(captions: tuple[str,str], *, title=False) -> Image.Image:
    # Keep the two languages visually distinct and the main artwork above 562 px.
    height = 178 if title else 144
    image = Image.new("RGBA",(W,height))
    draw = ImageDraw.Draw(image)
    if title:
        draw.rounded_rectangle((204,14,W-204,166),radius=18,fill=(26,26,42,226))
        draw.line((424,145,856,145),fill="#d3a777",width=2)
    else:
        draw.rectangle((0,0,W,height),fill=(22,23,36,243))
        draw.line((0,0,W,0),fill="#cfa77b",width=2)
    for language, text in enumerate(captions):
        top = ((28,100) if title else (15,77))[language]
        face = font(language,((61,35) if title else (29,26))[language])
        max_width = 832 if title else 1120
        lines = [""]
        for word in text.split():
            candidate = " ".join(part for part in (lines[-1],word) if part)
            if face.getlength(candidate) <= max_width:
                lines[-1] = candidate
            else:
                lines.append(word)
        if len(lines) > (1 if title else 2) or any(
            not line or face.getlength(line) > max_width for line in lines
        ):
            raise ValueError(f"Caption exceeds its safe area: {text}")
        step = 30 if language == 0 else 32
        for row,line in enumerate(lines):
            draw.text((W//2,top+step*row),line,font=face,anchor="mt",fill=TEXT_COLORS[language])
    return image


def media(*args: str, cwd=None, capture=False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["ffmpeg","-hide_banner","-loglevel","error","-nostdin",*args],
        cwd=cwd,check=True,capture_output=capture,
    )


def clip(work: Path, index: int) -> None:
    inputs = []
    graph = []
    if index:
        inputs += ["-loop","1","-framerate",str(FPS),"-t",str(DISSOLVE),"-i",f"art-{index-1:02}.png"]
        graph += ["[0:v]setsar=1,format=yuv444p[old]"]
    art_input = int(index > 0)
    inputs += ["-loop","1","-framerate",str(FPS),"-t",str(SHOT_SECONDS),"-i",f"art-{index:02}.png"]
    graph += [f"[{art_input}:v]setsar=1,format=yuv444p[art]"]
    current = "art"
    if index:
        graph += [f"[old][art]xfade=transition=fade:duration={DISSOLVE}:offset=0[dissolved]"]
        current = "dissolved"
    inputs += ["-i",f"caption-{index:02}.png"]
    enabled = ":enable='lt(t,5)'" if index == SHOTS-1 else ""
    graph += [f"[{current}][{art_input+1}:v]overlay=0:H-h{enabled}[captioned]"]
    current = "captioned"
    if index == 0 or index == SHOTS-1:
        name, y, timing = ("title",65,"lt(t,6)") if index == 0 else ("promo","H-h","gte(t,5)")
        inputs += ["-i",f"{name}.png"]
        graph += [f"[{current}][{art_input+2}:v]overlay=0:{y}:enable='{timing}'[complete]"]
        current = "complete"
    media(
        "-filter_complex_threads","1",*inputs,"-filter_complex",";".join(graph),
        "-map",f"[{current}]","-t",str(SHOT_SECONDS),"-an","-c:v","libx264",
        "-preset","ultrafast","-crf","20","-threads","1","-pix_fmt","yuv420p",
        "-video_track_timescale","90000",f"clip-{index:02}.mp4",cwd=work,
    )


def require(condition, description):
    if not condition:
        raise ValueError(f"Verification failed: {description}")


def probe(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe","-v","error","-count_frames","-show_streams","-show_format",
         "-of","json",str(path)],capture_output=True,check=True,text=True,
    )
    require(not result.stderr,"FFprobe reported decode errors")
    return json.loads(result.stdout)


def check_captions(path: Path, timeline: list[Cue], workers: int) -> None:
    for language in range(2):
        extracted = media(
            "-i",str(path),"-map",f"0:s:{language}","-f","srt","-",capture=True,
        ).stdout.decode("utf-8").replace("\r\n","\n").strip()
        require(extracted == srt_text(timeline,language).strip(),
                f"{FONTS[language]} subtitle text or cue timings")
    # Sample every bilingual cue. Verify bright pixels at the actual shaped
    # glyph positions, including text on the first frame of the promotion.
    samples = [(cue.start+2,cue.captions,False) for cue in timeline[:-1]]
    samples += [(ENDING,PROMO,False),(TOTAL-1,PROMO,False),(2,TITLE,True)]

    def check_sample(sample):
        time, captions, title = sample
        expected = np.asarray(caption_overlay(captions,title=title))
        top = 65 if title else H-expected.shape[0]
        raw = media(
            "-ss",str(time),"-i",str(path),"-map","0:v:0","-frames:v","1",
            "-vf",f"crop={W}:{expected.shape[0]}:0:{top}","-pix_fmt","rgb24",
            "-threads","1","-f","rawvideo","-",capture=True,
        ).stdout
        require(len(raw)==expected.shape[0]*W*3,f"missing video frame at {time}s")
        actual = np.frombuffer(raw,dtype=np.uint8).reshape(expected.shape[0],W,3)
        for start,end in (((22,98),(99,143)) if title else ((13,74),(76,143))):
            glyph = (expected[start:end,:,0] > 245) & (expected[start:end,:,1] > 203)
            require(np.count_nonzero(glyph)>100,f"empty reference caption at {time}s")
            fraction = np.mean(actual[start:end,:,0][glyph]>170)
            require(fraction>.9,f"burned caption is missing or unreadable at {time}s")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for _ in pool.map(check_sample,samples):
            pass


def check_transitions(path: Path) -> None:
    per_shot = SHOT_SECONDS * FPS
    midpoint = DISSOLVE * FPS // 2
    # Exclude the caption strip, where text changes at the shot boundary.
    expression = (
        f"gte(n,{per_shot-1})*(eq(mod(n,{per_shot}),{per_shot-1})+"
        f"eq(mod(n,{per_shot}),{midpoint})+eq(mod(n,{per_shot}),{DISSOLVE*FPS+2}))"
    )
    raw = media(
        "-threads","2","-i",str(path),"-map","0:v:0","-an","-sn","-filter_threads","1",
        "-vf",f"select='{expression}',crop=1280:550:0:0,scale=128:55,format=gray",
        "-fps_mode","passthrough","-threads","1","-f","rawvideo","-",capture=True,
    ).stdout
    frames = np.frombuffer(raw,dtype=np.uint8).reshape(-1,55,128).astype(np.float32)
    # The selected sequence is previous endpoint, midpoint, and next endpoint.
    # There is one extra final frame at the end of the file.
    require(len(frames)==(SHOTS-1)*3+1,"cross-dissolve sample count")
    for index,(before,middle,after) in enumerate(frames[:-1].reshape(-1,3,55,128),1):
        difference = np.mean(np.abs(after-before))
        blend_error = np.mean(np.abs(middle-(before+after)*.5))
        require(difference>1 and blend_error<max(1.7,.18*difference),
                f"missing or interrupted dissolve at {index*SHOT_SECONDS}s")


def verify(path: Path, timeline: list[Cue], workers: int) -> None:
    report = probe(path)
    subtitle_streams = [s for s in report["streams"] if s["codec_type"]=="subtitle"]
    video = [s for s in report["streams"] if s["codec_type"]=="video"]
    audio = [s for s in report["streams"] if s["codec_type"]=="audio"]
    require(len(report["streams"])==4 and len(video)==len(audio)==1 and len(subtitle_streams)==2,
            "expected video, stereo audio and two subtitle streams")
    v, a = video[0],audio[0]
    require("mp4" in report["format"]["format_name"].split(","),"MP4 container")
    require(all(Fraction(item["duration"])==TOTAL for item in (report["format"],v,a,*subtitle_streams)),
            "600-second container and stream durations")
    require((v["width"],v["height"],v["sample_aspect_ratio"],v["display_aspect_ratio"])
            == (W,H,"1:1","16:9"),"1280×720, square pixels, 16:9")
    require(v["codec_name"]=="h264" and v["pix_fmt"]=="yuv420p","H.264 video")
    require(all(Fraction(v[key])==FPS for key in ("r_frame_rate","avg_frame_rate"))
            and int(v["nb_read_frames"])==TOTAL*FPS,"30 fps and 18,000 decodable video frames")
    require(a["codec_name"]=="aac" and a["channels"]==2 and int(a["sample_rate"])==RATE,
            "48 kHz stereo AAC")
    require([(s["codec_name"],s["tags"].get("language")) for s in subtitle_streams]
            == [("mov_text","eng"),("mov_text","tam")],"English and Tamil subtitle tracks")
    check_captions(path,timeline,workers)
    check_transitions(path)

    audio_log = subprocess.run(
        ["ffmpeg","-hide_banner","-nostdin","-i",str(path),"-vn","-sn",
         "-af","volumedetect","-f","null","-"],check=True,capture_output=True,text=True,
    ).stderr
    levels = dict(re.findall(r"(mean_volume|max_volume): (-?[\d.]+) dB",audio_log))
    mean, peak = (float(levels[key]) for key in ("mean_volume","max_volume"))
    require(-23 <= mean <= -17 and -14 < peak <= -1,"audible music and peak headroom")
    print(f"Verified {TOTAL}s, {W}×{H}, {FPS} fps, H.264/AAC, "
          f"{len(timeline)} bilingual caption cues, {SHOTS-1} dissolves, music RMS {mean} dBFS and peak {peak} dBFS.",
          flush=True)


def render(path: Path, shots: list[Shot], workers: int) -> None:
    timeline = cues(shots)
    path.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix=".saint-francis-",dir=path.parent) as directory:
        work = Path(directory)
        caption_overlay(TITLE,title=True).save(work/"title.png")
        caption_overlay(PROMO).save(work/"promo.png")
        hashes = set()
        for index,shot in enumerate(shots):
            image = work/f"art-{index:02}.png"
            draw_plate(shot.setting,shot.palette,shot.elements,index,image)
            hashes.add(hashlib.sha256(image.read_bytes()).digest())
            caption_overlay(shot.captions).save(work/f"caption-{index:02}.png")
        require(len(hashes)==SHOTS,"each shot must have its own generated artwork")
        print(f"Generated {SHOTS} distinct story plates and bilingual overlays.",flush=True)
        write_score(work/"score.wav",TOTAL)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for index,_ in enumerate(pool.map(lambda index: clip(work,index),range(SHOTS)),1):
                if index%10==0:
                    print(f"Rendered {index}/{SHOTS} shots.",flush=True)

        (work/"clips.txt").write_text(
            "".join(f"file 'clip-{index:02}.mp4'\nduration {SHOT_SECONDS}\n" for index in range(SHOTS)),
            encoding="utf-8",
        )
        for language,name in enumerate(("english","tamil")):
            (work/f"{name}.srt").write_text(srt_text(timeline,language),encoding="utf-8")
        candidate = work/"documentary.mp4"
        media(
            "-f","concat","-safe","1","-i","clips.txt","-i","score.wav",
            "-i","english.srt","-i","tamil.srt",
            "-map","0:v","-map","1:a","-map","2:s","-map","3:s",
            "-c:v","copy","-c:a","aac","-b:a","192k","-c:s","mov_text",
            "-af","alimiter=level_in=1.6:limit=0.79:attack=5:release=80:level=0:latency=1,apad",
            "-t",str(TOTAL),"-metadata:s:s:0","language=eng","-metadata:s:s:1","language=tam",
            "-disposition:s:0","0","-disposition:s:1","0","-movflags","+faststart",
            candidate.name,cwd=work,
        )
        verify(candidate,timeline,workers)
        candidate.replace(path)
    print(f"Rendered {path}",flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=OUT,help="MP4 path")
    parser.add_argument("--verify-only",action="store_true",help="verify an existing documentary MP4")
    parser.add_argument("--workers",type=int,default=min(3,os.cpu_count() or 1))
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be positive")
    for executable in ("ffmpeg","ffprobe","fc-match"):
        if not shutil.which(executable):
            parser.error(f"Missing executable: {executable}")
    try:
        shots = load_story()
        if args.verify_only:
            verify(args.output.resolve(),cues(shots),args.workers)
        else:
            render(args.output.resolve(),shots,args.workers)
    except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as error:
        parser.exit(1,f"{error}\n")


if __name__=="__main__":
    main()
