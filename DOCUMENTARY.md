# Saint Francis of Assisi documentary

The ten-minute production has 60 individually composed, original storybook illustrations and an original instrumental score. It covers Francis's upbringing in Assisi, his conversion and renunciation, San Damiano, the Friars Minor, Clare of Assisi, preaching, creation, the Sultan, La Verna, his death, and his legacy. The artwork uses shared vector motifs for recurring people and places. It is stylized and should not be read as a reconstruction of medieval Assisi or a likeness of its inhabitants.

## Run on GitHub

Pull requests that change the documentary or its dependencies trigger **Render Saint Francis 10-minute video**. Once the workflow is on the default branch, open **Actions** → **Render Saint Francis 10-minute video** → **Run workflow**. After a successful run, download **Saint-Francis-10-Minute-Video** from the run summary. The ZIP contains `Saint_Francis_10_Minute.mp4`. The 30-second renderer has its own workflow and artifact.

## Run locally on Ubuntu

```bash
sudo apt-get update
sudo apt-get install ffmpeg fontconfig fonts-noto-core fonts-dejavu-core python3-venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-documentary.txt
python -m unittest discover -s documentary/tests
python -m documentary.render
python -m documentary.render --verify-only
```

Use `--output PATH` for a different MP4 location and `--workers N` to set render parallelism. Rendering generates and cleans up the artwork, intermediate clips, caption overlays, subtitles, and stereo WAV. The final file is published only after verification succeeds.

Each shot occupies ten seconds. Beginning with shot two, its first second cross-dissolves into its artwork from the preceding plate. The opening title is layered over the first shot. The last illustration carries the devotional closing line until 09:55, then the bilingual call to action through 10:00.

Both captions are burned into the picture using RAQM for Tamil shaping. The MP4 additionally contains selectable English and Tamil text tracks, which start disabled. Verification decodes and counts the frames, checks durations and stream properties, compares the extracted timed captions with the script, checks both languages at the expected glyph positions in each burned-in cue, checks the midpoint of every dissolve, and measures the decoded audio level. The mix targets approximately −20 dBFS RMS. FFmpeg applies a look-ahead peak limiter before AAC encoding.

## Historical references

- [Franciscan Media chronology](https://www.franciscanmedia.org/franciscan-tradition-and-resources/chronology-of-the-life-of-st-francis/)
- [Benedict XVI’s general audience on Francis](https://www.vatican.va/content/benedict-xvi/en/audiences/2010/documents/hf_ben-xvi_aud_20100127.html)
- [Michael Robson’s Cambridge chronology](https://assets.cambridge.org/97805217/60430/frontmatter/9780521760430_frontmatter.pdf)
- [John Paul II on naming Francis patron of ecology](https://www.vatican.va/content/john-paul-ii/en/messages/peace/documents/hf_jp-ii_mes_19891208_xxiii-world-day-for-peace.html)
- [Vatican News biography](https://www.vaticannews.va/en/saints/10/04/st--francis-of-assisi--founder-of-the-franciscan--order--patron-.html)

Dates are approximate where the sources vary. The story attributes the speaking crucifix, the preaching to birds, and the vision at La Verna to early accounts.
