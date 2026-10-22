"""Future production format; kept separate from the short technical pilot."""
import json
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class NarrativeWindow(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    name:Literal['introduction','development','conclusion']
    start_seconds:int=Field(ge=0)
    end_seconds:int=Field(gt=0)
    purpose:str=Field(min_length=1)


class ProductionFormat(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    schema_version:Literal[3]
    target_seconds:Literal[90]
    audio_language:Literal['en']
    subtitle_language:Literal['fr-FR']
    target_words_per_minute_min:int=120
    target_words_per_minute_max:int=145
    speed_up_audio:Literal[False]=False
    style_approved:Literal[False]=False
    publication_enabled:Literal[False]=False
    schedule_enabled:Literal[False]=False
    windows:list[NarrativeWindow]=Field(min_length=3,max_length=3)

    @model_validator(mode='after')
    def correct_windows(self):
        expected=[('introduction',0,15),('development',15,75),('conclusion',75,90)]
        actual=[(w.name,w.start_seconds,w.end_seconds) for w in self.windows]
        if actual!=expected:
            raise ValueError('Production structure must be introduction0..15, development15..75, conclusion75..90')
        if not 0<self.target_words_per_minute_min<=self.target_words_per_minute_max:
            raise ValueError('Invalid natural narration pace')
        return self

    def writer_brief(self):
        """A usable planning contract, without starting any generation or TTS."""
        return {'target_seconds':self.target_seconds,'audio_language':self.audio_language,
            'subtitle_language':self.subtitle_language,'words_are_indicative':True,
            'timing_rule':'Measure English WAV; rewrite or adjust pauses, never accelerate speech',
            'production_gate':'BLOCKED_AWAITING_STYLE_APPROVAL',
            'sections':[{'name':w.name,'start_seconds':w.start_seconds,'end_seconds':w.end_seconds,
                'purpose':w.purpose,'indicative_english_words_min':(w.end_seconds-w.start_seconds)*self.target_words_per_minute_min//60,
                'indicative_english_words_max':(w.end_seconds-w.start_seconds)*self.target_words_per_minute_max//60} for w in self.windows]}


def load_production_format(path=None):
    root=Path(__file__).resolve().parents[2]
    target=Path(path) if path else root/'data/production/format-v3-90s.json'
    return ProductionFormat.model_validate(json.loads(target.read_text(encoding='utf-8')))
