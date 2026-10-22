"""Versioned bilingual input contracts; legacy dossiers remain readable."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Utterance(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    en: str = Field(min_length=1)
    fr: str = Field(min_length=1)


class BilingualScene(BaseModel):
    model_config = ConfigDict(extra='allow', strict=True)
    id: int = Field(ge=1, le=6)
    narration: str
    translation_fr: str
    visual: str = Field(min_length=1)
    claims: list[str] = Field(min_length=1)
    utterances: list[Utterance] = Field(min_length=1)

    @model_validator(mode='after')
    def texts_match(self):
        if self.narration != ' '.join(u.en for u in self.utterances):
            raise ValueError('English utterances differ from narration')
        if self.translation_fr != ' '.join(u.fr for u in self.utterances):
            raise ValueError('French utterances differ from translation')
        return self


class BilingualDossier(BaseModel):
    model_config = ConfigDict(extra='allow', strict=True)
    schema_version: Literal[2]
    audio_language: Literal['en']
    spoken_language: Literal['en-US', 'en-GB']
    subtitle_language: Literal['fr-FR']
    translation_locale: Literal['fr-FR']
    scenes: list[BilingualScene] = Field(min_length=3, max_length=6)
