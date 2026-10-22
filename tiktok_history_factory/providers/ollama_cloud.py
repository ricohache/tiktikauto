"""Ollama native /api and OpenAI /v1 contracts; no implicit paid fallback."""
import json
import urllib.error
import urllib.request


class OllamaCloudClient:
    def __init__(self, base_url, api_key, model='kimi-k3:cloud', timeout=120):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def chat(self, messages, temperature=0.3, max_tokens=1000):
        compatible = self.base_url.endswith('/v1')
        url = self.base_url + ('/chat/completions' if compatible else
                              '/chat' if self.base_url.endswith('/api') else '/api/chat')
        payload = {'model': self.model, 'messages': messages, 'stream': False}
        if compatible:
            payload.update(temperature=temperature, max_tokens=max_tokens)
        else:
            payload.update(options={'temperature': temperature, 'num_predict': max_tokens})
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = 'Bearer ' + self.api_key
        try:
            request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.load(response)
            if compatible:
                data['message'] = data['choices'][0]['message']
            if not data.get('message', {}).get('content', '').strip():
                return {'status': 'FAILED', 'error': 'Empty model response'}
            data['message'].pop('thinking', None)
            return {**data, 'status': 'SUCCESS', 'endpoint': url}
        except urllib.error.HTTPError as exc:
            return {'status': 'FAILED', 'http_code': exc.code, 'error': exc.reason}
        except Exception as exc:
            return {'status': 'FAILED', 'error': str(exc)}

    def generate(self, prompt, **kwargs):
        return self.chat([{'role': 'user', 'content': prompt}], **kwargs)
