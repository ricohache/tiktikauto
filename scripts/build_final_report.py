"""Build evidence-based reports; run with existing ComfyUI Python (Pydantic)."""
import csv
import hashlib
import json
import os
import platform
import sqlite3
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports'
WORK = ROOT / 'work/pilot-thiaroye-1944'
BACKUP = ROOT / 'backups/pilot-20261019-094855'


class Component(BaseModel):
    name: str
    status: Literal['OK', 'PARTIEL', 'BLOQUÉ', 'NON_TESTÉ']
    proof: str
    limitation: str = ''


class Section(BaseModel):
    number: int
    title: str
    text: str


class FinalReport(BaseModel):
    schema_version: Literal['1.0']
    created_at: str
    verdict: Literal['OPÉRATIONNEL', 'PARTIEL', 'BLOQUÉ']
    sections: list[Section]
    subsystems: list[Component]
    changes: list[dict[str, str]]
    tests: dict
    pilot: dict
    wan: dict
    next_action: str


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def checksum(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    now = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=2)))
    manifest = read_json(WORK / 'manifest.json')
    qc = read_json(WORK / 'qc.json')
    dossier = read_json(ROOT / 'data/subjects/thiaroye-1944.json')
    tests = read_json(REPORTS / 'tests-final.json')
    import re
    test_log = (REPORTS/'tests-final.log').read_text(encoding='utf-8-sig')
    count = re.search(r'Ran (\d+) tests', test_log)
    tests['count'] = int(count.group(1)) if count else None
    tests['other_observed_commands'] = [
        {'command': '& .\\scripts\\main.ps1 -Mode Doctor', 'exit_code': 0, 'result': '7 health checks OK'},
        {'command': '& C:\\TikTokHistoryFactory\\scripts\\main.ps1 -Mode Resume -JobId 4', 'cwd': 'C:\\', 'exit_code': 0, 'result': 'All seven stages resumed without regeneration'},
        {'command': '.\\.venv\\Scripts\\python.exe -m tiktok_history_factory pilot --try-wan --work-dir C:\\TikTokHistoryFactory\\work\\pilot-thiaroye-1944', 'exit_code': 0, 'result': 'Real 17-frame Wan generation and valid final MP4'},
        {'command': 'PowerShell Parser::ParseFile on scripts/*.ps1; Python ast.parse on package/tests', 'exit_code': 0, 'result': 'No syntax error in final checked sources'}]
    wan_path = WORK / 'wan/clip.wan.json'
    wan = read_json(wan_path) if wan_path.exists() else {'status': 'NOT_TESTED'}
    with urllib.request.urlopen('http://127.0.0.1:8188/system_stats', timeout=15) as response:
        machine = json.load(response)
    gpu = subprocess.run(['nvidia-smi','--query-gpu=name,driver_version,memory.total','--format=csv,noheader'],capture_output=True,text=True)
    changes = []
    candidates = []
    for base in ('tiktok_history_factory','scripts','tests','docs','workflows'):
        candidates += [p for p in (ROOT/base).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    candidates += [ROOT/name for name in ('README.md','pyproject.toml','.env','.env.example','.gitignore','requirements-lock.txt','data/subjects/thiaroye-1944.json')]
    candidates += [p for p in (ROOT/'assets/licenses').rglob('*') if p.is_file()]
    for path in sorted(candidates):
        relative = path.relative_to(ROOT)
        original = BACKUP/relative
        if not original.exists() or checksum(original) != checksum(path):
            changes.append({'path': str(relative), 'kind': 'MODIFIED' if original.exists() else 'CREATED',
                            'reason': 'Pilot integration, verification or documentation; see subsystem reports'})
    image_records = manifest['stages']['images']['generations']
    pilot = {'output': manifest['output_path'], 'duration': qc['duration'], 'status': manifest['status'],
             'scenes': len(image_records), 'image_seconds': [r.get('seconds') for r in image_records],
             'voice': qc['voice'], 'video_sha256': checksum(manifest['output_path']),
             'animation': manifest['animation'], 'publication': 'NON PUBLIÉ'}
    components = [
        Component(name='Infrastructure',status='OK',proof=f"{platform.platform()}; projet Python 3.11.9; ComfyUI {machine['system']['comfyui_version']}; {gpu.stdout.strip()}; RAM {machine['system']['ram_total']/1024**3:.2f} Gio",limitation='CPU : '+os.environ.get('PROCESSOR_IDENTIFIER','non mesuré')),
        Component(name='Recherche historique',status='PARTIEL',proof='3 sources collectées, extraits retrouvés, 4 claims avec références',limitation='Dossier révisé ; découverte autonome et preuve automatique de vérité non validées'),
        Component(name='Ollama Cloud',status='OK',proof='Kimi-k3:cloud répond via Ollama local /api/chat ; réponse réelle et usage tokens conservés',limitation='Solde et quotas du compte non consultés ; aucun crédit supplémentaire acheté'),
        Component(name='ComfyUI manga',status='OK',proof='4 illustrations locales SDXL, PNG 768x1344 avec workflow/seed/prompt_id/SHA-256',limitation='Modèle généraliste ; esthétique seinen et détails symboliques soumis à revue humaine'),
        Component(name='TTS français',status='OK',proof='Piper 1.8.0, SIWIS fr_FR, WAV 22050 Hz mono non silencieux',limitation='Écoute humaine et prononciation de Thiaroye non certifiées par une mesure automatique'),
        Component(name='Animation',status='OK' if wan.get('status')=='SUCCESS' else 'PARTIEL',proof='FFmpeg réel ; essai Wan : '+wan.get('status','inconnu'),limitation='Le succès technique Wan ne prouve pas sa qualité visuelle ; voir WAN_BENCHMARK.md'),
        Component(name='FFmpeg',status='OK',proof=f"1080x1920 H.264/AAC, 30 fps, {qc['duration']:.3f} s, décodage complet sans erreur"),
        Component(name='Orchestration',status='PARTIEL',proof='7 phases réelles, statuts SQLite, verrou exclusif, checkpoints SHA-256, reprise sans nouveaux médias',limitation='Pilote à dossier révisé ; automatisation générale multi-sujets non certifiée'),
        Component(name='SQLite',status='OK',proof='Base intègre, job 4 awaiting_review, historiques de phases ; sauvegardes cohérentes',limitation='Trois anciennes tâches de test conservées ; aucun ancien élément supprimé'),
        Component(name='Pilote vidéo réel',status='OK',proof=manifest['output_path'],limitation='AWAITING_REVIEW ; aucune publication autorisée')]
    sources = '\n'.join('- '+s['title']+' : '+s['url'] for s in dossier['sources'])
    tree = '\n'.join(str(p.relative_to(ROOT)) for p in sorted(Path(manifest['output_path']).parent.rglob('*')) if p.is_file())
    rows = [
        (1,'Résumé exécutif','VERDICT GLOBAL = PARTIEL. Le pilote réel est opérationnel et exporté pour revue. La chaîne autonome générale et le débit quotidien ne sont pas déclarés validés.'),
        (2,'Machine réellement observée',components[0].proof+'\n'+components[0].limitation+'\nPython ComfyUI : '+machine['system']['python_version']+'\nPyTorch : '+machine['system']['pytorch_version']),
        (3,'État initial et sauvegardes','Base initiale : smoke test existant, aucun modèle image ni voix FR, connecteurs incomplets. Sauvegarde avant modifications : '+str(BACKUP)+'. Sauvegardes supplémentaires : backups/before-pilot-*, pilot-before-visual-revision-03, pilot-before-visual-revision-04 et pilot-before-final-render. Le dépôt racine n’est pas Git ; aucune initialisation de distant.'),
        (4,'Fichiers créés ou corrigés','\n'.join(f"- {c['kind']} : {c['path']} — {c['reason']}" for c in changes)+'\nListe des sources, scripts, dépendances et licences ; les médias et poids sont détaillés aux sections 5, 6 et 12. Caches Python et copies de sauvegarde exclus de cette liste. Aucune donnée utilisateur supprimée. .env contient des valeurs privées et reste exclu des exports.'),
        (5,'Arborescence des livrables réels',tree),
        (6,'Modèles, provenance et licences','SDXL officiel, 6 938 078 334 octets, révision 462165984030d82259a11f4367a4eed129e94a7b, Open RAIL++-M. Voix SIWIS 63 201 294 octets, CC-BY 4.0. Wan : 18 144 966 705 octets, Apache 2.0, détails et SHA-256 dans wan-model-evaluation.json. Vérifications locales consignées dans les .provenance.json. Piper GPL-3.0. Polices Windows seulement rasterisées. Aucun modèle NSFW spécialisé installé. Voir docs/LICENCES.md.'),
        (7,'Fournisseurs et limites','Kimi Cloud par la passerelle existante http://127.0.0.1:11434/api/chat ; aucun réglage global modifié. ComfyUI local, Piper local CPU, montage local FFmpeg. Sources publiques et Hugging Face. Aucun service payant à l’usage ajouté. Solde du forfait inconnu.'),
        (8,'Déroulement du pilote',sources+'\nScénario français source-verrouillé, 4 scènes symboliques sans gore ni chiffre de victimes. PNG réels, fiche personnage composite, narration Piper, SRT/ASS alignés aux phrases, animation '+manifest['animation']['mode']+', MP4 et QC. Les illlustrations ne constituent pas des archives.'),
        (9,'Tests exacts et codes de sortie',json.dumps(tests,ensure_ascii=False,indent=2)+'\nTests API native/compatible OpenAI et erreurs OOM/timeout : simulations unitaires explicitement identifiées. Les tests d’intégration lisent les médias réels. Le test technique de SaveVideo à deux images unies est seulement un contrôle de contrat, jamais appelé vidéo Wan.'),
        (10,'Récapitulatif des exigences','Voir REQUIREMENTS_MATRIX.md et .csv. Les lignes PARTIAL ne sont pas présentées comme terminées ; les exigences TikTok et production restent désactivées.'),
        (11,'Benchmark réel','Images retenues, secondes de génération par fichier : '+str(pilot['image_seconds'])+'. Le premier essai initial a pris 26,23 s, sans OOM. Pic VRAM SDXL non échantillonné, non inventé. Wan : '+wan.get('status','NOT_TESTED')+', temps '+str(wan.get('seconds','non mesuré'))+' s. Télémétrie GPU brute dans clip.wan.json si disponible. Les clips FFmpeg et la voix sont chronométrés dans run_history ; pas de capacité 3/jour déduite de ce seul épisode.'),
        (12,'Fichiers livrés','Vidéo : '+manifest['output_path']+'\nDossier complet : '+str(Path(manifest['output_path']).parent)+'\nPreuves et médias intermédiaires : '+str(WORK)+'\nLicences : '+str(ROOT/'assets/licenses')),
        (13,'Coûts','Aucun achat, aucun abonnement nouveau, aucune API TTS/image à l’usage. Usage de l’abonnement Ollama existant dans sa connexion actuelle ; tokens retournés par les appels conservés, solde non connu. Énergie totale et facture électrique non mesurées. KWH_PRICE_EUR configurable ; une mesure GPU seule ne représente pas la consommation complète du PC.'),
        (14,'Publication TikTok','NON PUBLIÉ. Aucun appel API TikTok, aucun upload, aucune tâche quotidienne créée ou activée. Exports locaux exclusivement destinés à une revue humaine.'),
        (15,'Auto-corrections','Route Ollama corrigée ; API image réelle ; détection Piper fiable ; vrai stdin TTS et contrôle silence ; compositeur compatible ; boucle pilote et checkpoint ; sauvegarde DB ; anti-doublon SQL ; export bloqué sans fichier ; sous-titre résiduel corrigé ; anachronismes visuels rejetés ; résolution ASS explicite après inspection du MP4 ; tests d’intégration et de reprise. Un test a échoué à cause d’une indentation puis a été corrigé et relancé. Un lien de licence Wan absent du dépôt de poids a été remplacé par le texte officiel du dépôt Wan-Video.'),
        (16,'Risques et restes à faire','IMPORTANT : revue humaine du style manga seinen, des accessoires, de la diction et des sources avant diffusion. IMPORTANT : recherche autonome multi-sujets, machine d’états exhaustive, Pydantic généralisé et planification réellement certifiée restent partiels. IMPORTANT : outils legacy supervisor.py et anciens générateurs ne doivent pas servir de lanceur ; schéma SQLite incompatible et boucle récurrente. MINEUR : découpage de sous-titres à la phrase, sans alignement mot à mot. Aucun blocage critique pour lire le pilote livré.'),
        (17,'Démonstration reproductible','& C:\\TikTokHistoryFactory\\scripts\\main.ps1 -Mode Doctor\n& C:\\TikTokHistoryFactory\\scripts\\main.ps1 -Mode Resume -JobId 4\n& C:\\TikTokHistoryFactory\\scripts\\main.ps1 -Mode Export\nLa reprise conserve les étapes validées. Ajouter --try-wan à la commande Python seulement pour le mode optionnel documenté. Le menu est disponible sans argument.'),
        (18,'Conditions avant trois vidéos quotidiennes','Validation explicite du pilote par le propriétaire ; validation de plusieurs dossiers indépendants ; mesure du débit complet, incidents et reprises ; contrôle des quotas ; horaires choisis par le propriétaire ; concurrence GPU 1 ; tests de charge. Aucun horaire imposé ni production quotidienne déclenchée.'),
        (19,'Adéquation à la demande','Vrai pilote historique français de 20–30 s, quatre dessins 2D détaillés et déclarés IA, non graphiques, médias réellement produits. Style guidé seinen, à valider humainement : SDXL généraliste ne garantit pas chaque détail. Chaîne pilote fonctionnelle ; autonomie documentaire générale non certifiée. Le test synthétique antérieur reste distinct et n’est pas livré comme pilote réel.'),
        (20,'Prochaine action humaine unique','Visionner et écouter le pilote livré, puis valider ou préciser les corrections de style, d’histoire et de diction. Aucune activation de cadence ou de publication n’est demandée ici.')]
    report = FinalReport(schema_version='1.0',created_at=now.isoformat(),verdict='PARTIEL',
                         sections=[Section(number=n,title=t,text=body) for n,t,body in rows],
                         subsystems=components,changes=changes,tests=tests,pilot=pilot,wan=wan,
                         next_action=rows[-1][2])
    serialized = report.model_dump_json(indent=2)
    FinalReport.model_validate_json(serialized)
    name='FINAL_REPORT_20261019_PILOT'
    (REPORTS/(name+'.json')).write_text(serialized,encoding='utf-8')
    (REPORTS/(name+'.schema.json')).write_text(json.dumps(FinalReport.model_json_schema(),ensure_ascii=False,indent=2),encoding='utf-8')
    md='# Rapport final — TikTokHistoryFactory — '+now.isoformat()+'\n\n'
    md+='| Sous-système | État | Preuve / limite |\n|---|---|---|\n'
    for item in components:
        md+=f'| {item.name} | {item.status} | {item.proof} {item.limitation} |\n'
    for section in report.sections:
        md+=f'\n## {section.number:02d}. {section.title}\n\n{section.text}\n'
    md+='\n## Ce que je n’ai pas pu vérifier\n\nÉcoute humaine, certification d’une restitution historique visuelle exacte, fidélité stylistique garantie, solde Ollama, facture électrique et débit quotidien durable. Aucun compte TikTok testé.\n'
    (REPORTS/(name+'.md')).write_text(md,encoding='utf-8')
    print('REPORT_VALIDATED',REPORTS/(name+'.md'))


if __name__=='__main__':
    main()
