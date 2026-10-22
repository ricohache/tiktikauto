"""V2 language, pace, caption and rendering regression contracts."""
import inspect
import json
import unittest
from pathlib import Path
from tiktok_history_factory.config.settings import Settings
from tiktok_history_factory.media.bilingual_audio import caption_lines
from tiktok_history_factory.media.prompts import build_image_prompt
from tiktok_history_factory.pipeline.pilot import validate_dossier, visual_inputs
from tiktok_history_factory.providers.comfyui_images import ComfyUIImageProvider
from tiktok_history_factory.providers.ffmpeg import FFmpegProvider
from tiktok_history_factory.providers.piper_tts import PiperTTSProvider


class V2Contracts(unittest.TestCase):
    def test_explicit_english_locale_must_match_voice(self):
        provider = PiperTTSProvider(Settings().PIPER_MODEL_PATH, expected_language='en-GB')
        self.assertFalse(provider.available)

    def test_translation_and_voice_do_not_invalidate_images(self):
        scene = {'id':1, 'positive':'manga', 'negative':'photo', 'seed':42, 'translation_fr':'avant'}
        before = visual_inputs([scene])
        scene.update(translation_fr='après', narration='New English', voice='new voice')
        self.assertEqual(before, visual_inputs([scene]))
        scene['positive'] = 'changed drawing'
        self.assertNotEqual(before, visual_inputs([scene]))

    def test_new_defaults_are_english_french(self):
        s = Settings()
        self.assertEqual(s.SPOKEN_LANGUAGE, 'en-US')
        self.assertEqual(s.SUBTITLE_LANGUAGE, 'fr-FR')
        self.assertNotIn('fr_FR', s.PIPER_MODEL_PATH)
        self.assertFalse(s.TIKTOK_PUBLISH_ENABLED)

    def test_french_voice_cannot_silently_replace_english(self):
        s = Settings()
        provider = PiperTTSProvider(str(s.PROJECT_ROOT/'tools/piper/voices/fr_FR-siwis-medium.onnx'))
        self.assertFalse(provider.available)

    def test_acceleration_is_rejected(self):
        provider = PiperTTSProvider(Settings().PIPER_MODEL_PATH)
        if provider.available:
            self.assertEqual(provider.synthesize('Test.', 'unused.wav', .9)['status'], 'BLOCKED')

    def test_captions_reject_three_lines(self):
        with self.assertRaises(ValueError):
            caption_lines('Un texte beaucoup trop long. '*10)
        self.assertLessEqual(len(caption_lines('Le bilan et les circonstances exactes restent débattus.').splitlines()), 2)

    def test_translation_mismatch_is_rejected(self):
        dossier = json.loads(Path(Settings().PILOT_DOSSIER).read_text(encoding='utf-8'))
        dossier['scenes'][0]['translation_fr'] = 'Wrong translation'
        with self.assertRaises(ValueError):
            validate_dossier(dossier)

    def test_style_leads_prompt_and_lora_connects_both_encoders(self):
        self.assertTrue(build_image_prompt('Senegal 1944').startswith('LineAniAF'))
        graph = ComfyUIImageProvider.workflow('a','b','base',768,1344,42,28,'manga',1)
        self.assertEqual(graph['2']['inputs']['clip'], ['8',1])
        self.assertEqual(graph['3']['inputs']['clip'], ['8',1])
        self.assertEqual(graph['5']['inputs']['model'], ['8',0])

    def test_no_permanent_drawtext_or_tempo_filter(self):
        source = inspect.getsource(FFmpegProvider.render_pilot)
        self.assertNotIn('drawtext=', source)
        self.assertNotIn('atempo', source)
        self.assertIn('comment=Reconstitution historique', source)
        self.assertIn('ass=captions.ass', source)
