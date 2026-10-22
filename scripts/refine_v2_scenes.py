"""Preserve rejected drawings; correct only the two scenery compositions."""
import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'data/subjects/thiaroye-1944-v2.json'
d=json.loads(p.read_text(encoding='utf-8'))
d['export_revision']=3
d['scenes'][0]['image_revision']=3
d['scenes'][0]['visual']='One low whitewashed plaster barracks facade, corrugated iron roof, bare sandy ground, Senegal West Africa 1944. Empty courtyard. Hand drawn angular architecture, flat black shadow, no tree, no people, no porch, no Japanese buildings.'
d['scenes'][2]['image_revision']=3
d['scenes'][2]['visual']='Close-up manga still life of ONE plain white enamel drinking cup on a rough wooden bench, isolated against blank white plaster background. A bold black diagonal shadow. Senegal 1944, symbolic absence, no buildings, no doors, no people, no weapons, no writing.'
p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
print('Only scenes 1 and 3 revised; earlier versions retained')
