"""Alignement amélioré des sous-titres FR par durée phonétique réelle du WAV.
Remplace l'allocation proportionnelle simple par une segmentation par phrases naturelles.
Sans Whisper, on utilise la durée mesurée de chaque fichier WAV Piper.
"""
import math
import re


def split_into_sentences(text: str) -> list:
    """Segmente un texte en phrases naturelles."""
    # Séparateurs: . ! ? ; — suivi d'espace ou fin de chaîne
    sentences = re.split(r'(?<=[.!?;—])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]




def _split_into_chunks(text: str, max_chars: int = 55) -> list:
    """Decoupe un texte long en segments de max_chars caracteres max."""
    if len(text) <= max_chars:
        return [text]
    chunks = []
    words = text.split()
    current = ''
    for word in words:
        if len(current) + len(word) + 1 <= max_chars:
            current = (current + ' ' + word).strip()
        else:
            if current:
                chunks.append(current)
            current = word
    if current:
        chunks.append(current)
    return chunks
def estimate_phonetic_weight(text: str) -> float:
    """Estime le poids phonétique d'un texte par le nombre de syllabes approximatif.
    Français: ~1 syllabe par voyelle groupée.
    """
    # Compte les groupes de voyelles comme des syllabes approximatives
    vowels = re.findall(r'[aeiouyàâäéèêëïîôöùûü]+', text.lower())
    return max(len(vowels), 1)


def allocate_sentence_timestamps(sentences_en: list, sentences_fr: list, 
                                   voice_duration_sec: float) -> list:
    """Alloue les timestamps de chaque phrase proportionnellement à son poids phonétique.
    Retourne une liste de (texte_fr, start_sec, end_sec).
    """
    if len(sentences_en) != len(sentences_fr):
        # Si mismatch, utiliser le texte FR comme référence
        sentences_fr = split_into_sentences(' '.join(sentences_fr))
    
    if not sentences_fr:
        return []
    
    # Calculer les poids phonétiques
    weights = [estimate_phonetic_weight(s) for s in sentences_en]
    total_weight = sum(weights)
    
    result = []
    current_time = 0.0
    
    for i, fr_text in enumerate(sentences_fr):
        weight = weights[i] if i < len(weights) else 1.0
        duration = voice_duration_sec * weight / total_weight
        end_time = current_time + duration
        result.append({
            'text': fr_text,
            'start_sec': round(current_time, 3),
            'end_sec': round(end_time, 3),
            'duration_sec': round(duration, 3),
            'weight': weight
        })
        current_time = end_time
    
    return result


def build_subtitle_segments(scene_narration_en: str, scene_narration_fr: str,
                             voice_duration_sec: float, min_duration: float = 1.5) -> list:
    """Construit les segments de sous-titres alignés sur la narration réelle.
    """
    sentences_en = split_into_sentences(scene_narration_en)
    sentences_fr = split_into_sentences(scene_narration_fr)
    
    # Si le nombre de phrases diffère, essayer d'aligner
    if len(sentences_en) != len(sentences_fr):
        # Utiliser le texte FR comme base, segmenter le EN par ponctuation
        # Si trop de phrases EN, les fusionner
        if len(sentences_en) > len(sentences_fr):
            # Fusionner les phrases EN excédentaires
            merged = []
            ratio = len(sentences_en) / len(sentences_fr)
            idx = 0
            for _ in range(len(sentences_fr)):
                count = max(1, round(ratio))
                chunk = ' '.join(sentences_en[idx:idx+count])
                merged.append(chunk)
                idx += count
            sentences_en = merged
        elif len(sentences_fr) > len(sentences_en):
            # Fusionner les phrases FR excédentaires
            merged = []
            ratio = len(sentences_fr) / len(sentences_en)
            idx = 0
            for _ in range(len(sentences_en)):
                count = max(1, round(ratio))
                chunk = ' '.join(sentences_fr[idx:idx+count])
                merged.append(chunk)
                idx += count
            sentences_fr = merged
    
    # Allouer les timestamps
    segments = allocate_sentence_timestamps(sentences_en, sentences_fr, voice_duration_sec)
    
    # Decouper les segments longs (>55 chars) en morceaux plus courts
    split_segments = []
    for seg in segments:
        text = seg['text']
        if len(text) <= 55:
            split_segments.append(seg)
        else:
            chunks = _split_into_chunks(text, 55)
            total_weight = estimate_phonetic_weight(text)
            current_time = seg['start_sec']
            for chunk in chunks:
                chunk_weight = estimate_phonetic_weight(chunk)
                duration = seg['duration_sec'] * chunk_weight / total_weight if total_weight > 0 else seg['duration_sec'] / len(chunks)
                end_time = current_time + duration
                split_segments.append({
                    'text': chunk,
                    'start_sec': round(current_time, 3),
                    'end_sec': round(end_time, 3),
                    'duration_sec': round(duration, 3),
                    'weight': chunk_weight
                })
                current_time = end_time
    
    # Fusionner les segments trop courts
    merged = []
    i = 0
    while i < len(split_segments):
        seg = split_segments[i].copy()
        while seg['duration_sec'] < min_duration and i + 1 < len(split_segments):
            i += 1
            next_seg = split_segments[i]
            seg['text'] += ' ' + next_seg['text']
            seg['end_sec'] = next_seg['end_sec']
            seg['duration_sec'] = seg['end_sec'] - seg['start_sec']
        merged.append(seg)
        i += 1
    
    return merged


if __name__ == '__main__':
    # Test
    en = "On December first, nineteen forty-four, French troops opened fire. African soldiers were killed. Their exact number remains disputed."
    fr = "Le 1er décembre 1944, des troupes françaises ont ouvert le feu. Des soldats africains ont été tués. Leur nombre exact reste débattu."
    result = build_subtitle_segments(en, fr, 8.5)
    for r in result:
        print(f"[{r['start_sec']:.2f} - {r['end_sec']:.2f}] {r['text']}")
