"""Package real V2 evidence and schema-validated final report; no publishing."""
import csv
import json
import platform
import re
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field
from PIL import Image, ImageDraw, ImageOps
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tiktok_history_factory.pipeline.checkpoints import digest

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'work/pilot-thiaroye-1944-v2'
REPORTS=ROOT/'reports'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


class Section(BaseModel):
    number:int
    title:str
    text:str


class Report(BaseModel):
    schema_version:Literal['2.0']
    created_at:str
    verdict:Literal['PARTIEL']
    sections:list[Section]=Field(min_length=20,max_length=20)
    components:list[dict]
    changes:list[dict]
    tests:dict
    pilot:dict
    wan:dict
    next_action:str


def main():
    now=datetime.now(timezone.utc).isoformat()
    manifest=read(WORK/'manifest.json')
    qc=read(WORK/'qc.json')
    voice=read(WORK/'audio/voice-manifest.json')
    dossier=read(ROOT/'data/subjects/thiaroye-1944-v2.json')
    wan=read(WORK/'wan/clip.wan.json')
    exported=Path(manifest['output_path']).parent
    shutil.copytree(WORK/'research', exported/'research', dirs_exist_ok=True)
    licences=exported/'licences'
    licences.mkdir(exist_ok=True)
    for source in (ROOT/'assets/licenses').glob('*'):
        if source.is_file() and source.suffix in ('.md','.txt','.json'):
            shutil.copy2(source, licences/source.name)
    tests=read(REPORTS/'tests-v2.json')
    log=(REPORTS/'tests-v2.log').read_text(encoding='utf-8-sig')
    tests['count']=int(re.search(r'Ran (\d+) tests',log).group(1))
    if tests['exit_code'] or tests['count']<50:
        raise RuntimeError('Final tests not successful')
    commands=[
      {'command':r'.\.venv\Scripts\python.exe scripts/acquire_v2_assets.py','exit_code':0,'scope':'REAL: pinned weights and publisher hashes'},
      {'command':r'.\.venv\Scripts\python.exe scripts/compare_v2.py','exit_code':0,'scope':'REAL: controlled GPU base/LoRA variants and two English voice samples'},
      {'command':r'.\.venv\Scripts\python.exe -m tiktok_history_factory pilot --resume --try-wan --dossier data/subjects/thiaroye-1944-v2.json','exit_code':0,'scope':'REAL: revision-3-wan-attempt'},
      {'command':r'.\.venv\Scripts\python.exe -m tiktok_history_factory pilot --dossier data/subjects/thiaroye-1944-v2.json','exit_code':0,'scope':'REAL: revision-3, matched FFmpeg-only alternative'},
      {'command':r'& C:\TikTokHistoryFactory\scripts\main.ps1 -Mode Resume -JobId 5','cwd':'C:\\','exit_code':0,'scope':'REAL: seven stages resumed, no generation'},
      {'command':r'.\.venv\Scripts\python.exe -m tiktok_history_factory doctor','exit_code':0,'scope':'Seven health checks OK; real inference proved separately'},
      {'command':r'.\.venv\Scripts\python.exe -m compileall -q tiktok_history_factory tests','exit_code':0,'scope':'STATIC'},
    ]
    tests['other_commands']=commands
    tests['powershell']=read(REPORTS/'powershell-v2.json')
    # Export both an immutable review package and a ready local import copy.
    ready=ROOT/'output/ready/5_v2_final.mp4'
    ready.parent.mkdir(parents=True,exist_ok=True)
    if ready.exists() and digest(ready)!=digest(manifest['output_path']):
        raise RuntimeError('Different ready video exists; choose a new revision')
    shutil.copy2(manifest['output_path'],ready)
    for name in ('manifest.json','qc.json','cover.jpg','caption.txt','sources.md','subtitles.srt','subtitles.ass','narration-en.wav'):
        shutil.copy2(exported/name,ready.parent/('5_v2_'+name))
    frames=exported/'review-frames'
    frames.mkdir(exist_ok=True)
    ffmpeg=str(ROOT/'ffmpeg/bin/ffmpeg.exe')
    sheet=Image.new('RGB',(1080,1920),'white')
    for index,item in enumerate(voice['utterances']):
        path=frames/f'caption-{index+1:02d}.png'
        t=(item['start_seconds']+item['end_seconds'])/2
        subprocess.run([ffmpeg,'-v','error','-ss',str(t),'-i',manifest['output_path'],'-frames:v','1','-y',str(path)],check=True,capture_output=True)
        with Image.open(path) as image:
            sheet.paste(image.convert('RGB').resize((270,480)),((index%4)*270,(index//4)*960))
    # Two rows, without implying blank space belongs to the video.
    compact=Image.new('RGB',(1080,960),'white')
    for index in range(8):
        with Image.open(frames/f'caption-{index+1:02d}.png') as image:
            compact.paste(image.convert('RGB').resize((270,480)),((index%4)*270,(index//4)*480))
    compact.save(exported/'subtitles-review.jpg',quality=94)
    old=ROOT/'output/review/thiaroye-1944-pilote/revision-7-wan-attempt/contact-sheet.jpg'
    new=exported/'contact-sheet.jpg'
    comparison=Image.new('RGB',(1152,1160),'#202020')
    draw=ImageDraw.Draw(comparison)
    for y,path,label in ((0,old,'V1 DRAFT_REJECTED'),(580,new,'V2 CANDIDATE - OWNER REVIEW PENDING')):
        draw.text((10,y+6),label,fill='white')
        with Image.open(path) as image:
            comparison.paste(ImageOps.fit(image.convert('RGB'),(1152,554)),(0,y+24))
    comparison.save(exported/'old-new-comparison.jpg',quality=94)
    review={
      'status':'CANDIDATE_NOT_OWNER_ACCEPTED','reviewed_at':now,
      'comparison':'work/v2-comparison-style-first/comparison.jpg',
      'selection':'SDXL Base + LineAniRedmond V2, strength 1.0; seed 19441204 portrait comparison',
      'rejected':['V1 sepia/engraving and French accelerated narration','V2 comparison 1 photographic portraits','V2 scene-01-v2: photographic tree and unrequested figures','V2 scene-03-v2: wooden porch too suggestive of Japanese scenery'],
      'final_observations':['Black/white ink and solid shadows; no sepia','African composite character in scenes 2/4 has broadly matching face, hair and shirt; exact identity consistency not guaranteed','Cup is symbolic; no claim it is an archival object','Scene 1 is a generic drawn building, not a verified reconstruction of Thiaroye camp','No graphic violence, fake orders or casualty number','Source PNGs and generated Wan midpoint inspected visually'],
      'remaining':['Owner must judge whether this style is sufficiently Japanese seinen','Garment and architectural details are approximations, not archive-verified','Voice samples and final WAV supplied; agent cannot certify listening quality or proper-name pronunciation by ear'],
      'wan':'One V2 clip generated and decoded; reference composition retained at inspected midpoint; motion subtle'}
    (exported/'editorial-review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
    telemetry=[]
    for sample in wan.get('telemetry',[]):
        try:
            values=[float(x.strip()) for x in sample['gpu'].split(',')]
            telemetry.append(values)
        except (ValueError,KeyError):
            pass
    benchmark={'status':wan['status'],'seconds':wan.get('seconds'),'width':wan['width'],'height':wan['height'],
      'frames':wan['frames'],'fps':wan['fps'],'samples':len(telemetry),
      'peak_observed_gpu_memory_mib':max((v[0] for v in telemetry),default=None),
      'max_observed_temperature_c':max((v[3] for v in telemetry),default=None),
      'scope':'Whole-GPU samples every ~4 seconds; not a continuous allocation peak or electricity meter',
      'fallback':str(exported/'pilot.mp4'),
      'wan_alternative':str(exported.parent/'revision-3-wan-attempt/pilot.mp4'),
      'source':str(WORK/'wan/clip.wan.json')}
    (REPORTS/'WAN_BENCHMARK_V2.json').write_text(json.dumps(benchmark,indent=2),encoding='utf-8')
    (REPORTS/'WAN_BENCHMARK_V2.md').write_text('# Wan V2 — essai réel unique\n\n'+json.dumps(benchmark,ensure_ascii=False,indent=2)+'\n\nUn clip 2,125 s, 480×832, 17 images à 8 fps. FFmpeg remplit la durée du plan par gel final ; ce ne sont pas 6 s de mouvement Wan. Le montage FFmpeg seul utilise les mêmes sources et durées.\n',encoding='utf-8')
    backups=sorted(ROOT.glob('backups/v2-before-*'))
    backup=ROOT/'backups/v2-before-20261019-115710'
    changes=[]
    candidates=[]
    for folder in ('tiktok_history_factory','scripts','tests','docs','workflows'):
        candidates += [p for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in ('.py','.ps1','.md','.json') and '__pycache__' not in p.parts]
    candidates += [ROOT/p for p in ('README.md','.env.example','pyproject.toml','requirements-lock.txt')]
    for p in candidates:
        previous=backup/p.relative_to(ROOT)
        if not previous.exists() or digest(previous)!=digest(p):
            changes.append({'file':str(p.relative_to(ROOT)), 'action':'modified' if previous.exists() else 'new_or_not_in_initial_backup',
                'sha256':digest(p), 'reason':'V2 languages, manga, QC, tests, delivery or documentation'})
    with sqlite3.connect('file:'+ (ROOT/'data/factory.db').as_posix()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        phases=[dict(r) for r in db.execute('select * from run_history where task_id=5 order by id')]
        task=dict(db.execute('select id,status,tiktok_video_id,published_at from video_tasks where id=5').fetchone())
    components=[
      {'component':'Sources/Kimi','before':'Sources and native Kimi working','change':'Claims retained; source-locked English script with reviewed French translation','test':'Cached source SHA/excerpts + actual Kimi response','result':'OK / REAL','proof':'work/pilot-thiaroye-1944-v2/research; script/llm-response.json','risk':'Human editorial review; no automatic truth proof'},
      {'component':'English voice','before':'French accelerated voice rejected','change':'Piper John, utterances, no acceleration','test':f"Actual WAV {voice['words_per_minute']} WPM; PCM verified",'result':'OK technique / revue écoute requise','proof':'narration-en.wav; voice-manifest.json','risk':'Proper names and naturalness not certified by agent listening'},
      {'component':'French captions','before':'Long whole-sentence blocks','change':'Eight translated units, <=2 lines, exact WAV boundaries','test':'Actual SRT/ASS and 8 extracted caption frames','result':'OK / REAL','proof':'subtitles.srt; subtitles.ass; subtitles-review.jpg','risk':'Reading rates vary; one unit ~18.9 chars/s, date intentionally slower'},
      {'component':'Manga','before':'Sepia engraving rejected','change':'Verified manga LoRA, two comparisons, final corrections','test':'Real PNG/graph/SHA + visual inspection','result':'PARTIAL / CANDIDATE','proof':'contact-sheet.jpg; editorial-review.json','risk':'Owner acceptance and archive-level wardrobe/building fidelity pending'},
      {'component':'Compositor','before':'Permanent AI drawtext banner','change':'Filter removed; disclosure in metadata/caption','test':'Real command log, decode and full blackdetect','result':'OK / REAL','proof':'render/ffmpeg-log.json; qc.json','risk':'Future platform rules must be checked before any publication'},
      {'component':'Wan/fallback','before':'V1 real Wan installed','change':'One new I2V test, paired FFmpeg-only export','test':f"Actual Wan {wan.get('seconds')}s; full decode",'result':'OK / REAL','proof':'reports/WAN_BENCHMARK_V2.json','risk':'Very subtle 2.125s clip; 8GB requires offload'},
      {'component':'Resume/CLI','before':'Atomic checkpoints and SQLite','change':'Bilingual inputs, visual-only dependencies, new job5','test':'Seven RESUMED stages from C:\\, exit0','result':'OK / REAL','proof':'tests-v2.log; checkpoints.json','risk':'General subject discovery and full production scheduling still incomplete'},
      {'component':'TikTok/scheduler','before':'Disabled','change':'Remain disabled','test':'Default configuration tests, SQLite no publication ID','result':'BLOQUÉ volontairement','proof':'tests-v2.log; DB job5','risk':'No account authorization or daily-production acceptance'}]
    next_action='Regarder et écouter le pilote V2 pour accepter ou préciser le style manga, la voix et la prononciation de Thiaroye.'
    texts=[
      ('Résumé exécutif','VERDICT GLOBAL = PARTIEL. Nouveau pilote réel livré, technique conforme au contrat EN/FR. Qualité artistique et diction non acceptées au nom du propriétaire. Aucun upload.'),
      ('Machine observée',f"RTX4060 Laptop 8GB, pilote596.08; RAM34029125632 octets dans system_stats; Windows {platform.version()}; Python {platform.python_version()}; ComfyUI0.41.0, torch2.14.0+cu130, Piper1.8.0, Pydantic2.13.5. Disque libre à la livraison: {shutil.disk_usage(ROOT).free/1024**3:.1f} GiB. CPU détaillé: inventaire V1 conservé, pas remesuré par CIM (accès refusé)."),
      ('État initial et sauvegardes','V1 préservé comme DRAFT_REJECTED. File ComfyUI vide et aucun .part trouvé avant travail. Inventaire processus via CIM refusé; contrôle de file et fichiers effectué. Sauvegardes V2: '+', '.join(str(p) for p in backups)+'. Backups SQLite avant chaque exécution.'),
      ('Fichiers créés/modifiés/supprimés','Inventaire et SHA dans le JSON changes. Principaux: settings, Piper, prompts, ComfyUI LoRA, compositeur, contrats Pydantic, bilingue, pilote, CLI, main.ps1, tests, docs. Dossier sujet V2 ajouté, ancien intact. Aucun fichier utilisateur supprimé. Les rapports V1 restent archivés.'),
      ('Arborescence finale','Code réutilisé sous tiktok_history_factory; sources data/subjects; travail work/pilot-thiaroye-1944-v2; livrables '+str(exported)+'; import manuel '+str(ready)+'; comparaisons work/v2-comparison*; rapports reports/*V2* et tests-v2.*.'),
      ('Modèles et licences','SDXL Base officiel existant + LineAniRedmond V2 auteur ArtificialGuyBR, commit411d5335378c13e63bf0d5376b405a39e9a869cb, LoRA170540028 octets, OpenRAIL-M. SDXL OpenRAIL++ conservé. John/Kristin: fiches LibriVox domaine public, repo MIT, John depuis Kristin entraînée de zéro. Wan Apache2 existant. Toutes provenances/tailles/SHA dans assets/licenses et .provenance.json. Pas de garantie sur les droits de chaque donnée image d’entraînement non publiée.'),
      ('Fournisseurs et budget','ComfyUI localhost8188 GPU; Piper CPU venv; Kimi cloud via Ollama localhost11434/api/chat, compte existant. Aucun paramètre global modifié. Deux voix et LoRA acquis gratuitement; Pydantic installé seulement dans venv. Commandes autorisées hors sandbox pour CDN et tests, sans changement du profil réseau.'),
      ('Pipeline réel',f"Thiaroye1944: trois sources, quatre claims, narration EN en huit unités FR appariées, quatre PNG768x1344, voix{voice['duration']:.3f}s, {voice['words_per_minute']} mots/minute sans changement de tempo. Images finales versions3/2/3/2. Wan17images480x832, FFmpeg1080x1920/30fps/H264/AAC, SRT/ASS, QC et export. Personnage fictif composite; décor et tasse illustratifs."),
      ('Tests et commandes',f"{tests['count']} tests réussis, dont mocks explicitement nommés et huit tests intégration médias réels; zéro skip final. Journal tests-v2.log. Suite lancée trop tôt pendant Wan: échec conservé tests-v2-inflight.*, puis corrigé par attente de fin, sans assouplir les tests. Permission temporaire os.replace vérifiée hors sandbox. AST PowerShell0erreur; compileall0; doctor0; reprise0; détails commandes dans JSON."),
      ('Matrice exigences','Matrice A–U conservée avec réserves générales et complétée par exigences V2, preuves et limites. DONE ne signifie pas acceptation esthétique. Publication et planification restent désactivées; automatisation de nouveaux sujets non certifiée.'),
      ('Benchmark',json.dumps(benchmark,ensure_ascii=False)+'. Historique des temps par phase dans JSON pilot.phases. CPU/RAM peak non mesurés pour toute la mission; température et VRAM Wan sont des échantillons, pas des pics continus.'),
      ('Livrables',str(exported)+' : pilot.mp4, narration-en.wav, voice-manifest.json, subtitles.srt/.ass, scenario.txt, translation-fr.txt, storyboard.json, media/PNG et graphes, sources.md, caption.txt, CREDITS, manifest, qc, contact-sheet, review-frames et comparatif ancien/nouveau. Variante Wan: '+benchmark['wan_alternative']),
      ('Coûts','Achat externe nouveau: 0€. Abonnement Ollama existant utilisé, quota restant non lu. Électricité non mesurée au compteur; toute estimation doit utiliser tarif configuré et puissance machine entière, pas seulement GPU. Aucune nouvelle API payante.'),
      ('TikTok','NON PUBLIÉ. Aucun compte connecté, upload/draft/scheduler lancé. SQLite tâche5 awaiting_review, IDs de publication vides. Import manuel possible techniquement après acceptation; vérification des règles de plateforme requise avant publication future.'),
      ('Auto-corrections','Première comparaison trop photographique: priorité donnée au style dans le prompt. Deux scènes refusées à la revue: arbre photographique avec silhouettes et porche évoquant un décor japonais; seules ces scènes régénérées. Accélération FR supprimée; voix EN explicite et refus du fallback FR. Paragraphes remplacés par unités bilingues; filtre IA retiré; fondus noirs retirés; QC blackdetect/clipping; dépendances visuelles séparées de la traduction. Tests de régression ajoutés.'),
      ('Risques et restes','IMPORTANT — Propriétaire: juger style et écoute; agent ne peut certifier une écoute humaine. Historien/relecteur: vêtements/décor génériques non certifiés comme reconstruction exacte. IMPORTANT — Développeur: découverte indépendante de sujets, tous contrats métier Pydantic et schéma DB/migrations générales restent partiels; seules les entrées bilingues sont strictement validées. Planificateur3/jour non finalisé et non activé. MINEUR — débit de lecture variable, nom Thiaroye approximé par lexique. Aucun blocage technique du pilote courant.'),
      ('Démonstration reproductible',r'Set-Location C:\TikTokHistoryFactory ; .\scripts\main.ps1 -Mode Doctor ; .\scripts\main.ps1 -Mode Resume -JobId 5 ; .\scripts\main.ps1 -Mode Export . Reprise à entrées identiques: sept phases réutilisées, aucune nouvelle génération. --try-wan explicite uniquement si souhaité; même clip repris par empreinte.'),
      ('Passage à trois vidéos/jour','NON ACTIVÉ. Nécessite validation humaine du pilote, sujets/sources nouveaux indépendants, tests de charge60–90s, quotas Cloud, budget disque et disponibilité PC, horaires explicites, GPUconcurrence1. Un pilote22.53s ne certifie pas cette cadence; machine éteinte ne produit rien.'),
      ('Adéquation et ce qui reste non vérifié','Historique illustrée en manga, pas histoire du manga. EN audio et FR traduit réels, budget externe0, exports locaux. Non vérifié: acceptation esthétique, écoute humaine de la diction, exactitude archivistique du décor/vêtement, autonomie tous sujets, charge quotidienne, API TikTok réelle, électricité mesurée. Le candidat ne doit pas être appelé production autonome complète.'),
      ('Prochaine action humaine unique',next_action)
    ]
    pilot={'manifest':manifest,'qc':qc,'voice':voice,'phases':phases,'task':task,'editorial_review':review,'ready_path':str(ready)}
    report=Report(schema_version='2.0',created_at=now,verdict='PARTIEL',sections=[Section(number=i,title=t,text=s) for i,(t,s) in enumerate(texts,1)],components=components,changes=changes,tests=tests,pilot=pilot,wan=benchmark,next_action=next_action)
    stem=REPORTS/'FINAL_REPORT_20261019_V2'
    payload=report.model_dump_json(indent=2)
    Report.model_validate_json(payload)
    stem.with_suffix('.json').write_text(payload,encoding='utf-8')
    stem.with_suffix('.schema.json').write_text(json.dumps(Report.model_json_schema(),ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Rapport final V2 — TikTokHistoryFactory','',f'Date: {now}','']
    for section in report.sections:
        lines += [f'## {section.number:02d}. {section.title}','',section.text,'']
    lines += ['## Tableau final','','| Composant | Existant avant | Modification V2 | Test réel | Résultat | Preuve | Risque résiduel |','|---|---|---|---|---|---|---|']
    for c in components:
        lines += ['| '+' | '.join(str(c[k]).replace('|','/') for k in ('component','before','change','test','result','proof','risk'))+' |']
    lines += ['','VERDICT : PARTIEL — pilote réel livré ; revue artistique et écoute requises.','',next_action]
    stem.with_suffix('.md').write_text('\n'.join(lines),encoding='utf-8')
    # Preserve A-U matrix rows and add explicit V2 requirements; no fictitious closure.
    matrix=REPORTS/'REQUIREMENTS_MATRIX.csv'
    rows=list(csv.DictReader(matrix.open(encoding='utf-8-sig')))
    rows=[r for r in rows if not r['id'].startswith('V2-')]
    for ident,requirement,status,proof,limit in [
      ('V2-0','Conservation et sauvegardes','DONE',str(backup),'Anciens brouillons rejetés préservés'),
      ('V2-1','Comparaison manga et illustrations','PARTIAL','work/v2-comparison-style-first/comparison.jpg; editorial-review.json','Style candidat, acceptation propriétaire requise; décors approximatifs'),
      ('V2-2','Voix EN et débit naturel','PARTIAL','voice-manifest.json; narration-en.wav','123.05 WPM sans accélération; écoute non certifiée par agent'),
      ('V2-3','Sous-titres traduits FR','DONE','subtitles.srt; subtitles.ass; subtitles-review.jpg','Timings par WAV, pas alignement mot à mot; lecture humaine utile'),
      ('V2-4','Absence bandeau IA dans vidéo','DONE','render/ffmpeg-log.json; review-frames','Transparence maintenue caption/commentaire MP4'),
      ('V2-5','Wan et fallback réels','DONE','reports/WAN_BENCHMARK_V2.json','Un clip2.125s, pas pleine vidéo animée'),
      ('V2-6','Reprise et contrats bilingues','DONE','tests-v2.log; reports/bilingual-dossier-v2.schema.json','Scope pilote documenté, contrats métier généraux partiels'),
      ('V2-7','Double revue et livraison','PARTIAL','reports/FINAL_REPORT_20261019_V2.md','Code/tests et inspection images effectués; écoute/acceptation propriétaire requises')]:
        rows.append(dict(id=ident,requirement=requirement,status=status,code='pipeline/pilot.py; media/bilingual_audio.py; providers/ffmpeg.py',test='tests/test_v2.py; tests/test_real_pilot.py',evidence=proof,limit=limit))
    with matrix.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['id','requirement','status','code','test','evidence','limit'])
        writer.writeheader(); writer.writerows(rows)
    (REPORTS/'REQUIREMENTS_MATRIX.md').write_text('# Matrice A–U + V2\n\nLes preuves V1 sont historiques ; V2 prime pour langues, visuels et overlay.\n\n| ID | Exigence | Statut | Preuve | Limite |\n|---|---|---|---|---|\n'+'\n'.join('| '+' | '.join(r[k].replace('|','/') for k in ('id','requirement','status','evidence','limit'))+' |' for r in rows),encoding='utf-8')
    index=['# Livraison V2 — candidat pour revue','',f'[Vidéo FFmpeg](pilot.mp4) — {qc["duration"]:.3f}s, EN {voice["words_per_minute"]} mots/minute, sous-titres FR.','',
      '[Narration anglaise](narration-en.wav) · [SRT français](subtitles.srt) · [ASS français](subtitles.ass)',
      '[Script anglais](scenario.txt) · [Traduction française](translation-fr.txt)',
      '[Planche contact](contact-sheet.jpg) · [Ancien / nouveau](old-new-comparison.jpg) · [Sous-titres en images](subtitles-review.jpg)',
      '[Sources](sources.md) · [Manifeste](manifest.json) · [QC](qc.json) · [Revue éditoriale](editorial-review.json)',
      '',f'Variante Wan : {benchmark["wan_alternative"]}',f'Rapport complet : {stem.with_suffix(".md")}',
      '', 'Statut : AWAITING_REVIEW. NON PUBLIÉ. Ancien pilote DRAFT_REJECTED. Style et diction à écouter/juger par le propriétaire.']
    (exported/'INDEX.md').write_text('\n'.join(index),encoding='utf-8')
    (exported/'artifact_hashes.json').write_text(json.dumps({str(p.relative_to(exported)):digest(p) for p in exported.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'},indent=2),encoding='utf-8')
    print('DELIVERED',exported,'REPORT',stem.with_suffix('.md'),'TESTS',tests['count'],'VERDICT PARTIEL')


if __name__=='__main__':
    main()
