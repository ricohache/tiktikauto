"""Deliver only the approved-scope specialist trials and future format contract."""
import json
import shutil
import sys
import urllib.request
from datetime import datetime,timezone
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageStat

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from test_specialist_manga import WORK,MODEL,REPO,REV,FILENAME,SIZE,SHA,PROMPTS,NEGATIVE,digest,save_json
from tiktok_history_factory.config.production import load_production_format

OUT=ROOT/'output/review/specialist-manga-emi2-20261019'


def main():
    review_path=WORK/'visual-review.json'
    if not review_path.exists():
        raise RuntimeError('Actual agent visual inspection must be recorded before delivery')
    review=json.loads(review_path.read_text(encoding='utf-8'))
    trial=json.loads((WORK/'trial-results.json').read_text(encoding='utf-8'))
    if len(trial['results'])!=2 or any(r['status']!='SUCCESS' for r in trial['results']):
        raise RuntimeError('Two actual successful compositions are required for this delivery mode')
    OUT.mkdir(parents=True,exist_ok=True)
    for folder in ('images','workflows','sources','provenance','reference-B'):
        (OUT/folder).mkdir(exist_ok=True)
    rows=[]
    reference=ROOT/'work/art-comparison-20261019-manga-ink/images'
    for result in trial['results']:
        scene=result['scene']
        image=WORK/'images'/f'{scene}-Emi2.png'
        graph=result['workflow']
        assert digest(image)==result['sha256']
        assert graph['1']['inputs']['ckpt_name']==FILENAME
        assert not any(n['class_type']=='LoraLoader' for n in graph.values())
        assert graph['2']['inputs']['clip']==graph['3']['inputs']['clip']==['1',1]
        assert graph['5']['inputs']['model']==['1',0]
        assert graph['5']['inputs']['seed']==PROMPTS[scene]['seed']
        assert graph['5']['inputs']['steps']==20
        assert graph['5']['inputs']['sampler_name']=='euler_ancestral'
        assert graph['5']['inputs']['scheduler']=='normal'
        assert graph['5']['inputs']['cfg']==7.5
        assert graph['2']['inputs']['text']==PROMPTS[scene]['text']
        assert graph['3']['inputs']['text']==NEGATIVE
        with Image.open(image) as png:
            assert png.size==(768,1344)
            assert json.loads(png.info['prompt'])==graph
            assert ImageStat.Stat(png.convert('L')).stddev[0]>8
        shutil.copy2(image,OUT/'images'/image.name)
        shutil.copy2(image.with_suffix('.generation.json'),OUT/'images'/image.with_suffix('.generation.json').name)
        save_json(OUT/'workflows'/f'{scene}-Emi2.api.json',graph)
        ref=reference/f'{scene}-B-MangaInk.png'
        shutil.copy2(ref,OUT/'reference-B'/ref.name)
        shutil.copy2(ref.with_suffix('.generation.json'),OUT/'reference-B'/ref.with_suffix('.generation.json').name)
        samples=[]
        for item in result['telemetry']:
            try:
                samples.append([float(x.strip()) for x in item['gpu'].split(',')])
            except (ValueError,KeyError):
                pass
        rows.append({'scene':scene,'seed':PROMPTS[scene]['seed'],'resolution':[768,1344],
            'seconds':result['seconds'],'prompt_id':result['prompt_id'],'sha256':result['sha256'],
            'peak_sampled_gpu_memory_mib':max((s[0] for s in samples),default=None),
            'max_sampled_gpu_temperature_c':max((s[3] for s in samples),default=None),
            'gpu_samples':len(samples),'ram_free_after':result['system_after']['system']['ram_free']})
    assert MODEL.stat().st_size==SIZE and digest(MODEL)==SHA
    provenance=MODEL.with_suffix(MODEL.suffix+'.provenance.json')
    shutil.copy2(provenance,OUT/'provenance'/provenance.name)
    shutil.copytree(WORK/'sources',OUT/'sources',dirs_exist_ok=True)
    for name in ('publisher-metadata.json','safetensors-header.json','preflight-and-licence-audit.json','system-before-trials.json','visual-review.json','trial-results.json'):
        shutil.copy2(WORK/name,OUT/'provenance'/name)
    profile=load_production_format()
    save_json(OUT/'production-format-90s.json',profile.model_dump())
    save_json(OUT/'production-writer-brief.json',profile.writer_brief())
    save_json(OUT/'production-format-90s.schema.json',profile.model_json_schema())
    before=json.loads((WORK/'protected-before.json').read_text())
    changed=[name for name,h in before.items() if not (ROOT/name).is_file() or digest(ROOT/name)!=h]
    assert not changed,changed
    preservation={'checked_at':datetime.now(timezone.utc).isoformat(),'protected_files':len(before),'changed':[],
        'unchanged':True,'scope':'All pre-existing pilot media/manifests, review/ready output files, .env/.env.example, current settings and pilot dossier. New files only; new checkpoint and future profile added separately.'}
    save_json(OUT/'preservation-check.json',preservation)
    save_json(WORK/'preservation-check.json',preservation)
    # B is reference only. Prompts and sampler have deliberately been adapted to Emi2.
    sheet=Image.new('RGB',(1536,2784),'#202020')
    draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25)
    for row,scene in enumerate(PROMPTS):
        for col,label,path in (
            (0,'B - REFERENCE ONLY',OUT/'reference-B'/f'{scene}-B-MangaInk.png'),
            (1,'EMI 2 - SPECIALIZED CHECKPOINT',OUT/'images'/f'{scene}-Emi2.png')):
            x,y=col*768,row*1392
            draw.text((x+12,y+10),f'{scene} | {label}',font=font,fill='white')
            with Image.open(path) as image:
                sheet.paste(image.convert('RGB'),(x,y+48))
    sheet.save(OUT/'comparison-full.png')
    sheet.resize((768,1392)).save(OUT/'comparison-preview.jpg',quality=95)
    new=Image.new('RGB',(1536,1392),'#202020')
    draw=ImageDraw.Draw(new)
    for index,scene in enumerate(PROMPTS):
        draw.text((index*768+12,10),f'Emi 2 | {scene} | seed {PROMPTS[scene]["seed"]}',font=font,fill='white')
        with Image.open(OUT/'images'/f'{scene}-Emi2.png') as image:
            new.paste(image.convert('RGB'),(index*768,48))
    new.save(OUT/'new-trials-native.png')
    report={'created_at':datetime.now(timezone.utc).isoformat(),'status':'TRIAL_COMPLETE_AWAITING_STYLE_VALIDATION',
        'technical_status':'SUCCESS_TWO_REAL_IMAGES_8GB_NATIVE_COMFYUI',
        'artistic_status':review['overall_status'],'owner_approved':False,
        'model':{'repo':REPO,'revision':REV,'filename':FILENAME,'bytes':SIZE,'sha256':SHA,
            'kind':'Complete illustration-specialized SDXL-family checkpoint; no style LoRA and not original general SDXL Base weights',
            'licence':'CreativeML OpenRAIL++-M; commercial use included in publisher intended uses'},
        'model_audit':json.loads((WORK/'preflight-and-licence-audit.json').read_text()),
        'runs':rows,'visual_review':review,'preservation':preservation,
        'production_90s':profile.writer_brief(),
        'tests':{'production_format_unit_tests':3,'production_format_exit_code':0,
            'artifact_checks':'Actual PNG/SHA/embedded workflow; native checkpoint path; no LoraLoader; seeds/steps/sampling/CFG; model SHA; prior files unchanged',
            'video_test':'NOT_RERUN: video/audio/subtitle files preserved, no video generated'},
        'alternatives':[
            {'model':'cagliostrolab/animagine-xl-4.0','decision':'NOT_DOWNLOADED',
             'reason':'Publisher documents safe/sensitive/nsfw/explicit rating conditioning. SFW tags/negatives and downstream classifier+review can reduce risk, not make weights SFW-only. Requires explicit user decision before relaxing current no-NSFW-model rule.',
             'source':'https://huggingface.co/cagliostrolab/animagine-xl-4.0'},
            {'model':'aipicasso/emi-2-5','decision':'NOT_DOWNLOADED',
             'reason':'Same family, uses CosmicMan-SDXL in training lineage. One Emi2 checkpoint chosen to evaluate drawing-oriented engine without downloading several weights. Not declared incompatible; not benchmarked.',
             'source':'https://huggingface.co/aipicasso/emi-2-5'},
            {'model':'aipicasso/emi','decision':'NOT_DOWNLOADED','reason':'Older checkpoint, gated access requiring contact-data sharing; ungated Emi2 selected instead.',
             'source':'https://huggingface.co/aipicasso/emi'},
            {'model':'jianzongwu/DiffSensei','decision':'NOT_DOWNLOADED','reason':'Official reduced-memory workflow documented with24GB GPU; custom pipeline, no verified native8GB workflow.',
             'source':'https://github.com/jianzongwu/DiffSensei'},
            {'model':'fumeisama/drawatoon-v1','decision':'NOT_DOWNLOADED','reason':'No usable licence established from published README/files.',
             'source':'https://huggingface.co/fumeisama/drawatoon-v1'}],
        'comparison_limits':['B is an already-rejected reference, not a newly regenerated baseline.',
            'Scene intent and seeds retained, but positive/negative prompts, sampler, steps and CFG adapted to Emi2. This is a strategy comparison, not a single-variable causal A/B test.',
            'Identical seeds do not lock composition or character identity across different weights and conditioning.',
            'GPU memory/temperature are whole-GPU sampled values, not continuous peaks.',
            'Emi2 is illustration-oriented, not advertised as an adult checkpoint; no SFW-only guarantee or independently audited training set is claimed.',
            'No historical wardrobe/building detail is certified by image generation alone. Character is a fictional composite, no portrait of an identified victim.',
            'New90s contract is planning/validation only; the90s production compositor/story pipeline is not claimed operational or activated.'],
        'next_action':'Owner reviews these two compositions and accepts/rejects the direction. No further image or video production until that decision.'}
    save_json(OUT/'REPORT.json',report)
    lines=['# Nouveau moteur spécialisé — Emi 2','',
        '**Technique : deux générations réelles réussies sur RTX4060 Laptop8Go.**',
        '**Artistique : '+review['overall_status']+'. Aucune validation du propriétaire enregistrée.**','',
        '[Planche comparative native](comparison-full.png) · [Nouveaux essais natifs](new-trials-native.png)','',
        '## Choix du moteur et préflight','',
        f'[Emi2 — dépôt officiel AI Picasso](https://huggingface.co/{REPO}/tree/{REV}) : checkpoint complet spécialisé illustration japonaise, {SIZE} octets (6,46Gio), sans LoRA de style. Un seul nouveau checkpoint téléchargé; les modèles existants sont conservés.',
        '',f'Commit : `{REV}`. SHA256 : `{SHA}`. Téléchargement reprenable et vérifié. Fichier : `{MODEL}`.','',
        'La fiche décrit les usages ComfyUI standards et commerciaux, sous CreativeML OpenRAIL++-M. La licence standard est archivée, ainsi que la fiche et les configurations du dépôt. Les restrictions contre usages illégaux/trompeurs/dommageables restent applicables. Les déclarations de l’éditeur sur ses données ne sont pas présentées comme un audit indépendant de chaque image.','',
        'Emi2 n’est pas annoncé comme checkpoint adulte. Il n’est cependant pas certifié incapable de contenu NSFW. Cet essai impose adultes entièrement vêtus, exclusions de nudité/sexualité/gore et inspection des deux résultats. Les prompts négatifs ne sont pas un filtre de sécurité garanti. Aucun remplacement par un modèle explicitement NSFW n’a été autorisé.','',
        '## Réglages et compatibilité réelle','',
        'ComfyUI natif : CheckpointLoaderSimple → CLIPTextEncode → KSampler → VAEDecode → SaveImage. Aucun LoraLoader ni nœud tiers ajouté. Le checkpoint complet téléchargé contient des tenseursF16 (inspection réelle), bien que l’exemple Diffusers de la fiche utiliseBF16. Gestion mémoire/offload native.','',
        'La fiche Emi2 emploie des tags de type Waifu Diffusion et donne un exemple Euler ancestral20pas. Le JSON scheduler du dépôt nomme EulerDiscrete: cette différence est explicitée dans l’audit. Le test suit l’exemple Euler ancestral,20pas, CFG7,5, scheduler normal, batch1,768×1344. La fiche ne fixe pas de résolution unique; cette taille reste dans le budget SDXL~1Mpix déjà testé et correspond au ratio du pilote.','',
        'Pas d’embedding négatif, LoRA de correction des mains, FreeU ou fusion avec un modèle photo lors de cette évaluation du checkpoint seul. Ces recommandations optionnelles de l’éditeur ne sont pas présentées comme installées.','',
        '| Scène | Seed | Temps réel | VRAM observée maximale | PNG original | Workflow effectif |',
        '|---|---:|---:|---:|---|---|']
    for r in rows:
        s=r['scene']
        lines.append(f'| {s} | {r["seed"]} | {r["seconds"]}s | {r["peak_sampled_gpu_memory_mib"]}MiB | [PNG](images/{s}-Emi2.png) | [JSON](workflows/{s}-Emi2.api.json) |')
    lines+=['','## Évaluation visuelle réelle','']
    for scene in PROMPTS:
        lines+=['### '+scene,'',review[scene],'']
    lines+=['**Continuité :** '+review['continuity'],'','**Comparaison à B :** '+review['comparison_to_B'],'',
        '## Modèles non téléchargés et concessions éventuelles','']
    for alt in report['alternatives']:
        lines+=['- ['+alt['model']+']('+alt['source']+') : '+alt['reason']]
    lines+=['','Si les nouveaux essais sont refusés, les suites à décider sont : poursuivre la recherche d’un checkpoint spécialisé sans objectif NSFW déclaré, ou autoriser explicitement un checkpoint anime capable deNSFW dans un workflow strictementSFW avec contrôles additionnels. Cette seconde concession n’est pas présumée acquise.','',
        '## Format narratif futur90s','',
        'Profil version3 enregistré et validé : introduction0–15s, développement15–75s, conclusion75–90s; audioEN, sous-titresFR, aucun accélérateur vocal, style/publication/planification désactivés. Budgets indicatifs :30–36,120–145,30–36 mots anglais. Trois tests du nouveau contrat réussis (code0).','',
        'Cette étape n’implémente ni ne lance une vidéo90s. Le scénario, l’audio, les sous-titres et les critères du pilote technique court restent en place. Le moteur de montage90s et ses futurs tests seront à adapter après acceptation du style et du contenu historique.','',
        '## Préservation et preuves','',f'{len(before)} fichiers préexistants contrôlés par SHA256 : aucun modifié. Références A/B/C conservées, B uniquement comparative, C écartée. Aucun rendu vidéo, aucune TTS, aucune publication, aucun scheduler lancé. Aucune configuration Codex/tiktoknet modifiée.','',
        'Les graphes intégrés aux PNG sont égaux aux JSON livrés. Modèle, PNG, paramètres et fichiers protégés contrôlés sur disque. Journal de télémétrie et statistiques ComfyUI dans provenance/.','',
        '## Limites de comparaison','']+['- '+v for v in report['comparison_limits']]
    lines+=['','**Arrêt : attente de votre validation du style avant les images définitives.**']
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    (OUT/'INDEX.md').write_text('# Essais spécialisés Emi2\n\n[Rapport](REPORT.md) · [Planche comparée àB](comparison-full.png) · [Deux nouveaux essais](new-trials-native.png)\n\n[Portrait original](images/portrait-Emi2.png) · [Camp original](images/camp-Emi2.png)\n\nAucune validation artistique automatique. Pas de vidéo régénérée.\n',encoding='utf-8')
    (OUT/'scripts').mkdir(exist_ok=True)
    for name in ('test_specialist_manga.py','deliver_specialist_manga.py'):
        shutil.copy2(ROOT/'scripts'/name,OUT/'scripts'/name)
    save_json(OUT/'artifact_hashes.json',{str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'})
    print('SPECIALIST TRIAL DELIVERED',OUT,'TECHNICAL SUCCESS; STYLE AWAITING VALIDATION; protected',len(before),flush=True)


if __name__=='__main__':
    main()
