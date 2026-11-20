import re
import unittest

from documentary.render import (
    ENDING, FPS, PROMO, SHOTS, TITLE, TOTAL, caption_overlay, cues, load_story, srt_text,
)


class DocumentaryTest(unittest.TestCase):
    def setUp(self):
        self.shots = load_story()
        self.timeline = cues(self.shots)

    def test_sixty_shots_and_exact_ending(self):
        self.assertEqual(len(self.shots), SHOTS)
        self.assertEqual(SHOTS, 60)
        self.assertEqual(TOTAL * FPS, 18000)
        self.assertEqual(self.timeline[0].start, 0)
        self.assertEqual(self.timeline[-1].start, ENDING)
        self.assertEqual(self.timeline[-1].end, 600)
        self.assertEqual(TOTAL - ENDING, 5)
        self.assertEqual(self.timeline[-1].captions, PROMO)
        for previous, following in zip(self.timeline, self.timeline[1:]):
            self.assertEqual(previous.end, following.start)

    def test_distinct_art_direction_and_captions_fit(self):
        signatures = {shot.elements for shot in self.shots}
        self.assertEqual(len(signatures), SHOTS)
        for cue in self.timeline:
            with self.subTest(time=cue.start):
                self.assertEqual(caption_overlay(cue.captions).size, (1280, 144))
        self.assertEqual(caption_overlay(TITLE, title=True).size, (1280, 178))

    def test_english_and_tamil_srt(self):
        for language in (0, 1):
            track = srt_text(self.timeline, language)
            self.assertEqual(len(re.findall(r" --> ", track)), 61)
            self.assertIn("00:09:55,000 --> 00:10:00,000", track)
            self.assertTrue(track.endswith(PROMO[language] + "\n"))


if __name__ == "__main__":
    unittest.main()
