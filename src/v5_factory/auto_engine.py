"""Moteur de production autonome pour TikTokHistoryFactory V5.
Orchestre la chaîne complète : sujet → storyboard → images → narration → sous-titres → MP4.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path
from typing import Dict, List, Optional

_V5_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_V5_DIR))
sys.path.insert(0, str(_V5_DIR.parent.parent / 'TikTokHistoryFactory_finish_v5'))

import finish_pilot as fp
import subtitle_aligner as sa
from comfyui_client import generate_images_for_scenes
import quality_v5 as qv
from catalogue import SubjectCatalogue, _slug_hash

DEFAULT_ROOT = Path(r'C:\TikTokHistoryFactory')
FPS = 30
WIDTH, HEIGHT = 1080, 1920
TARGET_SECONDS = 90
MIN_SHOT_DURATION = 1.5


class AutoProductionEngine:
    """Moteur end-to-end de production vidéo historique autonome."""

    def __init__(self, project: Path = DEFAULT_ROOT):
        self.project = project.resolve()
        self.ffmpeg = fp.check_exe('ffmpeg')
        self.ffprobe = fp.check_exe('ffprobe')
        self.catalogue = SubjectCatalogue()
        # Connexion SQLite pour persistance
        self.db_path = self.project / 'data' / 'factory.db'
        self._init_db()

    def _init_db(self):
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        # Table des productions pour anti-doublon et reprise
        c.execute('''
            CREATE TABLE IF NOT EXISTS auto_productions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                title_en TEXT,
                title_fr TEXT,
                status TEXT DEFAULT 'pending',
                storyboard_path TEXT,
                output_dir TEXT,
                mp4_path TEXT,
                sha256 TEXT,
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                error TEXT,
                qc_passed INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()

    def _db_insert(self, slug: str, title_en: str, title_fr: str):
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        try:
            c.execute('INSERT OR IGNORE INTO auto_productions (slug, title_en, title_fr, status) VALUES (?,?,?,?)',
                     (slug, title_en, title_fr, 'pending'))
            conn.commit()
        except:
            pass
        conn.close()

    def _db_update(self, slug: str, status: str, output_dir: str = None, mp4_path: str = None,
                   sha256: str = None, error: str = None, qc_passed: int = 0):
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        completed = 'CURRENT_TIMESTAMP' if status == 'completed' else None
        c.execute('''
            UPDATE auto_productions
            SET status=?, output_dir=?, mp4_path=?, sha256=?, error=?, qc_passed=?,
                completed_at=CASE WHEN ?='completed' THEN CURRENT_TIMESTAMP ELSE completed_at END
            WHERE slug=?
        ''', (status, output_dir, mp4_path, sha256, error, qc_passed, status, slug))
        conn.commit()
        conn.close()

    def _db_get_completed_hashes(self) -> List[str]:
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("SELECT slug FROM auto_productions WHERE status IN ('completed','rendering','storyboarding')")
        result = [_slug_hash(r[0]) for r in c.fetchall()]
        conn.close()
        return result

    def generate_storyboard(self, subject: Dict, work_dir: Path) -> Path:
        """Génère un storyboard automatique à partir du catalogue."""
        print(f'[STORYBOARD] Génération pour: {subject["slug"]}')
        summary_en = subject['summary_en']
        summary_fr = subject['summary_fr']

        # Scénario structuré en 11 scènes (~90s)
        scenes = self._build_scenes_from_subject(subject)

        storyboard = {
            "episode": subject["slug"],
            "style": "japanese manga seinen, monochrome, black and white, ink drawing, screentone, expressive shadows",
            "total_duration_sec": TARGET_SECONDS,
            "scenes": scenes
        }

        script_dir = work_dir / 'script'
        script_dir.mkdir(parents=True, exist_ok=True)
        sb_path = script_dir / 'storyboard.json'
        sb_path.write_text(json.dumps(storyboard, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f'[STORYBOARD] Sauvegardé: {sb_path}')
        return sb_path

    def _build_scenes_from_subject(self, subject: Dict) -> List[Dict]:
        """Construit 11 scènes narratives à partir du résumé du sujet."""
        # Textes prédéfinis basés sur les sujets catalogués
        # Pour l'autonomie réelle, on utiliserait un LLM local (Gemma via Ollama)
        # Ici, on utilise les textes structurés du catalogue
        templates = {
            'patrice-lumumba-assassinat': {
                'scenes': [
                    ("On January seventeenth, nineteen sixty-one, Patrice Lumumba, the first elected prime minister of the Congo, was captured.", "Le 17 janvier 1961, Patrice Lumumba, premier ministre démocratiquement élu du Congo, fut capturé."),
                    ("Belgian officers and Congolese rivals had conspired against him for months.", "Des officiers belges et des rivaux congolais avaient conspiré contre lui pendant des mois."),
                    ("He was taken to Katanga province, where separatist forces held him.", "Il fut emmené au Katanga, où des forces séparatistes le détenaient."),
                    ("There, he was tortured and humiliated in front of foreign officers.", "Là-bas, il fut torturé et humilié devant des officiers étrangers."),
                    ("A Belgian officer later admitted his unit supervised the execution.", "Un officier belge admit plus tard que son unité avait supervisé l'exécution."),
                    ("Lumumba and two ministers were shot by a firing squad.", "Lumumba et deux ministres furent fusillés."),
                    ("Their bodies were later dissolved in acid to leave no trace.", "Leurs corps furent ensuite dissous dans l'acide pour ne laisser aucune trace."),
                    ("The CIA had targeted him as a communist threat.", "La CIA l'avait ciblé comme une menace communiste."),
                    ("Belgium officially apologized only in two thousand two.", "La Belgique ne s'excusa officiellement qu'en 2002."),
                    ("Lumumba's assassination remains one of colonialism's darkest chapters.", "L'assassinat de Lumumba reste l'un des chapitres les plus sombres du colonialisme."),
                    ("His voice still echoes across Africa today.", "Sa voix résonne encore aujourd'hui à travers l'Afrique.")
                ]
            },
                        'ruben-um-nyobe': {
                'scenes': [
                    ("In nineteen forty-eight, Ruben Um Nyobe helped found the UPC, calling for Cameroon's independence from French rule.", "En 1948, Ruben Um Nyobè contribue à fonder l'UPC qui réclame l'indépendance du Cameroun face à la France."),
                    ("He was a teacher, a trade unionist, and a committed opponent of the French administration.", "Il était instituteur, syndicaliste et opposant résolu à l'administration française."),
                    ("The UPC demanded full independence, unlike other parties accepting gradual autonomy.", "L'UPC exigeait l'indépendance totale, contrairement aux autres partis qui acceptaient une autonomie progressive."),
                    ("French authorities responded with repression, forcing Um Nyobe into hiding.", "Les autorités françaises répondirent par la répression, contraignant Um Nyobè à la clandestinité."),
                    ("He became known as the invisible prime minister, leading resistance from the bush.", "On le surnomma le Premier ministre invisible, dirigeant la résistance depuis la brousse."),
                    ("In nineteen fifty-eight, Um Nyobe was ambushed and killed by French forces.", "En 1958, Um Nyobè fut tué en embuscade par les forces françaises."),
                    ("His body was never returned to his family.", "Son corps ne fut jamais rendu à sa famille."),
                    ("After his death, the UPC continued its struggle for years, marked by further repression.", "Après sa mort, l'UPC poursuivit son combat pendant des années, marqué par d'autres répressions."),
                    ("Today, Um Nyobe is remembered as a symbol of Cameroonian independence.", "Aujourd'hui, Um Nyobè est reconnu comme un symbole de l'indépendance camerounaise."),
                    ("His story reminds us that the fight for self-determination often comes at a great personal cost.", "Son histoire rappelle que la lutte pour l'autodétermination a souvent un lourd prix personnel."),
                    ("Ruben Um Nyobe gave his life for a Cameroon that would finally be free.", "Ruben Um Nyobè a donné sa vie pour un Cameroun qui serait enfin libre.")
                ]
            },
            'tirailleurs-senegalais': {
                'scenes': [
                    ("For over a century, West African tirailleurs fought in France's colonial wars.", "Pendant plus d'un siècle, les tirailleurs d'Afrique de l'Ouest ont combattu dans les guerres coloniales de la France."),
                    ("From Verdun to Indochina, they served in France's most brutal conflicts.", "De Verdun à l'Indochine, ils ont servi dans les conflits les plus brutaux de la France."),
                    ("They were promised equality, but faced discrimination and unpaid pensions.", "On leur avait promis l'égalité, mais ils ont fait face à la discrimination et aux pensions impayées."),
                    ("After independence, many veterans were abandoned by the French state.", "Après l'indépendance, de nombreux anciens combattants furent abandonnés par l'État français."),
                    ("They marched on Paris in nineteen forty-four, demanding fair treatment.", "Ils marchèrent sur Paris en 1944, réclamant un traitement équitable."),
                    ("African soldiers were often the first to die on European battlefields.", "Les soldats africains furent souvent les premiers à mourir sur les champs de bataille européens."),
                    ("France only officially recognized their contribution decades later.", "La France ne reconnut officiellement leur contribution que des décennies plus tard."),
                    ("Their pensions remained frozen at colonial rates until the two thousands.", "Leurs pensions restèrent gelées aux taux coloniaux jusqu'aux années 2000."),
                    ("The last surviving tirailleurs passed away with neither honor nor justice.", "Les derniers tirailleurs survivants sont décédés sans honneur ni justice."),
                    ("Their sacrifice symbolizes the forgotten debts of European colonial powers.", "Leur sacrifice symbolise les dettes oubliées des puissances coloniales européennes."),
                    ("Remembering them means recognizing that colonial history is not finished.", "Se souvenir d'eux, c'est reconnaître que l'histoire coloniale n'est pas terminée.")
                ]
            },
'thomas-sankara-1987': {
                'scenes': [
                    ("On October fifteenth, nineteen eighty-seven, Burkina Faso lost its revolutionary president.", "Le 15 octobre 1987, le Burkina Faso perdait son président révolutionnaire."),
                    ("Thomas Sankara, known as the upright man, had transformed his nation.", "Thomas Sankara, surnommé l'homme intègre, avait transformé sa nation."),
                    ("He fought corruption, promoted women's rights, and planted millions of trees.", "Il a combattu la corruption, promu les droits des femmes et planté des millions d'arbres."),
                    ("His reforms threatened French influence in West Africa.", "Ses réformes menaçaient l'influence française en Afrique de l'Ouest."),
                    ("A group of officers led by his friend Blaise Compaoré struck.", "Un groupe d'officiers mené par son ami Blaise Compaoré frappa."),
                    ("Sankara was killed in a coup at the age of thirty-seven.", "Sankara fut tué lors d'un coup d'État à l'âge de trente-sept ans."),
                    ("Twelve of his companions were also murdered that day.", "Douze de ses compagnons furent également assassinés ce jour-là."),
                    ("Compaoré ruled for twenty-seven years after eliminating his rival.", "Compaoré régna vingt-sept ans après avoir éliminé son rival."),
                    ("Sankara's legacy lives on in youth movements across Africa.", "L'héritage de Sankara survit dans les mouvements de jeunesse en Afrique."),
                    ("His assassination remains unpunished.", "Son assassinat reste impuni."),
                    ("Some truths only survive in the memory of those who refuse to forget.", "Certaines vérités ne survivent que dans la mémoire de ceux qui refusent d'oublier.")
                ]
            },
            'guerre-algerie-violences': {
                'scenes': [
                    ("Between nineteen fifty-four and nineteen sixty-two, Algeria bled.", "Entre 1954 et 1962, l'Algérie saignait."),
                    ("The war of independence claimed hundreds of thousands of lives.", "La guerre d'indépendance a fait des centaines de milliers de morts."),
                    ("French forces used torture as a systematic weapon.", "Les forces françaises utilisaient la torture comme arme systématique."),
                    ("Villages were burned and civilians massacred.", "Des villages furent brûlés et des civils massacrés."),
                    ("The FLN also carried out brutal reprisals against suspected traitors.", "Le FLN a aussi mené des représailles brutales contre des suspects."),
                    ("Harkis, Algerian fighters who sided with France, were abandoned after independence.", "Les harkis, combattants algériens pro-français, furent abandonnés après l'indépendance."),
                    ("Many were killed by the FLN, others fled to France in poverty.", "Beaucoup furent tués par le FLN, d'autres fuirent vers la France dans la misère."),
                    ("The Algerian War was kept out of French schoolbooks for decades.", "La guerre d'Algérie fut occultée des manuels scolaires français pendant des décennies."),
                    ("In two thousand five, France officially recognized the Algerian genocide.", "En 2005, la France reconnut officiellement le génocide algérien."),
                    ("The wounds of colonization run deep on both shores of the Mediterranean.", "Les blessures de la colonisation sont profondes des deux côtés de la Méditerranée."),
                    ("History must remember, not to divide, but so it never happens again.", "L'histoire doit se souvenir, non pour diviser, mais pour que cela ne se reproduise jamais.")
                ]
            },
            'pende-revolt-1931': {
                'scenes': [
                    ("In May nineteen thirty-one, the Pende people of the Belgian Congo rose up. For years, forced labor and crushing taxes had reduced their villages to starvation. Rubber companies took their land and their dignity. The breaking point had finally arrived.", "En mai 1931, le peuple Pende du Congo belge se souleva. Pendant des annees, le travail force et les impots ecrasants avaient reduit leurs villages a la famine. Les companies du caoutchouc prirent leurs terres et leur dignite. Le point de rupture etait enfin arrive."),
                    ("Colonial officials demanded heavy head taxes from every adult man. Workers had to spend weeks harvesting rubber instead of tending their own fields. Families went hungry while plantation profits soared. The injustice was unbearable.", "Les fonctionnaires coloniaux exigeaient de lourds impots de capitation de chaque homme adulte. Les travailleurs devaient passer des semaines a recolter le caoutchouc au lieu de cultiver leurs propres champs. Les familles souffraient de la faim pendant que les profits des plantations s'envolaient. L'injustice etait insupportable."),
                    ("The Societe de concession companies ruled vast territories with brutal efficiency. Armed guards enforced impossible quotas on villagers who had no choice but to comply. Resistance meant punishment, humiliation, and worse. Colonial power knew no mercy.", "Les societes de concession regissaient de vastes territoires avec une brutalite efficace. Des gardes armes imposaient des quotas impossibles aux villageois qui n'avaient d'autre choix que d'obtempérer. La resistance signifiait punition, humiliation et pire. Le pouvoir colonial ne connaissait aucune pitie."),
                    ("In early June, Pende men finally refused to surrender their harvests to colonial agents. They gathered in the villages and declared that no more rubber would be collected at gunpoint. The colonial administration saw this as open rebellion. The response would be devastating.", "En debut juin, les hommes Pende refuserent enfin de livrer leurs recoltes aux agents coloniaux. Ils se rassemblerent dans les villages et declarerent qu'aucun caoutchouc ne serait plus recolte sous la menace des armes. L'administration coloniale vit cela comme une rebellion ouverte. La reponse serait devastatrice."),
                    ("On June eighth, nineteen thirty-one, territorial agent Maximilien Balot arrived in Kilamba village to collect taxes. An angry crowd confronted him. Shots were fired, and Balot was killed. His death gave the colonial administration the pretext it wanted for massive retaliation.", "Le 8 juin 1931, l'agent territorial Maximilien Balot arriva au village de Kilamba pour collecter les impots. Une foule en colere le confronta. Des coups de feu furent tires, et Balot fut tue. Sa mort donna a l'administration coloniale le pretexte qu'elle cherchait pour une retaliation massive."),
                    ("The colonial administration responded with machine guns, artillery, and mass reprisals. Columns of Force Publique soldiers swept through Pende territory. Hundreds of villagers were rounded up, beaten, and executed without trial. The violence was systematic and deliberate.", "L'administration coloniale repondit par des mitrailleuses, de l'artillerie et des represailles massives. Des colonnes de soldats de la Force Publique balayerent le territoire Pende. Des centaines de villageois furent rassembles, battus et executes sans proces. La violence etait systematique et deliberée."),
                    ("In the weeks that followed, hundreds of Pende men, women, and children were killed. Many were shot trying to flee into the forest. Others were burned alive in their homes. The exact number of victims remains unknown, but estimates range into the thousands. Colonial records were deliberately destroyed.", "Dans les semaines qui suivirent, des centaines d'hommes, de femmes et d'enfants Pende furent tues. Beaucoup furent abattus en tentant de fuir dans la foret. D'autres furent brules vifs dans leurs maisons. Le nombre exact de victimes reste inconnu, mais les estimations vont jusqu'aux milliers. Les archives coloniales furent deliberement detruites."),
                    ("Entire villages were burned to the ground by colonial troops. Survivors fled into the dense forest, leaving behind everything they owned. Families were separated, and many starved in hiding. The land that had sustained them for generations was now a scarred and silent wasteland.", "Des villages entiers furent reduits en cendres par les troupes coloniales. Les survivants s'enfuirent dans la dense foret, abandonnant tout ce qu'ils possedaient. Les familles furent separees, et beaucoup moururent de faim dans leur cachette. La terre qui les avait sustenus pendant des generations etait maintenant un terrain sterile et silencieux."),
                    ("While the blood still flowed, the Leverhulme rubber and palm oil plantations continued their operations as if nothing had happened. British and Belgian businessmen profited from the forced labor that had triggered the revolt. The system of exploitation remained firmly in place, untouched by the massacre.", "Pendant que le sang coulait encore, les plantations de caoutchouc et d'huile de palme Leverhulme continuerent leurs operations comme si de rien n'etait. Des hommes d'affaires britanniques et belges profiterent du travail force qui avait declenche la revolte. Le systeme d'exploitation restait fermement en place, intact malgre le massacre."),
                    ("The Pende revolt was systematically buried in colonial archives for decades. Belgian officials classified the records and denied the scale of the killings. It was only in the late twentieth century that historians began reconstructing the truth from scattered documents. The silence was a second violence.", "La revolte Pende fut systematiquement enfouie dans les archives coloniales pendant des decennies. Les fonctionnaires belges classerent les dossiers et nierent l'ampleur des tueries. Ce n'est que vers la fin du vingtieme siecle que des historiens commencerent a reconstruire la verite a partir de documents epars. Le silence fut une seconde violence."),
                    ("Today, the Pende revolt remains a powerful symbol of Africa's forgotten fight for dignity. It reminds us that behind every colonial statistic, there were human beings who refused to surrender. Their resistance lives on in the memory of those who demand justice for the crimes of colonialism.", "Aujourd'hui, la revolte Pende reste un symbole puissant de la lutte oubliee de l'Afrique pour sa dignite. Elle nous rappelle que derriere chaque statistique coloniale, il y avait des etres humains qui refusaient de se rendre. Leur resistance survit dans la memoire de ceux qui reclament justice pour les crimes du colonialisme.")
                ]
            },
            'madagascar-revolt-1947': {
                'scenes': [
                    ("On March twenty-ninth, nineteen forty-seven, the Malagasy people rose against French colonial rule.", "Le 29 mars 1947, le peuple malgache se souleva contre la domination coloniale francaise."),
                    ("Armed insurgents with spears and a few rifles seized control of several military posts.", "Des insurges armes de sagaies et de quelques fusils prirent le controle de plusieurs postes militaires."),
                    ("France responded by deploying troops and bombing inland villages.", "La France reagit en deployant des troupes et en bombardant les villages de l'interieur."),
                    ("Thousands of Malagasy were killed, far more than official French estimates admitted.", "Des milliers de Malgaches furent tues, bien plus que les estimations officielles francaises ne l'admettaient."),
                    ("The repression lasted for months, with summary executions and detention camps.", "La repression dura des mois, avec des executions sommaires et des camps de detention."),
                    ("The leaders of the Malagasy Democratic Renewal Movement were arrested and tried.", "Les leaders du Mouvement democratique de la renovation malgache furent arretes et juges."),
                    ("Survivors were deported to forced labor camps on Nosy Lava island.", "Les survivants furent deportes dans des camps de travail force sur l'ile de Nosy Lava."),
                    ("France maintained silence for decades about the scale of the repression.", "La France maintint le silence pendant des decennies sur l'ampleur de la repression."),
                    ("It was only in nineteen ninety that France began to open its archives on the uprising.", "Ce n'est qu'en 1990 que la France commenca a ouvrir ses archives sur la revolte."),
                    ("Today, the nineteen forty-seven uprising remains a symbol of the struggle for Malagasy independence.", "Aujourd'hui, la revolte de 1947 reste un symbole de la lutte pour l'independance malgache."),
                    ("This story reminds us that colonial archives still hide truths.", "Cette histoire rappelle que les archives coloniales cachent encore des verites.")
                ]
            }
        }

        slug = subject['slug']
        tmpl = templates.get(slug)
        if not tmpl:
            raise RuntimeError(f'Aucun template de storyboard pour: {slug}. Le catalogue doit être enrichi.')

        scenes = []
        for i, (en, fr) in enumerate(tmpl['scenes'], 1):
            scenes.append({
                "id": f"SC{i:02d}",
                "narration_en": en,
                "narration_fr": fr,
                "positive_prompt": subject.get('style_prompt', '') + f", scene {i}, historical event",
                "seed": int(subject['event_date'].split('-')[0]) * 10000 + i * 100
            })
        return scenes

    def produce_subject(self, slug: str) -> Dict:
        """Produit un episode complet a partir du catalogue."""
        start_time = time.time()
        subject = self.catalogue.get_by_slug(slug)
        if not subject:
            raise ValueError(f"Sujet inconnu: {slug}")

        self._db_insert(slug, subject["title_en"], subject["title_fr"])
        self._db_update(slug, "storyboarding")

        # Dossier de travail
        work_dir = self.project / "work" / f"auto-{slug}"
        work_dir.mkdir(parents=True, exist_ok=True)
        (work_dir / "images").mkdir(exist_ok=True)

        # 1. Storyboard
        storyboard_path = self.generate_storyboard(subject, work_dir)
        sb = json.loads(storyboard_path.read_text(encoding="utf-8-sig"))
        scenes = sb.get("scenes", [])
        print(f"[STORYBOARD] {len(scenes)} scenes generees")

        # 2. Generation images reelles ComfyUI/Emi2
        print(f"[IMAGES] Generation ComfyUI pour {slug}...")
        img_results = generate_images_for_scenes(
            scenes, work_dir / "images", subject.get("style_prompt", "")
        )
        success_imgs = sum(1 for r in img_results if r["status"] in ("success", "cached"))
        print(f"[IMAGES] {success_imgs}/{len(scenes)} images disponibles")
        if success_imgs < len(scenes):
            missing = [r["scene"] for r in img_results if r["status"] not in ("success", "cached")]
            raise RuntimeError(f"Images manquantes: {missing}")

        for s in scenes:
            s["source_image"] = str(work_dir / "images" / f"{s['id']}.png")

        self._db_update(slug, "storyboard_ready", output_dir=str(work_dir))

        # 3. Production V5
        output_dir = self.project / "output" / f"auto-{slug}-v5"
        self._db_update(slug, "rendering", output_dir=str(output_dir))

        try:
            result = self._run_v5_production(scenes, storyboard_path, slug, output_dir, work_dir)

            mp4_path = result['mp4']
            sha = hashlib.sha256(Path(mp4_path).read_bytes()).hexdigest()
            self._db_update(slug, 'completed', output_dir=str(output_dir), mp4_path=mp4_path,
                           sha256=sha, qc_passed=1)

            elapsed = time.time() - start_time
            print(f"[DONE] {slug} en {elapsed:.1f}s | MP4: {mp4_path}")
            return {**result, 'elapsed_sec': elapsed, 'status': 'completed'}

        except Exception as e:
            self._db_update(slug, 'failed', error=str(e))
            raise
    def _run_v5_production(self, scenes, storyboard_path: Path, slug: str, output_dir: Path, work_dir: Path) -> Dict:
        """Execute le pipeline V5 sur le storyboard."""
        out = output_dir.resolve()
        out.mkdir(parents=True, exist_ok=True)
        for sub in ("images", "audio", "shots", "metadata", "subtitles", "review"):
            (out / sub).mkdir(exist_ok=True)

        # Verifier images pre-generees
        for s in scenes:
            img = Path(s.get("source_image", ""))
            if not img.exists():
                raise FileNotFoundError(f"Image manquante pour {s['id']}: {img}")

        # Narration
        timings = fp.synthesize_voice(self.project, scenes, out / "audio", self.ffprobe)
        goal = TARGET_SECONDS
        frames = fp.allocate_frames(timings, goal, FPS)
        starts = []
        t = 0.0
        for count in frames:
            starts.append(t)
            t += count / FPS

        # Sous-titres alignes sur les durees phonetiques reelles du WAV
        voice_durations = []
        for s in scenes:
            wav = out / "audio" / (s["id"] + ".wav")
            if wav.exists():
                import wave
                with wave.open(str(wav), 'rb') as wf:
                    dur = wf.getnframes() / wf.getframerate()
                voice_durations.append(round(dur, 3))
            else:
                voice_durations.append(round(TARGET_SECONDS / len(scenes), 3))
        ass_path, timings_json, nsubs = self._generate_aligned_subtitles(
            scenes, voice_durations, out / "subtitles"
        )

        # Rendu shots
        enc = fp.pick_ffmpeg_encoder(self.ffmpeg, False)
        framing_spec_path = _V5_DIR.parent.parent / "TikTokHistoryFactory_finish_v5" / "framing-v5.json"
        framing_spec = json.loads(framing_spec_path.read_text(encoding="utf-8-sig"))
        shots = []
        shot_manifest = []
        for j, s in enumerate(scenes):
            n = frames[j]
            first = max(1, round(n * 0.48))
            second = n - first

            # Shot A
            img_a = s["source_image"]
            dest_a = out / "shots" / f"{s['id']}_A.mp4"
            framing_a = dict(framing_spec["defaults"]["A"])
            framing_a.update(framing_spec["shots"].get(f"{s['id']}_A", {}))
            status_a = fp.render_shot(self.ffmpeg, img_a, dest_a, first, enc, 0, framing=framing_a)
            shots.append(dest_a)
            shot_manifest.append({"scene": s["id"], "file": str(dest_a), "image": img_a,
                                   "frames": first, "duration_sec": round(first / FPS, 3), "status": status_a})

            # Shot B
            img_b = out / "images" / (s["id"] + "_B.png")
            if not img_b.exists():
                img_b = img_a
            dest_b = out / "shots" / f"{s['id']}_B.mp4"
            framing_b = dict(framing_spec["defaults"]["B"])
            framing_b.update(framing_spec["shots"].get(f"{s['id']}_B", {}))
            status_b = fp.render_shot(self.ffmpeg, str(img_b), dest_b, second, enc, 1, framing=framing_b)
            shots.append(dest_b)
            shot_manifest.append({"scene": s["id"], "file": str(dest_b), "image": str(img_b),
                                   "frames": second, "duration_sec": round(second / FPS, 3), "status": status_b})

        # Audio
        wav = out / "audio" / "narration.wav"
        fp.merge_audio(self.ffmpeg, [(s, out / "audio" / (s["id"] + ".wav"), frames[i]) for i, s in enumerate(scenes)],
                        frames, wav, out / "audio")

        # Extrait controle
        preview = out / "review" / "control-excerpt.mp4"
        fp.render_video(self.ffmpeg, shots, wav, ass_path, preview, False, target=min(12, goal))
        preview_media = qv.media_probe(self.ffprobe, preview)
        preview_audio = qv.audio_signal(self.ffmpeg, preview)
        fp.generate_review_frames(self.ffmpeg, preview, out / "review" / "control-frames", target=min(12, goal))
        print(f"[CONTROL] Extrait OK: peak={preview_audio['peak_dbfs']} dBFS")

        # MP4 final
        result = out / f"{slug}-v5-final.mp4"
        fp.render_video(self.ffmpeg, shots, wav, ass_path, result, False, target=goal)
        fp.generate_contact_sheet(shot_manifest, out / "storyboard.jpg")
        fp.generate_review_frames(self.ffmpeg, result, out / "review", target=goal)

        # QC
        qc = qv.check_final(self.ffmpeg, self.ffprobe, result, timings_json,
                            ass_path, goal=goal)

        # Rapports
        report = {
            "episode": slug, "result": str(result), "qc": qc,
            "shots": len(shots), "subtitles": nsubs,
            "technical_checks_passed": qc["technical_checks_passed"]
        }
        (out / "metadata" / "finish-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        return {"mp4": str(result), "qc": qc, "shots": len(shots), "subtitles": nsubs}
    def _generate_aligned_subtitles(self, scenes, voice_durations, subtitles_dir):
        """Genere les sous-titres FR alignes par duree phonetique reelle."""
        subtitles_dir.mkdir(parents=True, exist_ok=True)
        fontpath = str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arialbd.ttf")

        all_subs = []
        cumulative_time = 0.0
        for i, s in enumerate(scenes):
            dur = voice_durations[i]
            segs = sa.build_subtitle_segments(
                s["narration_en"], s["narration_fr"], dur, min_duration=MIN_SHOT_DURATION
            )
            for seg in segs:
                seg['start_sec'] = round(cumulative_time + seg['start_sec'], 3)
                seg['end_sec'] = round(cumulative_time + seg['end_sec'], 3)
                all_subs.append(seg)
            cumulative_time += dur

        ass_path = subtitles_dir / "subtitles-fr.ass"
        self._write_ass(all_subs, str(ass_path), fontpath)

        srt_path = subtitles_dir / "subtitles-fr.srt"
        self._write_srt(all_subs, str(srt_path))

        # Format compatible quality_v5: start/end/lines
        cues = []
        for seg in all_subs:
            cues.append({"start": seg["start_sec"], "end": seg["end_sec"], "lines": [seg["text"]]})
        timings_json = subtitles_dir / "timings.json"
        with open(timings_json, "w", encoding="utf-8") as f:
            json.dump(cues, f, indent=2, ensure_ascii=False)

        return ass_path, timings_json, len(all_subs)

    def _write_ass(self, segments, ass_path, fontpath):
        """Ecrit un fichier ASS avec style TikTok pour QC."""
        lines = []
        lines.append("[Script Info]")
        lines.append("Title: TikTokHistoryFactory Subtitles")
        lines.append("ScriptType: v4.00+")
        lines.append("PlayResX: 1080")
        lines.append("PlayResY: 1920")
        lines.append("ScaledBorderAndShadow: yes")
        lines.append("")
        lines.append("[V4+ Styles]")
        lines.append("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding")
        fontname = Path(fontpath).stem if fontpath else "Arial"
        lines.append(f"Style: TikTok,{fontname},70,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,4,0,2,40,40,360,1")
        lines.append("")
        lines.append("[Events]")
        lines.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")

        def fmt(t):
            h = int(t // 3600)
            m = int((t % 3600) // 60)
            s = t % 60
            return f"{h}:{m:02d}:{s:05.2f}"

        for i, seg in enumerate(segments, 1):
            start = fmt(seg["start_sec"])
            end = fmt(seg["end_sec"])
            text = seg["text"].replace(chr(10), "\\N")
            lines.append(f"Dialogue: 0,{start},{end},TikTok,,0,0,0,,{text}")

        Path(ass_path).write_text("\n".join(lines), encoding="utf-8")
    def _write_srt(self, segments, srt_path):
        """Ecrit un fichier SRT."""
        lines = []
        for i, seg in enumerate(segments, 1):
            start = seg["start_sec"]
            end = seg["end_sec"]
            lines.append(str(i))
            def fmt(t):
                h = int(t // 3600)
                m = int((t % 3600) // 60)
                s = int(t % 60)
                ms = int((t % 1) * 1000)
                return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
            lines.append(f"{fmt(start)} --> {fmt(end)}")
            lines.append(seg["text"])
            lines.append("")
        Path(srt_path).write_text("\n".join(lines), encoding="utf-8")

    def run_batch(self, count: int = 3) -> List[Dict]:
        """Produit une file de N épisodes automatiquement."""
        completed_hashes = self._db_get_completed_hashes()
        available = self.catalogue.list_available(completed_hashes)
        results = []
        for i in range(min(count, len(available))):
            subject = available[i]
            print(f'\n=== BATCH [{i+1}/{count}] : {subject["slug"]} ===')
            try:
                result = self.produce_subject(subject['slug'])
                results.append({'slug': subject['slug'], 'status': 'completed', **result})
            except Exception as e:
                print(f'[FAIL] {subject["slug"]}: {e}')
                results.append({'slug': subject['slug'], 'status': 'failed', 'error': str(e)})
        return results


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Moteur de production autonome TikTokHistoryFactory V5')
    ap.add_argument('--project', type=Path, default=DEFAULT_ROOT)
    ap.add_argument('--subject', type=str, help='Slug du sujet à produire')
    ap.add_argument('--batch', type=int, default=0, help='Nombre d\'épisodes à produire en file')
    ap.add_argument('--status', action='store_true', help='Afficher le statut des productions')
    a = ap.parse_args()

    engine = AutoProductionEngine(a.project)

    if a.status:
        import sqlite3
        conn = sqlite3.connect(str(engine.db_path))
        c = conn.cursor()
        c.execute('SELECT slug, status, mp4_path, qc_passed FROM auto_productions ORDER BY started_at DESC')
        for row in c.fetchall():
            mp4 = row[2] or ""
            print(f"{row[0]:30s} | {row[1]:15s} | QC={row[3]} | {mp4}")
        conn.close()
        sys.exit(0)

    if a.subject:
        result = engine.produce_subject(a.subject)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif a.batch > 0:
        results = engine.run_batch(a.batch)
        print('\n=== RÉSULTATS BATCH ===')
        for r in results:
            print(f"{r['slug']:30s} | {r['status']}")
    else:
        # Par défaut: produire le premier sujet disponible
        available = engine.catalogue.list_available(engine._db_get_completed_hashes())
        if not available:
            print('Aucun sujet disponible. Tous les sujets du catalogue ont été produits.')
            sys.exit(0)
        subject = available[0]
        print(f'Sujet sélectionné automatiquement: {subject["slug"]}')
        result = engine.produce_subject(subject['slug'])
        print(json.dumps(result, indent=2, ensure_ascii=False))
