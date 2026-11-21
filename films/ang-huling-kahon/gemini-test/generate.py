import argparse
import base64
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL = 'gemini-omni-1.2-flash'
FORMAT = {'type': 'video', 'duration': '8s', 'resolution': '720p', 'aspect_ratio': '16:9'}
REFERENCES = [ROOT / 'references' / f'{name}.jpg' for name in ('ben', 'lita', 'kitchen')]
CONTINUITY = (
    'Original naturalistic Filipino drama, present-day Pampanga. In reference order: '
    'Ben, Lita, and their shared kitchen. Preserve their faces, hairstyles, white polo '
    'and pale blue blouse, worn table, soft warm window light, and the letter. '
    'Use quiet room tone. Keep the camera fixed. No titles, subtitles, or music.'
)

parser = argparse.ArgumentParser()
parser.add_argument('--generate', action='store_true', help='Submit the three paid video requests')
args = parser.parse_args()
shots = json.loads((ROOT / 'shots.json').read_text())
for path in REFERENCES:
    if not path.is_file():
        parser.error(f'Missing visual reference: {path.name}')
if not args.generate:
    print(f'Prepared {len(shots)} × 8 seconds at 720p using {MODEL}; no API calls made.')
    raise SystemExit(0)

key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
if not key:
    parser.error('Set GEMINI_API_KEY securely in the Codex runtime.')
from google import genai

client = genai.Client(api_key=key)
image_parts = [
    {'type': 'image', 'mime_type': 'image/jpeg',
     'data': base64.b64encode(path.read_bytes()).decode('ascii')}
    for path in REFERENCES
]
for shot in shots:
    target = ROOT / f"{shot['id']}.mp4"
    if target.is_file():
        print(f'{target.name} already exists')
        continue
    pending = target.with_suffix('.pending')
    with pending.open('x') as marker:
        marker.write('Request started. Check Google activity before retrying an uncertain submission.\n')
    result = client.interactions.create(
        model=MODEL,
        input=[{'type': 'text', 'text': CONTINUITY + ' ' + shot['action']}, *image_parts],
        response_format=FORMAT,
    )
    video = result.output_video
    if video is None or not video.data:
        raise RuntimeError(f"No video returned for {shot['id']}; inspect the interaction before retrying.")
    draft = target.with_suffix('.partial')
    draft.write_bytes(base64.b64decode(video.data))
    draft.replace(target)
    pending.unlink()
    print(f'Saved {target.name}')
