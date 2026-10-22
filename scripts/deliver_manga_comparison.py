"""Package six observed artistic tests, actual API graphs and preservation proof."""
import html
import json
import shutil
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageStat

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from compare_manga_ink import WORK, SCENES, STYLE, NEGATIVE, digest, save_json

OUT=ROOT/'output/review/art-comparison-20261019-manga-ink'
LABELS=('A-LineAniRedmond','B-MangaInk','C-BoldLineManga')
LORAS=('LineAniRedmondV2-Lineart-LineAniAF.safetensors','manga-ink-screentone.safetensors','boldlinemanga.safetensors')
TRIGGERS=('LineAniAF','m4ng41nk','in the style of TOK')
STRENGTHS=(1.0,.85,1.0)


def archive_sources():
    sources={
      'DiffSensei-README.md':'https://raw.githubusercontent.com/jianzongwu/DiffSensei/main/README.md',
      'Drawatoon-v1-README.md':'https://huggingface.co/fumeisama/drawatoon-v1/raw/main/README.md',
      'BandW-Manga-README.md':'https://huggingface.co/alvdansen/BandW-Manga/raw/main/README.md',
      'MangaDiffusionPoC-README-ja.md':'https://huggingface.co/aipicasso/manga-diffusion-poc/raw/main/README.md',
      'MangaDiffusionPoC-README-en.md':'https://huggingface.co/aipicasso/manga-diffusion-poc/raw/main/README_en.md',
      'MangaDiffusionPoC-LICENSE.txt':'https://huggingface.co/aipicasso/manga-diffusion-poc/raw/main/LICENSE',
      'LineAni-CreativeML-OpenRAIL-M.txt':'https://raw.githubusercontent.com/CompVis/stable-diffusion/main/LICENSE'}
    records=[]
    folder=WORK/'candidate-research'
    folder.mkdir(exist_ok=True)
    for name,url in sources.items():
        path=folder/name
        if not path.exists():
            with urllib.request.urlopen(url,timeout=30) as response:
                blob=response.read(2*1024**2+1)
                if len(blob)>2*1024**2:
                    raise RuntimeError('Source exceeds 2MiB bound')
                path.write_bytes(blob)
        records.append({'url':url,'file':name,'sha256':digest(path),'retrieved_at':datetime.now(timezone.utc).isoformat()})
    save_json(folder/'sources.json',records)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    archive_sources()
    for sub in ('images','workflows','licences','candidate-research','provenance'):
        (OUT/sub).mkdir(exist_ok=True)
    rows=[]
    for scene,spec in SCENES.items():
        for label,lora,trigger,strength in zip(LABELS,LORAS,TRIGGERS,STRENGTHS):
            png=WORK/'images'/f'{scene}-{label}.png'
            record_path=png.with_suffix('.generation.json')
            record=json.loads(record_path.read_text(encoding='utf-8'))
            graph=record['workflow']
            assert record['status']=='SUCCESS'
            assert digest(png)==record['sha256']
            assert graph['1']['inputs']['ckpt_name']=='sd_xl_base_1.0.safetensors'
            assert graph['8']['inputs']['lora_name']==lora
            assert graph['8']['inputs']['strength_model']==strength
            assert graph['8']['inputs']['strength_clip']==strength
            assert graph['2']['inputs']['clip']==graph['3']['inputs']['clip']==['8',1]
            assert graph['5']['inputs']['model']==['8',0]
            assert graph['5']['inputs']['seed']==spec['seed']
            assert (graph['5']['inputs']['cfg'],graph['5']['inputs']['steps'],graph['5']['inputs']['sampler_name'],graph['5']['inputs']['scheduler'])==(7.0,28,'dpmpp_2m','karras')
            assert graph['3']['inputs']['text']==NEGATIVE
            assert graph['2']['inputs']['text']==f'{trigger}, {STYLE}. {spec["description"]}'
            with Image.open(png) as image:
                assert image.size==(768,1344)
                assert json.loads(image.info['prompt'])==graph
                stddev=ImageStat.Stat(image.convert('L')).stddev[0]
                assert stddev>8
            save_json(OUT/'workflows'/f'{scene}-{label}.api.json',graph)
            shutil.copy2(png,OUT/'images'/png.name)
            shutil.copy2(record_path,OUT/'images'/record_path.name)
            rows.append({'scene':scene,'variant':label,'seed':spec['seed'],'width':768,'height':1344,
                'checkpoint':'sd_xl_base_1.0.safetensors','lora':lora,'trigger':trigger,
                'strength_model':strength,'strength_clip':strength,'cfg':7,'steps':28,
                'sampler':'dpmpp_2m','scheduler':'karras','seconds':record['seconds'],
                'sha256':record['sha256'],'prompt_id':record['prompt_id'],'technical_status':'SUCCESS',
                'artistic_status':'NOT_ACCEPTED','image':f'images/{png.name}',
                'workflow':f'workflows/{scene}-{label}.api.json','luminance_stddev':stddev})
    for name in ('comparison-ABC-full.png','comparison-ABC-preview.jpg','comparison-full.png','comparison-preview.jpg'):
        shutil.copy2(WORK/name,OUT/name)
    # Native resolution per-scene rows are easier to inspect than a downscaled six-panel sheet.
    for scene in SCENES:
        sheet=Image.new('RGB',(2304,1392),'#202020')
        draw=ImageDraw.Draw(sheet)
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25)
        for col,label in enumerate(LABELS):
            draw.text((col*768+12,10),f'{label} | seed {SCENES[scene]["seed"]}',font=font,fill='white')
            with Image.open(WORK/'images'/f'{scene}-{label}.png') as image:
                sheet.paste(image.convert('RGB'),(col*768,48))
        sheet.save(OUT/f'comparison-{scene}-full.png')
    shutil.copytree(WORK/'licences',OUT/'licences',dirs_exist_ok=True)
    shutil.copytree(WORK/'candidate-research',OUT/'candidate-research',dirs_exist_ok=True)
    models=[]
    for name in LORAS:
        path=ROOT/'ComfyUI/ComfyUI/models/loras'/name
        source=path.with_suffix(path.suffix+'.provenance.json')
        item=json.loads(source.read_text())
        assert path.stat().st_size==item['bytes'] and digest(path)==item['sha256']
        models.append(item)
        shutil.copy2(source,OUT/'provenance'/source.name)
    base=ROOT/'ComfyUI/ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors'
    provenance=base.with_suffix(base.suffix+'.provenance.json')
    base_record=json.loads(provenance.read_text())
    assert digest(base)==base_record['sha256']
    models.insert(0,base_record)
    shutil.copy2(provenance,OUT/'provenance'/provenance.name)
    for name in ('licence-audit.json','C-licence-audit.json','publisher-metadata.json','C-publisher-metadata.json','B-safetensors-header.json','C-safetensors-header.json'):
        shutil.copy2(WORK/name,OUT/'provenance'/name)
    before=json.loads((WORK/'protected-before.json').read_text())
    changed=[name for name,h in before.items() if not (ROOT/name).is_file() or digest(ROOT/name)!=h]
    assert not changed,changed
    preservation={'checked_at':datetime.now(timezone.utc).isoformat(),'protected_files':len(before),'changed':changed,'unchanged':True,
      'scope':'Existing pilot work directories, all pre-existing output/review and output/ready files, project language settings and V2 dossier. No video reconstruction, no production DB edit, no TTS/subtitle regeneration.'}
    save_json(WORK/'preservation-check.json',preservation)
    save_json(OUT/'preservation-check.json',preservation)
    defects={
      'A-LineAniRedmond':{
        'portrait':'Contour dessiné et aplats présents, mais expression figée. Coiffure haute/lisse malgré cheveux courts demandés, pose proche du portrait posé. Trame peu lisible. Identité visuelle du tirailleur demandé insuffisamment maîtrisée.',
        'camp':'Lecture de documents identifiable, mais trois figures au lieu de deux, mains/pieds peu définis, habits et couvre-chefs non vérifiés. Bâtiment de planches/toile et sol pierreux au lieu des matériaux/sable demandés. Texture proche d’une gravure/illustration imprimée.'},
      'B-MangaInk':{
        'portrait':'Aplats noirs plus francs et personnage à cheveux courts; contour plus simple et représentation demandée mieux suivie. Pose encore frontale et statique, faible tension émotionnelle, fond de pierres au lieu du mur enduit, trame surtout granuleuse plutôt que points manga réguliers.',
        'camp':'Deux personnages lisant un document, encrage sombre; pas d’apparence de photographie de studio. Résultat cependant très proche d’A, détail des visages/mains faible, document et costumes génériques. Décor ne permet pas de certifier Thiaroye1944; aspect livre illustré/gravure toujours présent.'},
      'C-BoldLineManga':{
        'portrait':'Trait beaucoup plus épais mais perte du sujet demandé: longue chevelure, pose et vêtement différents. Détail facial et anatomie simplifiés; fond gris, pas de trame de points satisfaisante. Candidat écarté.',
        'camp':'La scène de camp et le document disparaissent au profit d’un cadrage serré de personnages se tenant. Cheveux longs et chapeau, contours simplifiés, fond crème malgré palette neutre demandée. Candidat écarté.'}}
    candidates=[
      {'model':'jianzongwu/DiffSensei','kind':'Checkpoint spécialisé manga + pipeline custom','decision':'NOT_INSTALLED',
       'reason':'Documentation officielle: variante sans MLLM annoncée sur RTX4090 24GB pour petits/moyens panneaux. Pas de workflow natif ComfyUI 8GB vérifié; ne pas confondre cela avec une preuve d’impossibilité absolue.','source':'https://github.com/jianzongwu/DiffSensei'},
      {'model':'fumeisama/drawatoon-v1','kind':'Checkpoint manga/PixArt modifié','decision':'NOT_INSTALLED',
       'reason':'README réduit à TODO et aucun fichier LICENSE dans la liste publiée consultée; autorisation d’usage non établie.','source':'https://huggingface.co/fumeisama/drawatoon-v1'},
      {'model':'aipicasso/manga-diffusion-poc','kind':'Checkpoint manga SD2','decision':'NOT_INSTALLED',
       'reason':'Licence Mitsua et fiche anglaise autorisent le commercial avec transparence IA. Mais la fiche japonaise classe les vidéos monétisées parmi les usages non envisagés: indication divergente, pas une interdiction commerciale affirmée ici. Non retenu avant clarification pour l’usage futur envisagé.','source':'https://huggingface.co/aipicasso/manga-diffusion-poc'},
      {'model':'alvdansen/BandW-Manga','kind':'LoRA SDXL spécialisé','decision':'NOT_INSTALLED',
       'reason':'Fiche: diffusion pour recherche seulement, contacter auteur pour usage commercial. Le tag OpenRAIL-M ne suffit pas à lever cette restriction explicite.','source':'https://huggingface.co/alvdansen/BandW-Manga'}]
    report={'created_at':datetime.now(timezone.utc).isoformat(),'status':'COMPARISON_COMPLETE_AWAITING_OWNER_REVIEW',
      'technical_verdict':'6/6 actual generations SUCCESS; 768x1344; PNG embedded graph equals delivered workflow; actual model SHA verified',
      'artistic_verdict':'Aucune variante retenue pour images définitives. B est la piste la moins éloignée parmi ces essais, sans conformité seinen établie. C est écarté.',
      'owner_acceptance':False,'production_changed':False,'runs':rows,'models':models,
      'licences':{'A':'CreativeML OpenRAIL-M, déclaration auteur ArtificialGuyBR; source CreativeML archivée',
          'B':'OpenRAIL++ déclaré par strkyyy au commit856ecac6ef6203faf52116dfc42c36f02bd93cbc',
          'C':'OpenRAIL++ déclaré par Chan-Y au commitebc3b45377f790c0e24d14289d32a92aba6d6d49',
          'base':'CreativeML OpenRAIL++-M, StabilityAI',
          'limits':'Éditeurs, commits, fichiers et licences déclarées vérifiés; droits détaillés de tous jeux d’entraînement non audités. Pas de nouvelle API payante ni de modèle annoncé NSFW sélectionné.'},
      'B_architecture':'1120 tenseurs UNet LoRA, rang16, dimensions attention croisée2048; pas de tenseurs encodeur texte. CLIP85% est le paramètre de nœud mais aucune adaptation de CLIP n’est contenue dans ce fichier.',
      'C_architecture':'LoRA SDXL avec tenseurs UNet et encodeurs texte; 528 clés encodeur texte dans le fichier inspecté. Chargement réel via ComfyUI réussi sur8GB.',
      'comparison_limits':['A/B/C changent le LoRA, son déclencheur et son intensité prévue; toutes les autres entrées restent identiques par scène.',
        'Même seed ne garantit pas même cadrage ou même personnage: les adaptations modifient le débruitage.',
        'Le modèle B conseille aussi K-LMS ~25pas; cet essai conserve28pas DPM++2M/Karras afin de comparer les modèles sans changer simultanément le sampler.',
        'Aucun détail vestimentaire/architectural n’est présenté comme archive vérifiée. Les scènes sont des reconstitutions fictives et non des preuves historiques.',
        'Pas de poursuite des essais ni de génération définitive avant avis utilisateur.'],
      'defects':defects,'checkpoint_research':candidates,'preservation':preservation,
      'next_step':'Le propriétaire examine les planches et valide une direction ou rejette les trois. Arrêt des générations jusqu’à sa réponse.'}
    save_json(OUT/'REPORT.json',report)
    lines=['# Comparaison artistique manga A / B / C','',
      '**Statut : essais terminés — aucune image définitive validée.**','',report['artistic_verdict'],'',
      '[Planche intégrale 2304×2784](comparison-ABC-full.png) · [Portraits 2304×1392](comparison-portrait-full.png) · [Camp 2304×1392](comparison-camp-full.png)','',
      '## Protocole et résultats techniques','',
      'Six PNG réellement générés sur RTX4060 Laptop8GB, sans reconstruction vidéo. Chaque PNG original fait768×1344. Les planches à résolution native ne retouchent pas les dessins. La palette crème de C est conservée pour montrer le défaut.','',
      'Checkpoint commun : SDXL Base1.0. CFG7, DPM++2M, Karras,28pas, batch1. Seed portrait19441204; seed camp19441201. Prompts de scène et négatifs identiques entre variantes; seuls LoRA/déclencheur/intensité changent.','',
      '| Variante | LoRA | Déclencheur | Modèle/CLIP | Licence déclarée |','|---|---|---|---|---|',
      '| A | LineAniRedmondV2 | LineAniAF | 1,0 / 1,0 | CreativeML OpenRAIL-M |',
      '| B | manga-ink-screentone | m4ng41nk | 0,85 / 0,85 | OpenRAIL++ |',
      '| C | BoldLine-Manga | in the style of TOK | 1,0 / 1,0 | OpenRAIL++ |','',
      'B ne contient pas de tenseurs CLIP: le réglage0,85 est présent dans le nœud mais agit uniquement sur les poids UNet disponibles. C contient aussi des poids des encodeurs texte. Les graphes API effectifs sont livrés dans workflows/.','',
      '| Scène | Variante | Durée réelle | Image PNG | Workflow API |','|---|---|---:|---|---|']
    for r in rows:
        lines.append(f'| {r["scene"]} | {r["variant"]} | {r["seconds"]}s | [PNG]({r["image"]}) | [JSON]({r["workflow"]}) |')
    lines += ['','## Inspection visuelle réelle','']
    for label,observations in defects.items():
        lines += [f'### {label}','', '**Portrait :** '+observations['portrait'],'','**Camp :** '+observations['camp'],'']
    lines += ['## Compatibilité et licences','',
      'Les poids B et C sont téléchargés depuis les dépôts indiqués, à commits figés, après lecture des fiches. Taille et SHA256 comparés aux LFS publiés; en-têtes safetensors inspectés; modèle SDXL et trois LoRA rehashés avant livraison. Le succès du calcul sur8GB démontre la faisabilité de ces deux compositions, pas une qualité artistique.','',
      'Fiches, texte des licences, métadonnées et empreintes sont dans licences/ et provenance/. Aucun supplément de licence non commercial n’apparaît dans les fiches B/C. Les restrictions OpenRAIL d’usage, de transparence et de redistribution restent applicables selon les modèles. L’origine précise de chaque donnée d’entraînement n’est pas prouvée par ces seules déclarations.','',
      '- [B — strkyyy/manga-ink-screentone](https://huggingface.co/strkyyy/manga-ink-screentone/tree/856ecac6ef6203faf52116dfc42c36f02bd93cbc)',
      '- [C — Chan-Y/BoldLine-Manga](https://huggingface.co/Chan-Y/BoldLine-Manga/tree/ebc3b45377f790c0e24d14289d32a92aba6d6d49)',
      '- [A — ArtificialGuyBR/LineAniRedmondV2](https://huggingface.co/artificialguybr/LineAniRedmond-LinearMangaSDXL-V2)',
      '- [Licence base SDXL](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/main/LICENSE.md)','',
      '## Recherche d’un checkpoint réellement spécialisé','',
      'Cette recherche a été effectuée après l’insuffisance de B. Aucun checkpoint ci-dessous n’est installé:','']
    for candidate in candidates:
        lines += [f'- [{candidate["model"]}]({candidate["source"]}) : '+candidate['reason']]
    lines += ['','C est donc un troisième LoRA spécialisé, pas un checkpoint complet présenté comme testé. Pas de téléchargement massif spéculatif ni d’installation d’un candidat de licence incertaine.','',
      '## Limites du comparatif','']+[f'- {x}' for x in report['comparison_limits']]
    lines += ['','## Conservation de l’existant','',f'{len(before)} fichiers préexistants contrôlés par SHA256: aucune modification. Narration EN, sous-titres FR, vidéos et médias antérieurs conservés. Aucune modification des paramètres de production ou des permissions Codex. Aucun appel TTS/FFmpeg de production ni upload.','',
      '## Reproduire les seuls essais','',
      '```powershell\nSet-Location C:\\TikTokHistoryFactory\n.\\.venv\\Scripts\\python.exe scripts/compare_manga_ink.py\n.\\.venv\\Scripts\\python.exe scripts/compare_manga_candidate_c.py\n```','',
      'Les fichiers identiques sont repris par empreinte. Ne pas relancer pour créer des images définitives avant validation du propriétaire.','',
      '**Arrêt demandé respecté : les six essais sont livrés. Attente de votre validation de la direction artistique.**']
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    cards=[]
    for scene in SCENES:
        cards.append(f'<h2>{html.escape(scene)}</h2><div class="grid">')
        for label in LABELS:
            image=f'images/{scene}-{label}.png'
            cards.append(f'<figure><figcaption>{html.escape(label)} — seed {SCENES[scene]["seed"]}</figcaption><a href="{image}" target="_blank"><img src="{image}" alt="{html.escape(scene+" "+label)}"></a><a href="workflows/{scene}-{label}.api.json">Workflow effectif</a></figure>')
        cards.append('</div>')
    (OUT/'INDEX.html').write_text('<!doctype html><html lang="fr"><meta charset="utf-8"><title>Comparaison manga A/B/C</title><style>body{background:#161616;color:#eee;font:17px Arial;margin:28px} .grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}figure{margin:0}img{width:100%;height:auto}a{color:#9bd7ff}figcaption{margin-bottom:12px}p{max-width:80ch}@media(max-width:700px){.grid{grid-template-columns:1fr}}</style><h1>Essais manga A / B / C</h1><p>Aucune validation artistique automatique. Cliquez sur les images pour les ouvrir à leur résolution native.</p><p><a href="REPORT.md">Rapport et défauts observés</a> · <a href="comparison-ABC-full.png">Planche intégrale</a></p>'+''.join(cards)+'</html>',encoding='utf-8')
    scripts=OUT/'scripts'
    scripts.mkdir(exist_ok=True)
    for name in ('compare_manga_ink.py','compare_manga_candidate_c.py','deliver_manga_comparison.py'):
        shutil.copy2(ROOT/'scripts'/name,scripts/name)
    save_json(OUT/'artifact_hashes.json',{str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'})
    save_json(WORK/'delivery.json',{'output':str(OUT),'report':str(OUT/'REPORT.md'),'status':report['status'],'images':6,'preservation':preservation})
    print('COMPARISON DELIVERED:',OUT,flush=True)
    print('6 real images; graphs/weights SHA verified; protected files unchanged:',len(before),flush=True)


if __name__=='__main__':
    main()
