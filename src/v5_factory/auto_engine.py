"""Moteur de production autonome pour TikTokHistoryFactory V5.
Orchestre la chaîne complète : sujet → storyboard → images → narration → sous-titres → MP4.
"""
from __future__ import annotations
import argparse
import re
import hashlib
import json
import math
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

    def _db_insert(self, slug: str, title_en: str, title_fr: str, run_id: str = ""):
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        try:
            c.execute('INSERT OR IGNORE INTO auto_productions (slug, title_en, title_fr, status, run_id) VALUES (?,?,?,?,?)',
                     (slug, title_en, title_fr, 'pending', run_id))
            conn.commit()
            # Ensure run_id is set even if row already existed
            if run_id:
                c.execute("UPDATE auto_productions SET run_id=? WHERE slug=? AND (run_id IS NULL OR run_id='')", (run_id, slug))
                conn.commit()
        except Exception as e:
            print(f'[DB INSERT WARN] {e}')
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
        templates =         templates = {
            'patrice-lumumba-assassinat': {
                'scenes': [
                    ("On January seventeenth, nineteen sixty-one, Patrice Lumumba was captured. He was the Congo's first elected prime minister.", "Le 17 janvier 1961, Patrice Lumumba fut capturé. Il était le premier ministre démocratiquement élu du Congo."),
                    ("Belgian officers and Congolese rivals had conspired against him for months. They feared his vision of a truly independent Congo.", "Des officiers belges et des rivaux congolais avaient conspiré contre lui pendant des mois. Ils craignaient sa vision d'un Congo véritablement indépendant."),
                    ("He was taken to Katanga, where separatist forces held him prisoner. Foreign mercenaries supervised his brutal detention.", "Il fut emmené au Katanga, où des forces séparatistes le détenaient prisonnier. Des mercenaires étrangers supervisèrent sa détention brutale."),
                    ("Lumumba was tortured and humiliated in front of foreign officers. A Belgian officer later admitted supervising the execution.", "Lumumba fut torturé et humilié devant des officiers étrangers. Un officier belge admit plus tard avoir supervisé l'exécution."),
                    ("Lumumba and two ministers were shot by a firing squad. Their bodies were dissolved in acid to erase all evidence.", "Lumumba et deux ministres furent fusillés. Leurs corps furent dissous dans l'acide pour effacer toute preuve."),
                    ("The CIA had targeted him as a dangerous communist threat. American and Belgian intelligence coordinated his elimination.", "La CIA l'avait ciblé comme une dangereuse menace communiste. Les services secrets américains et belges coordonnèrent son élimination."),
                    ("Belgium officially apologized only in two thousand two. No one was ever prosecuted for this state-sponsored murder.", "La Belgique ne s'excusa officiellement qu'en 2002. Personne ne fut jamais poursuivi pour ce meurtre commandité par l'État."),
                    ("His assassination ended the democratic hopes of the Congolese people. Foreign powers installed a dictator to protect mining interests.", "Son assassinat mit fin aux espoirs démocratiques du peuple congolais. Les puissances étrangères installèrent un dictateur pour protéger leurs intérêts miniers."),
                    ("His voice calling for African dignity still echoes across the continent. Pan-African movements draw inspiration from his sacrifice.", "Sa voix réclamant la dignité africaine résonne encore sur le continent. Les mouvements panafricanistes s'inspirent de son sacrifice."),
                    ("The United Nations inquiry confirmed Belgian complicity in his death. The full truth remains buried in classified archives.", "L'enquête des Nations Unies confirma la complicité belge dans sa mort. La vérité complète reste enfouie dans des archives classifiées."),
                    ("Patrice Lumumba gave his life for a vision of Africa that still inspires millions. His death remains one of colonialism's darkest chapters.", "Patrice Lumumba donna sa vie pour une vision de l'Afrique qui inspire encore des millions. Sa mort reste l'un des chapitres les plus sombres du colonialisme."),
                ]
            },
            'ruben-um-nyobe': {
                'scenes': [
                    ("In nineteen forty-eight, Ruben Um Nyobè helped found the UPC. This party demanded Cameroon's independence from French colonial rule.", "En 1948, Ruben Um Nyobè contribua à fonder l'UPC. Ce parti exigeait l'indépendance du Cameroun face à la domination coloniale française."),
                    ("He was a teacher, a trade unionist, and a committed opponent. French authorities saw the UPC as a dangerous threat to their empire.", "Il était instituteur, syndicaliste et opposant résolu. Les autorités françaises voyaient l'UPC comme une menace dangereuse pour leur empire."),
                    ("The UPC demanded full independence immediately. Other parties accepted gradual autonomy that preserved French dominance.", "L'UPC exigeait l'indépendance totale immédiatement. Les autres partis acceptaient une autonomie progressive qui préservait la domination française."),
                    ("French authorities responded with brutal repression and mass arrests. Um Nyobè was forced into hiding in the bush.", "Les autorités françaises répondirent par une répression brutale et des arrestations massives. Um Nyobè fut contraint à se cacher dans la brousse."),
                    ("He became known as the invisible prime minister. From the forest, he led armed resistance against colonial forces.", "On le surnomma le Premier ministre invisible. Depuis la forêt, il dirigeait la résistance armée contre les forces coloniales."),
                    ("In nineteen fifty-eight, Um Nyobè was ambushed and killed. French forces never returned his body to his grieving family.", "En 1958, Um Nyobè fut tué en embuscade. Les forces françaises ne rendirent jamais son corps à sa famille endeuillée."),
                    ("After his death, the UPC continued its struggle for years. The French army waged a brutal war against the independence fighters.", "Après sa mort, l'UPC poursuivit son combat pendant des années. L'armée française mena une guerre brutale contre les combattants pour l'indépendance."),
                    ("Thousands of Cameroonian civilians died in the hidden repression. France classified the archives and denied the massacres.", "Des milliers de civils camerounais périrent dans cette répression cachée. La France classifia les archives et nia les massacres."),
                    ("Today, Um Nyobè is honored as a father of Cameroonian independence. His portrait finally hangs in the National Assembly.", "Aujourd'hui, Um Nyobè est honoré comme un père de l'indépendance camerounaise. Son portrait trône enfin à l'Assemblée nationale."),
                    ("His story reminds us that self-determination demands courage. The fight for justice often comes at a terrible personal cost.", "Son histoire nous rappelle que l'autodétermination exige du courage. La lutte pour la justice a souvent un terrible prix personnel."),
                    ("Ruben Um Nyobè gave his life for a Cameroon that would finally be free. His sacrifice still inspires African liberation movements.", "Ruben Um Nyobè donna sa vie pour un Cameroun qui serait enfin libre. Son sacrifice inspire encore les mouvements de libération africains."),
                ]
            },
            'tirailleurs-senegalais': {
                'scenes': [
                    ("For over a century, West African tirailleurs fought in France's colonial wars. From Verdun to Indochina, they served in brutal conflicts.", "Pendant plus d'un siècle, les tirailleurs d'Afrique de l'Ouest combattirent dans les guerres coloniales de la France. De Verdun à l'Indochine, ils servirent dans des conflits brutaux."),
                    ("They were promised equality, but faced systematic discrimination. Their pensions remained frozen at colonial rates for decades.", "On leur avait promis l'égalité, mais ils firent face à une discrimination systématique. Leurs pensions restèrent gelées aux taux coloniaux pendant des décennies."),
                    ("After independence, many veterans were abandoned by France. The French state broke its promises to these loyal soldiers.", "Après l'indépendance, de nombreux anciens combattants furent abandonnés par la France. L'État français rompit ses promesses envers ces soldats loyaux."),
                    ("They marched on Paris in nineteen forty-four, demanding fair treatment. French police fired on the peaceful demonstration.", "Ils marchèrent sur Paris en 1944, réclamant un traitement équitable. La police française tira sur la manifestation pacifique."),
                    ("African soldiers were often the first to die on European battlefields. Their courage was celebrated but their dignity was denied.", "Les soldats africains furent souvent les premiers à mourir sur les champs de bataille européens. Leur courage fut célébré mais leur dignité fut niée."),
                    ("France only officially recognized their contribution in the two thousands. Decades of protests forced the state to acknowledge them.", "La France ne reconnut officiellement leur contribution qu'au début des années 2000. Des décennies de protestations forcèrent l'État à les reconnaître."),
                    ("Their pensions remained frozen at colonial rates until two thousand ten. Many veterans died in poverty, forgotten by the nation they served.", "Leurs pensions restèrent gelées aux taux coloniaux jusqu'en 2010. Beaucoup de vétérans moururent dans la pauvreté, oubliés par la nation qu'ils avaient servie."),
                    ("The last surviving tirailleurs passed away without justice. Their sacrifice symbolizes the forgotten debts of colonial powers.", "Les derniers tirailleurs survivants s'éteignirent sans justice. Leur sacrifice symbolise les dettes oubliées des puissances coloniales."),
                    ("Their story reveals the hypocrisy of the French republican promise. Liberty and equality stopped at the color line.", "Leur histoire révèle l'hypocrisie de la promesse républicaine française. La liberté et l'égalité s'arrêtaient à la ligne de couleur."),
                    ("Remembering them means recognizing colonial history is not finished. Their descendants still demand reparations today.", "Se souvenir d'eux, c'est reconnaître que l'histoire coloniale n'est pas terminée. Leurs descendants réclament encore des réparations aujourd'hui."),
                    ("The tirailleurs gave everything for France. France still owes them memory, dignity, and justice.", "Les tirailleurs donnèrent tout pour la France. La France leur doit encore mémoire, dignité et justice."),
                ]
            },
            'thomas-sankara-1987': {
                'scenes': [
                    ("On October fifteenth, nineteen eighty-seven, Burkina Faso lost its president. Thomas Sankara, the upright man, was assassinated.", "Le 15 octobre 1987, le Burkina Faso perdait son président. Thomas Sankara, l'homme intègre, fut assassiné."),
                    ("Sankara had transformed his nation in just four years. He fought corruption and promoted women's rights across the country.", "Sankara avait transformé sa nation en seulement quatre ans. Il avait combattu la corruption et promu les droits des femmes à travers le pays."),
                    ("He launched a massive vaccination campaign against polio. Millions of children were saved from preventable diseases.", "Il lança une campagne massive de vaccination contre la polio. Des millions d'enfants furent sauvés de maladies évitables."),
                    ("His revolutionary policies threatened French economic influence. Paris saw his independent socialism as a dangerous example.", "Ses politiques révolutionnaires menaçaient l'influence économique française. Paris voyait son socialisme indépendant comme un exemple dangereux."),
                    ("A group of officers led by Blaise Compaoré launched a coup. Compaoré was Sankara's closest friend and comrade-in-arms.", "Un groupe d'officiers mené par Blaise Compaoré lança un coup d'État. Compaoré était l'ami le plus proche et le camarade d'armes de Sankara."),
                    ("Sankara was killed at the age of thirty-seven. Twelve of his loyal companions were also murdered that same day.", "Sankara fut tué à l'âge de trente-sept ans. Douze de ses compagnons loyaux furent également assassinés ce même jour."),
                    ("Compaoré ruled for twenty-seven years after eliminating his rival. He reversed most of Sankara's progressive reforms.", "Compaoré régna vingt-sept ans après avoir éliminé son rival. Il renversa la plupart des réformes progressistes de Sankara."),
                    ("Sankara's legacy lives on in youth movements across Africa. His ideas about self-reliance inspire new generations.", "L'héritage de Sankara survit dans les mouvements de jeunesse en Afrique. Ses idées d'autosuffisance inspirent les nouvelles générations."),
                    ("In two thousand twenty-two, a military tribunal convicted Compaoré in absentia. But Sankara's assassination remains officially unpunished.", "En 2022, un tribunal militaire condamna Compaoré par contumace. Mais l'assassinat de Sankara reste officiellement impuni."),
                    ("His revolutionary courage challenged both local elites and foreign powers. Africa still needs leaders who put people before profit.", "Son courage révolutionnaire défiait à la fois les élites locales et les puissances étrangères. L'Afrique a encore besoin de leaders qui placent les gens avant le profit."),
                    ("Thomas Sankara proved that radical change is possible in Africa. His memory belongs to everyone who fights for justice.", "Thomas Sankara prouva que le changement radical est possible en Afrique. Sa mémoire appartient à tous ceux qui luttent pour la justice."),
                ]
            },
            'guerre-algerie-violences': {
                'scenes': [
                    ("Between nineteen fifty-four and nineteen sixty-two, Algeria bled. The war of independence claimed hundreds of thousands of lives.", "Entre 1954 et 1962, l'Algérie saignait. La guerre d'indépendance fit des centaines de milliers de morts."),
                    ("French forces used torture as a systematic weapon against civilians. The French army destroyed entire villages and massacred populations.", "Les forces françaises utilisaient la torture comme arme systématique contre les civils. L'armée française détruisit des villages entiers et massacra des populations."),
                    ("The FLN also carried out brutal reprisals against suspected collaborators. The violence touched every family on both sides.", "Le FLN mena également des représailles brutales contre des suspects de collaboration. La violence toucha chaque famille des deux côtés."),
                    ("The harkis, Algerian fighters who sided with France, were abandoned. Many were massacred by the FLN after independence.", "Les harkis, combattants algériens pro-français, furent abandonnés. Beaucoup furent massacrés par le FLN après l'indépendance."),
                    ("Others fled to France in poverty and discrimination. They lived in camps for decades, rejected by both nations.", "D'autres fuirent vers la France dans la pauvreté et la discrimination. Ils vécurent dans des camps pendant des décennies, rejetés par les deux nations."),
                    ("The Algerian War was kept out of French schoolbooks for forty years. An entire generation grew up without knowing this history.", "La guerre d'Algérie fut occultée des manuels scolaires français pendant quarante ans. Toute une génération grandit sans connaître cette histoire."),
                    ("In two thousand five, France passed a law recognizing colonial violence. But the wounds of colonization remain deep and open.", "En 2005, la France adopta une loi reconnaissant les violences coloniales. Mais les blessures de la colonisation restent profondes et ouvertes."),
                    ("Torture was not the act of a few rogue soldiers. It was institutionalized and covered up by the French state itself.", "La torture n'était pas l'acte de quelques soldats isolés. Elle fut institutionnalisée et couverte par l'État français lui-même."),
                    ("Survivors of the Battle of Algiers still seek truth and recognition. The French state continues to classify key documents.", "Les survivants de la bataille d'Alger recherchent encore la vérité et la reconnaissance. L'État français continue de classer des documents clés."),
                    ("The wounds of colonization run deep on both shores. Memory is not about dividing people but preventing future crimes.", "Les blessures de la colonisation sont profondes des deux côtés de la Méditerranée. La mémoire ne sert pas à diviser mais à prévenir de futurs crimes."),
                    ("History must remember so it never happens again. The Algerian War reminds us that imperialism leaves scars for generations.", "L'histoire doit se souvenir pour que cela ne se reproduise jamais. La guerre d'Algérie rappelle que l'impérialisme laisse des cicatrices pour des générations."),
                ]
            },
            'pende-revolt-1931': {
                'scenes': [
                    ("In May nineteen thirty-one, the Pende people rose up. Years of forced labor and crushing taxes had destroyed their villages.", "En mai 1931, le peuple Pende se souleva. Des années de travail forcé et d'impôts écrasants avaient détruit leurs villages."),
                    ("Colonial officials demanded heavy taxes from every adult man. Workers harvested rubber while their own fields starved.", "Les fonctionnaires exigeaient de lourds impôts de chaque homme adulte. Les travailleurs récoltaient du caoutchouc pendant que leurs champs souffraient."),
                    ("Concession companies ruled with brutal efficiency. Armed guards enforced impossible quotas on the villagers.", "Les sociétés de concession régnaient avec une brutalité efficace. Des gardes armés imposaient des quotas impossibles aux villageois."),
                    ("In early June, Pende men refused to surrender rubber. They declared an end to forced collection at gunpoint.", "En début juin, les hommes Pende refusèrent de livrer du caoutchouc. Ils déclarèrent la fin de la collecte forcée sous la menace des armes."),
                    ("On June eighth, agent Balot arrived in Kilamba village. An angry crowd confronted him and he was killed.", "Le 8 juin, l'agent Balot arriva au village de Kilamba. Une foule en colère le confronta et il fut tué."),
                    ("The administration responded with machine guns and artillery. Force Publique soldiers swept through Pende territory.", "L'administration répondit par des mitrailleuses et de l'artillerie. Des soldats de la Force Publique balayèrent le territoire Pende."),
                    ("Hundreds of Pende were killed in the following weeks. Many were shot while fleeing into the dense forest.", "Des centaines de Pende furent tués dans les semaines suivantes. Beaucoup furent abattus en fuyant dans la forêt dense."),
                    ("Entire villages were burned by colonial troops. Survivors fled into the forest, abandoning everything they owned.", "Des villages entiers furent brûlés par les troupes coloniales. Les survivants s'enfuirent dans la forêt, abandonnant tout ce qu'ils possédaient."),
                    ("The Leverhulme plantations continued as if nothing had happened. British and Belgian businessmen profited from forced labor.", "Les plantations Leverhulme continuèrent comme si de rien n'était. Des hommes d'affaires britanniques et belges profitèrent du travail forcé."),
                    ("The revolt was buried in colonial archives for decades. Officials denied the scale of the systematic massacre.", "La révolte fut enfouie dans les archives coloniales pendant des décennies. Les fonctionnaires nièrent l'ampleur du massacre systématique."),
                    ("The Pende revolt symbolizes Africa's forgotten fight for dignity. Their resistance lives on in those who demand colonial justice.", "La révolte Pende symbolise la lutte oubliée de l'Afrique pour sa dignité. Leur résistance survit chez ceux qui réclament justice pour le colonialisme."),
                ]
            },
            'madagascar-revolt-1947': {
                'scenes': [
                    ("On March twenty-ninth, nineteen forty-seven, the Malagasy people rose up. They rebelled against decades of French colonial exploitation.", "Le 29 mars 1947, le peuple malgache se souleva. Il se révolta contre des décennies d'exploitation coloniale française."),
                    ("Armed insurgents seized control of military posts across the island. France responded by deploying troops and bombing villages.", "Des insurges armés prirent le contrôle de postes militaires à travers l'île. La France répondit en déployant des troupes et en bombardant des villages."),
                    ("Thousands of Malagasy were killed, far more than France ever admitted. Official estimates deliberately minimized the death toll.", "Des milliers de Malgaches furent tués, bien plus que la France ne l'admit jamais. Les estimations officielles minimisèrent délibérément le nombre de morts."),
                    ("The repression lasted for months with summary executions. Entire villages were burned and survivors were sent to detention camps.", "La répression dura des mois avec des exécutions sommaires. Des villages entiers furent brûlés et les survivants furent envoyés dans des camps de détention."),
                    ("The leaders of the MDRM were arrested and tried in rigged courts. Many received harsh sentences for demanding their freedom.", "Les dirigeants du MDRM furent arrêtés et jugés dans des tribunaux truqués. Beaucoup reçurent des peines sévères pour avoir réclamé leur liberté."),
                    ("Survivors were deported to forced labor camps on Nosy Lava island. Families were torn apart and many died in captivity.", "Les survivants furent déportés dans des camps de travail forcé sur l'île de Nosy Lava. Des familles furent déchirées et beaucoup moururent en captivité."),
                    ("France maintained silence about the repression for decades. Colonial archives were classified to hide the truth from the world.", "La France maintint le silence sur la répression pendant des décennies. Les archives coloniales furent classifiées pour cacher la vérité au monde."),
                    ("It was only in nineteen ninety that France began opening its archives. Historians finally began reconstructing the truth.", "Ce n'est qu'en 1990 que la France commença à ouvrir ses archives. Les historiens commencèrent enfin à reconstruire la vérité."),
                    ("Today, the uprising remains a symbol of Malagasy independence. It reminds us that colonial archives still hide painful truths.", "Aujourd'hui, le soulèvement reste un symbole de l'indépendance malgache. Il nous rappelle que les archives coloniales cachent encore des vérités douloureuses."),
                    ("The Malagasy people paid a terrible price for daring to resist. Their sacrifice paved the way for independence in nineteen sixty.", "Le peuple malgache paya un terrible prix pour avoir osé résister. Leur sacrifice ouvrit la voie à l'indépendance en 1960."),
                    ("This story proves that colonial violence must be remembered. Only truth can heal the wounds of history.", "Cette histoire prouve que la violence coloniale doit être mémorisée. Seule la vérité peut guérir les blessures de l'histoire."),
                ]
            },
            'biafra-war-1967': {
                'scenes': [
                    ("In nineteen sixty-seven, the Igbo people of eastern Nigeria declared independence from the federal state. They named their new nation the Republic of Biafra.", "En 1967, le peuple Igbo de l'est du Nigeria proclama son indépendance de l'état fédéral. Il nomma sa nouvelle nation la République du Biafra."),
                    ("Nigeria responded with brutal war. British and Soviet weapons flooded Lagos to crush the secession.", "Le Nigeria répondit par une guerre brutale. Des armes britanniques et soviétiques affluèrent à Lagos pour écraser la sécession."),
                    ("A total blockade cut off Biafra from all food and medicine supplies. Two million civilians, mostly children, died from starvation and preventable disease.", "Un blocus total coupa le Biafra de toute nourriture et de tous médicaments. Deux millions de civils, principalement des enfants, moururent de famine."),
                    ("Images of starving children with distended bellies shocked the world. It was the first televised famine.", "Les images d'enfants affamés au ventre ballonné choquèrent le monde. Ce fut la première famine télévisée."),
                    ("Organizations tried airlifts to break the blockade. But Nigerian forces shot at relief planes.", "Des organisations tentèrent des ponts aériens pour briser le blocus. Mais les forces nigérianes tiraient sur les avions de secours."),
                    ("The world watched in horror but did little to stop the killing. Britain supplied weapons to Nigeria while publicly calling for peace and humanitarian access.", "Le monde regardait avec horreur sans rien faire pour arrêter le massacre. La Grande-Bretagne fournissait des armes tout en appelant à la paix."),
                    ("Biafran soldiers fought with courage. Without weapons or food, they could not win.", "Les soldats biafrais combattirent avec courage. Sans armes ni nourriture, ils ne purent gagner."),
                    ("In nineteen seventy, Biafra surrendered. The dream of Igbo independence was crushed by force.", "En 1970, le Biafra se rendit. Le rêve d'indépendance Igbo fut écrasé par la force."),
                    ("The war's legacy poisons politics. Ethnic tensions remain unresolved.", "L'héritage de la guerre empoisonne la politique. Les tensions ethniques demeurent non résolues."),
                    ("The oil beneath Biafran soil became Nigeria's greatest resource. But the Niger Delta people still live in crushing poverty and environmental pollution.", "Le pétrole sous le sol biafrais devint la plus grande ressource du Nigeria. Mais le peuple du delta du Niger vit toujours dans la pauvreté et la pollution."),
                    ("Biafra teaches that independence without protection is fragile. The world must not stand silent.", "Le Biafra enseigne que l'indépendance sans protection est fragile. Le monde ne doit pas rester silencieux."),
                ]
            },
            'namibia-genocide-1904': {
                'scenes': [
                    ("Between nineteen o four and nineteen o eight, German colonial forces exterminated the Herero and Nama peoples. It was the first genocide of the twentieth century.", "Entre 1904 et 1908, les forces coloniales allemandes exterminèrent les peuples Herero et Nama. Ce fut le premier génocide du vingtième siècle."),
                    ("German settlers seized fertile lands and forced indigenous peoples onto reservations. Cattle were confiscated and families starved.", "Des colons allemands s'emparèrent des terres fertiles et forcèrent les peuples autochtones sur des réserves. Le bétail fut confisqué et des familles moururent de faim."),
                    ("When the Herero rose up in January nineteen o four, German troops responded with extermination orders. Men, women, and children were hunted across the desert.", "Lorsque les Herero se soulevèrent en janvier 1904, les troupes allemandes répondirent par des ordres d'extermination. Hommes, femmes et enfants furent traqués à travers le désert."),
                    ("Survivors were driven into the Kalahari Desert. Those who did not die of thirst were imprisoned in concentration camps.", "Les survivants furent poussés dans le désert du Kalahari. Ceux qui ne moururent pas de soif furent emprisonnés dans des camps de concentration."),
                    ("German scientists conducted experiments on prisoners. Skulls were sent to Germany for racial research.", "Des scientifiques allemands menèrent des expériences sur les prisonniers. Des crânes furent envoyés en Allemagne pour des recherches raciales."),
                    ("The Nama people also rebelled and suffered the same fate. Their leader Hendrik Witbooi was killed in combat.", "Le peuple Nama se révolta également et subit le même sort. Leur chef Hendrik Witbooi fut tué au combat."),
                    ("Germany recognized the genocide only in twenty twenty-one. Reparations were promised but not fully delivered.", "L'Allemagne ne reconnut le génocide qu'en 2021. Des réparations furent promises mais non entièrement versées."),
                    ("Namibia gained independence in nineteen ninety. Descendants still demand justice and land restitution.", "La Namibie accéda à l'indépendance en 1990. Les descendants réclament encore justice et restitution des terres."),
                    ("The genocide reminds us colonial racism was deliberate. It was systematic and rooted in European ideology.", "Le génocide nous rappelle que le racisme colonial était délibéré. Il était systématique et ancré dans l'idéologie européenne."),
                ]
            },
        }

        # Charger templates supplementaires depuis tmp_templates.json
        tmp_path = self.project / "tmp_templates.json"
        if tmp_path.exists():
            extra = json.loads(tmp_path.read_text(encoding="utf-8"))
            for eslug, data in extra.items():
                scenes_extra = []
                for s in data.get("scenes", []):
                    if isinstance(s, dict):
                        scenes_extra.append((s["narration_en"], s["narration_fr"]))
                    else:
                        scenes_extra.append(s)
                templates[eslug] = {"scenes": scenes_extra}
        slug = subject['slug']
        tmpl = templates.get(slug)
        if not tmpl:
            # Tentative: dossier pre_sourced avec scenes detaillees
            pre_path = self.project / 'data' / 'pre_sourced' / slug / 'dossier.json'
            if pre_path.exists():
                dossier = json.loads(pre_path.read_text(encoding='utf-8'))
                scenes_data = dossier.get('scenes', [])
                if len(scenes_data) >= 6:
                    tmpl = {'scenes': [(s['narration_en'], s['narration_fr']) for s in scenes_data]}
                    print(f'[STORYBOARD] Using pre_sourced scenes for {slug}')
                else:
                    print(f'[STORYBOARD] pre_sourced dossier for {slug} has only {len(scenes_data)} scenes, need at least 6')
        if not tmpl:
            # Tentative: generation automatique a partir du resume detaille
            summary_en = subject.get('summary_en', '')
            summary_fr = subject.get('summary_fr', '')
            if len(summary_en) < 300 or len(summary_fr) < 300:
                raise RuntimeError(
                    f'No template for {slug} and summary too short ({len(summary_en)} EN / {len(summary_fr)} FR chars). '
                    f'Provide a template, a pre_sourced dossier with scenes, or a detailed summary (min 300 chars each).'
                )
            sentences_en = [s.strip() for s in re.split(r'(?<=[.!?])\s+', summary_en) if len(s.strip()) > 10]
            sentences_fr = [s.strip() for s in re.split(r'(?<=[.!?])\s+', summary_fr) if len(s.strip()) > 10]
            # Supprimer les phrases dupliquees exactes
            seen_en = set()
            uniq_en = []
            for s in sentences_en:
                if s not in seen_en:
                    seen_en.add(s)
                    uniq_en.append(s)
            seen_fr = set()
            uniq_fr = []
            for s in sentences_fr:
                if s not in seen_fr:
                    seen_fr.add(s)
                    uniq_fr.append(s)
            sentences_en = uniq_en
            sentences_fr = uniq_fr
            # Objectif: 11-13 scenes pour 22-26 shots sur ~90s
            MIN_SCENES = 11
            MAX_SCENES = 13
            if len(sentences_en) < MIN_SCENES or len(sentences_fr) < MIN_SCENES:
                raise RuntimeError(
                    f'No template for {slug} and not enough sentences in summary ({len(sentences_en)} EN / {len(sentences_fr)} FR). '
                    f'Need at least {MIN_SCENES} unique sentences per language for auto-generation (target 22-26 shots).'
                )
            paired = list(zip(sentences_en, sentences_fr))
            if len(paired) < MIN_SCENES:
                raise RuntimeError(
                    f'No template for {slug} and misaligned summaries ({len(sentences_en)} EN / {len(sentences_fr)} FR). '
                    f'Need at least {MIN_SCENES} aligned sentence pairs for auto-generation.'
                )
            paired = paired[:MAX_SCENES]
            tmpl = {'scenes': paired}
            print(f'[STORYBOARD] Auto-generated scenes from summary for {slug} ({len(paired)} scenes, no repetition, target 22-26 shots)')

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

    def produce_subject(self, slug: str, run_id: str = "") -> Dict:
        """Produit un episode complet a partir du catalogue."""
        start_time = time.time()
        subject = self.catalogue.get_by_slug(slug)
        if not subject:
            raise ValueError(f"Sujet inconnu: {slug}")

        self._db_insert(slug, subject["title_en"], subject["title_fr"], run_id)
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
        base_dir = self.project / "output" / f"auto-{slug}-v5"
        if base_dir.exists():
            ts = time.strftime("%Y%m%d_%H%M%S")
            output_dir = self.project / "output" / f"auto-{slug}-v5_{ts}"
        else:
            output_dir = base_dir
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

        # Mesurer les durees vocales reelles
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

        # Ajuster goal exactement a la narration reelle + 1s marge
        total_voice = sum(voice_durations)
        goal = math.ceil(total_voice) + 1

        # Allouer les frames APRES ajustement de goal
        frames = fp.allocate_frames(timings, goal, FPS)
        starts = []
        t = 0.0
        for count in frames:
            starts.append(t)
            t += count / FPS
        ass_path, timings_json, nsubs = self._generate_aligned_subtitles(
            scenes, voice_durations, out / "subtitles", goal
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
    def _generate_aligned_subtitles(self, scenes, voice_durations, subtitles_dir, goal=TARGET_SECONDS):
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
            text = seg["text"]
            # Decouper en 2 lignes max si texte trop long (>50 chars)
            if len(text) > 50:
                words = text.split()
                mid = len(words) // 2
                line1 = " ".join(words[:mid])
                line2 = " ".join(words[mid:])
                text = line1 + "\\N" + line2

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
