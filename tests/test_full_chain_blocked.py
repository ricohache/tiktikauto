import json, shutil, sys
from pathlib import Path

ROOT = Path(r'C:\TikTokHistoryFactory')
sys.path.insert(0, str(ROOT / 'src' / 'v5_factory'))

from discovery import HistoryDiscovery
from auto_engine import AutoProductionEngine
from tiktok_queue import TikTokQueue

def main():
    # Setup isolated env
    test_dir = ROOT / 'tests' / 'audit_full_chain'
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)
    (test_dir / 'data' / 'catalogue').mkdir(parents=True, exist_ok=True)
    (test_dir / 'data' / 'pre_sourced').mkdir(parents=True, exist_ok=True)
    (test_dir / 'work').mkdir(parents=True, exist_ok=True)

    cat = test_dir / 'data' / 'catalogue' / 'subjects.json'
    cat.write_text(json.dumps({'subjects': []}, ensure_ascii=False), encoding='utf-8')

    # New subject
    slug = 'berlin-wall-1989'
    ps_dir = test_dir / 'data' / 'pre_sourced' / slug
    ps_dir.mkdir(parents=True, exist_ok=True)
    summary = (
        'In November nineteen eighty-nine, the Berlin Wall fell after twenty-eight years of division. '
        'The East German regime had built the concrete barrier in nineteen sixty-one to stop citizens from fleeing to the West. '
        'For decades, families were separated and escape attempts ended in death at the border. '
        'In the summer of nineteen eighty-nine, Hungary opened its border with Austria, allowing East Germans to escape. '
        'Mass protests erupted in Leipzig and other cities throughout the autumn, demanding democratic reforms. '
        'On November ninth, a confused press conference announcement led thousands to gather at border crossings. '
        'Border guards, overwhelmed and without clear orders, eventually opened the gates. '
        'East and West Berliners celebrated together on the wall, chipping away at the concrete with hammers. '
        'The fall of the wall symbolized the collapse of Soviet communism across Eastern Europe. '
        'Germany reunified formally in October nineteen ninety, ending four decades of Cold War division. '
        'The event remains a powerful reminder that oppressive systems can crumble when people demand freedom. '
        'Today, fragments of the wall stand as memorials to the courage of those who resisted tyranny. '
        'The Berlin Wall teaches that physical barriers cannot forever divide a people determined to be free.'
    )
    summary_fr = (
        'En novembre mille neuf cent quatre-vingt-neuf, le mur de Berlin tomba apres vingt-huit annees de division. '
        'Le regime est-allemand avait construit la barriere de beton en mille neuf cent soixante et un pour empecher les citoyens de fuir vers l Ouest. '
        'Pendant des decennies, des familles furent separees et les tentatives d evasion se terminerent par la mort a la frontiere. '
        'En ete mille neuf cent quatre-vingt-neuf, la Hongrie ouvrit sa frontiere avec l Autriche, permettant aux Allemands de l Est de s echapper. '
        'Des protestations de masse eclaterent a Leipzig et dans d autres villes tout au long de l automne, exigeant des reformes democratiques. '
        'Le neuf novembre, une annonce confuse lors d une conference de presse amena des milliers de personnes aux points de passage frontaliers. '
        'Les gardes frontaliers, debordes et sans ordres clairs, finirent par ouvrir les portes. '
        'Les Berlinois de l Est et de l Ouest celebrerent ensemble sur le mur, entamant le beton a coups de marteau. '
        'La chute du mur symbolisa l effondrement du communisme sovietique a travers l Europe de l Est. '
        'L Allemagne se reunifia formellement en octobre mille neuf cent quatre-vingt-dix, mettant fin a quatre decennies de division de la Guerre froide. '
        'L evenement demeure un puissant rappel que les systemes oppressifs peuvent s effondrer lorsque les gens exigent la liberte. '
        'Aujourd hui, des fragments du mur se dressent comme des memorials au courage de ceux qui resisterent a la tyrannie. '
        'Le mur de Berlin enseigne que les barrieres physiques ne peuvent diviser eternellement un peuple determine a etre libre.'
    )
    dossier = {
        'slug': slug,
        'title_en': 'The Fall of the Berlin Wall',
        'title_fr': 'La chute du mur de Berlin',
        'summary_en': summary,
        'summary_fr': summary_fr,
        'event_date': '1989-11-09',
        'sources': [
            {'name': 'Wikipedia EN', 'url': 'https://en.wikipedia.org/wiki/Berlin_Wall', 'language': 'en'},
            {'name': 'Deutsches Historisches Museum', 'url': 'https://www.dhm.de', 'language': 'de'}
        ],
        'scenes': [],
        'wikipedia_url': '',
        'style_prompt': 'Japanese 2D seinen manga panel, bold expressive ink, weighted clean contours, solid black shadow shapes, halftone screentone dots, dramatic cinematic contrast, mature realistic anatomy, black and white with neutral gray, professional manga drawing, historical scene, no text, vertical composition'
    }
    (ps_dir / 'dossier.json').write_text(json.dumps(dossier, ensure_ascii=False, indent=2), encoding='utf-8')

    # Discover
    disc = HistoryDiscovery(test_dir / 'data' / 'factory.db', cat, test_dir / 'data' / 'pre_sourced')
    disc._test_network = lambda: False
    found = disc.discover(1)
    assert len(found) == 1 and found[0]['slug'] == slug
    print('[TEST] Discovery: PASS')

    # Storyboard
    engine = AutoProductionEngine(test_dir)
    subject = found[0]
    work_dir = test_dir / 'work' / f'auto-{slug}'
    work_dir.mkdir(parents=True, exist_ok=True)
    sb_path = engine.generate_storyboard(subject, work_dir)
    sb = json.loads(sb_path.read_text(encoding='utf-8'))
    scenes = sb.get('scenes', [])
    num_scenes = len(scenes)
    num_shots = num_scenes * 2
    print(f'[TEST] Storyboard: {num_scenes} scenes = {num_shots} shots')
    assert 11 <= num_scenes <= 13
    assert 22 <= num_shots <= 26

    # Verify art-direction block
    art_dir = json.loads((ROOT / 'data' / 'decisions' / 'art-direction-20261019.json').read_text(encoding='utf-8'))
    if not art_dir.get('final_image_generation_allowed'):
        print('[TEST] Image generation BLOCKED by art-direction decision')
        print('[TEST] Video production cannot proceed. Pipeline validated up to storyboard.')
        print('\n=== RESULT: PIPELINE VALIDATED, PRODUCTION BLOCKED BY POLICY ===')
        print(f'Subject: {slug}')
        print(f'Scenes: {num_scenes}')
        print(f'Shots: {num_shots}')
        print(f'Storyboard: {sb_path}')
        print('Next step requires: final_image_generation_allowed=true + style_approved=true')
        return

if __name__ == '__main__':
    main()
