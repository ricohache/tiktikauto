"""Validate the future 90s narrative contract without generating media."""
import unittest
from tiktok_history_factory.config.production import load_production_format, ProductionFormat


class ProductionFormatTests(unittest.TestCase):
    def test_ninety_second_structure_and_languages(self):
        profile=load_production_format()
        self.assertEqual(profile.target_seconds,90)
        self.assertEqual([(w.start_seconds,w.end_seconds) for w in profile.windows],[(0,15),(15,75),(75,90)])
        self.assertEqual((profile.audio_language,profile.subtitle_language),('en','fr-FR'))
        self.assertFalse(profile.speed_up_audio)
        self.assertFalse(profile.style_approved)

    def test_reject_incorrect_narrative_boundaries(self):
        data=load_production_format().model_dump()
        data['windows'][1]['start_seconds']=16
        with self.assertRaises(ValueError):
            ProductionFormat.model_validate(data)

    def test_writer_word_budgets_do_not_start_production(self):
        brief=load_production_format().writer_brief()
        self.assertEqual(brief['production_gate'],'BLOCKED_AWAITING_STYLE_APPROVAL')
        self.assertEqual([(s['indicative_english_words_min'],s['indicative_english_words_max']) for s in brief['sections']],[(30,36),(120,145),(30,36)])
