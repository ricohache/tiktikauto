"""Pinned V2 assets; inspect publisher cards before any weight download."""
import json
import sys
import urllib.request
from pathlib import Path
from acquire_pilot_assets import download, ROOT, LICENSES


def metadata(repo):
    with urllib.request.urlopen('https://huggingface.co/api/models/' + repo + '?blobs=true', timeout=30) as r:
        return json.load(r)


def acquire(repo, revision, filename, target, info):
    item = next(x for x in info['siblings'] if x['rfilename'] == filename)
    return download(repo, revision, filename, target, item['size'], item.get('lfs', {}).get('sha256'))


if __name__ == '__main__':
    repo = 'rhasspy/piper-voices'
    info = metadata(repo)
    revision = info['sha']
    for name in ('john', 'kristin'):
        folder = f'en/en_US/{name}/medium/'
        card = download(repo, revision, folder+'MODEL_CARD', LICENSES/f'{name}-MODEL_CARD.md')
        if 'public domain' not in Path(card['path']).read_text():
            raise RuntimeError('Voice dataset licence changed; review required')
        for suffix in ('.onnx', '.onnx.json'):
            filename = f'en_US-{name}-medium'+suffix
            acquire(repo, revision, folder+filename, ROOT/'tools/piper/voices'/filename, info)
    repo = 'artificialguybr/LineAniRedmond-LinearMangaSDXL-V2'
    revision = '411d5335378c13e63bf0d5376b405a39e9a869cb'
    info = metadata(repo)
    if info['sha'] != revision:
        raise RuntimeError('Publisher revision changed; review before acquiring')
    download(repo, revision, 'README.md', LICENSES/'LineAniRedmondV2-README.md')
    acquire(repo, revision, 'LineAniRedmondV2-Lineart-LineAniAF.safetensors',
            ROOT/'ComfyUI/ComfyUI/models/loras/LineAniRedmondV2-Lineart-LineAniAF.safetensors', info)
