"""Compose and mix an original stereo instrumental bed."""

from pathlib import Path
import wave

import numpy as np

RATE = 48_000
# Harmonic variations in C, A minor and F, with a G cadence.
PROGRESSIONS = (
    ((48,55,60,64,67), (45,52,60,64,69), (41,53,57,60,65), (43,55,59,62,67)),
    ((45,52,57,60,64), (40,52,55,59,64), (41,48,57,60,65), (43,50,55,59,62)),
    ((41,53,57,60,65), (48,55,60,64,67), (43,55,59,62,67), (45,52,57,60,64)),
    ((48,55,59,64,67), (41,53,57,60,65), (43,55,62,65,71), (48,55,60,64,72)),
)


def write_score(path: Path, seconds: int) -> None:
    samples = seconds * RATE
    stereo = np.zeros((samples, 2), dtype=np.float32)
    duration = 4
    t = np.arange(duration*RATE) / RATE
    pluck = np.minimum(1, t/.045) * np.exp(-1.5*t) * np.clip((2.65-t)/.43, 0, 1)
    pad = np.minimum(1, t/.58) * np.clip((3.72-t)/1.2, 0, 1)
    voices = {}

    def add(pitch, start, gain, pan, sustained=False):
        key = (pitch, sustained)
        if key not in voices:
            phase = 2*np.pi * 440 * 2**((pitch-69)/12) * t
            tone = np.sin(phase) + .16*np.sin(2*phase) * np.exp(-.5*t)
            if sustained:
                tone += .12*np.sin(phase*1.003)
            voices[key] = np.asarray(tone * (pad if sustained else pluck), dtype=np.float32)
        voice = voices[key]
        index = round(start*RATE)
        length = min(len(voice), samples-index)
        if length <= 0:
            return
        stereo[index:index+length, 0] += gain * np.sqrt(1-pan) * voice[:length]
        stereo[index:index+length, 1] += gain * np.sqrt(pan) * voice[:length]
        delay = round(.19*RATE)
        echo_length = min(length,samples-index-delay)
        if echo_length > 0:
            stereo[index+delay:index+delay+echo_length, 1] += .14 * gain * voice[:echo_length]

    bar = 0
    for start in range(0,seconds,4):
        section = (bar//8) % len(PROGRESSIONS)
        chord = PROGRESSIONS[section][bar%4]
        if seconds-start <= 8:
            chord = PROGRESSIONS[-1][2 if seconds-start > 4 else 3]
        add(chord[0],start,.42,.48,True)
        add(chord[1],start+.12,.15,.57,True)
        pattern = ((2,3,4,3,1), (3,2,4,1,2), (1,3,2,4,3), (2,4,3,2,1))[section]
        for i,(offset,note) in enumerate(zip((.2,.84,1.63,2.49,3.18),pattern)):
            pitch = chord[note] if i != 2 or bar%4 != 2 else chord[note]+12
            add(pitch,start+offset,.37 if i in (0,2) else .28,.36 if i%2 else .62)
        bar += 1

    stereo[:RATE] *= np.linspace(0,1,RATE,dtype=np.float32)[:,None]
    tail = min(seconds,4)*RATE
    stereo[-tail:] *= np.linspace(1,0,tail,dtype=np.float32)[:,None]
    rms = float(np.sqrt(np.einsum("ij,ij->",stereo,stereo,dtype=np.float64)/stereo.size))
    target_gain = 10**(-20/20)/rms
    # Preserve mix headroom in the WAV. FFmpeg applies makeup gain and a
    # look-ahead peak limiter when it encodes the final AAC stream.
    peak = float(np.max(np.abs(stereo)))
    gain = min(target_gain/1.6,.86/peak)
    with wave.open(str(path),"wb") as output:
        output.setparams((2,2,RATE,0,"NONE","not compressed"))
        for start in range(0,samples,10*RATE):
            pcm = np.rint(stereo[start:start+10*RATE]*gain*32767).astype("<i2")
            output.writeframesraw(pcm.tobytes())
