import json, urllib.request

# Tester Ollama pour generer un scenario historique
prompt = '''Generate a JSON object for a historical TikTok video about an African historical event. 
The video should be about 90 seconds in English narration.
Provide:
- slug: kebab-case identifier with year
- title_en: English title
- title_fr: French title
- event_date: YYYY-MM-DD
- summary_en: 2 sentences
- summary_fr: 2 sentences in French
- scenes: array of 12 objects, each with:
  - narration_en: one sentence, ~15-17 words, slow clear English for TTS
  - narration_fr: French translation, one sentence
  - image_prompt: detailed Japanese seinen manga panel description, black and white, no text

Respond ONLY with valid JSON.'''

data = {
    "model": "qwen2.5-coder:7b",
    "prompt": prompt,
    "stream": False,
    "options": {"temperature": 0.7, "num_predict": 2000}
}

req = urllib.request.Request(
    "http://localhost:11434/api/generate",
    data=json.dumps(data).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode())
    print(result.get("response", "NO RESPONSE")[:2000])
except Exception as e:
    print(f"Error: {e}")
