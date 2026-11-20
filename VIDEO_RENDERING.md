# Saint Francis of Assisi rendering

The Python renderer generates six original placeholder illustrations, an original stereo instrumental score, and English–Tamil captions. The first plate carries the bilingual opening title. Five 0.8-second cross-dissolves connect the six plates. The last plate carries “Like, Hype, Share and Subscribe” from 25.000 seconds through the end.

## GitHub Actions

Relevant pull requests run **Render Saint Francis video** automatically. After the workflow reaches the default branch, open **Actions** → **Render Saint Francis video** → **Run workflow**, choose the branch, and select **Run workflow** again. Once the run succeeds, open its summary and download **Saint-Francis-Video** under **Artifacts**. The ZIP contains `Saint_Francis_Test.mp4`.

FFprobe verification is part of the render step. It checks the MP4 container, exact duration of the container and both streams, frame count, frame rate, dimensions, sample aspect ratio, and H.264/AAC codecs. A failed render or verification prevents the upload.

## Local Ubuntu render

Use Python 3.12 and install the same dependencies as the workflow.

```bash
sudo apt-get install ffmpeg fonts-noto-core fonts-dejavu-core python3-venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python render_video.py
python render_video.py --verify-only
```

The renderer uses FFmpeg with libx264, AAC and libass with complex script shaping. Use `--output PATH` to render or verify a different MP4 path. Working assets are regenerated on each run and removed when it ends.
