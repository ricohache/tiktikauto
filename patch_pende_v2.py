import re

with open("src/v5_factory/auto_engine.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace Pende template with longer narrations
old_pende = """            'pende-revolt-1931': {
                'scenes': [
                    (\"In May nineteen thirty-one, the Pende people of the Belgian Congo rose up.\", \"En mai 1931, le peuple Pende du Congo belge se souleva.\"),
                    (\"Forced labor and head taxes had pushed them to the brink.\", \"Le travail force et les impots de capitation les avaient pousses au bord du gouffre.\"),
                    (\"Concession companies exploited their land with brutal efficiency.\", \"Les societes de concession exploitaient leurs terres avec une brutalite efficace.\"),
                    (\"Pende men refused to surrender their harvests to colonial agents.\", \"Les hommes Pende refuserent de livrer leurs recoltes aux agents coloniaux.\"),
                    (\"On June eighth, territorial agent Maximilien Balot was killed.\", \"Le 8 juin, l'agent territorial Maximilien Balot fut tue.\"),
                    (\"The colonial administration responded with machine guns and mass reprisals.\", \"L'administration coloniale repondit par des mitrailleuses et des represailles massives.\"),
                    (\"Hundreds of Pende were killed in the weeks that followed.\", \"Des centaines de Pende furent tues dans les semaines qui suivirent.\"),
                    (\"Villages were burned and survivors were driven into the forest.\", \"Des villages furent brules et les survivants furent pousses dans la foret.\"),
                    (\"The Leverhulme plantations continued operations as if nothing had happened.\", \"Les plantations Leverhulme continuerent leurs operations comme si de rien n'etait.\"),
                    (\"The Pende revolt was buried in colonial archives for decades.\", \"La revolte Pende fut enfouie dans les archives coloniales pendant des decennies.\"),
                    (\"Their resistance is part of Africa's forgotten fight for dignity.\", \"Leur resistance fait partie de la lutte oubliee de l'Afrique pour sa dignite.\")
                ]
            }"""

new_pende = """            'pende-revolt-1931': {
                'scenes': [
                    (\"In May nineteen thirty-one, the Pende people of the Belgian Congo rose up. For years, forced labor and crushing taxes had reduced their villages to starvation. Rubber companies took their land and their dignity. The breaking point had finally arrived.\", \"En mai 1931, le peuple Pende du Congo belge se souleva. Pendant des annees, le travail force et les impots ecrasants avaient reduit leurs villages a la famine. Les companies du caoutchouc prirent leurs terres et leur dignite. Le point de rupture etait enfin arrive.\"),
                    (\"Colonial officials demanded heavy head taxes from every adult man. Workers had to spend weeks harvesting rubber instead of tending their own fields. Families went hungry while plantation profits soared. The injustice was unbearable.\", \"Les fonctionnaires coloniaux exigeaient de lourds impots de capitation de chaque homme adulte. Les travailleurs devaient passer des semaines a recolter le caoutchouc au lieu de cultiver leurs propres champs. Les familles souffraient de la faim pendant que les profits des plantations s'envolaient. L'injustice etait insupportable.\"),
                    (\"The Societe de concession companies ruled vast territories with brutal efficiency. Armed guards enforced impossible quotas on villagers who had no choice but to comply. Resistance meant punishment, humiliation, and worse. Colonial power knew no mercy.\", \"Les societes de concession regissaient de vastes territoires avec une brutalite efficace. Des gardes armes imposaient des quotas impossibles aux villageois qui n'avaient d'autre choix que d'obtempérer. La resistance signifiait punition, humiliation et pire. Le pouvoir colonial ne connaissait aucune pitie.\"),
                    (\"In early June, Pende men finally refused to surrender their harvests to colonial agents. They gathered in the villages and declared that no more rubber would be collected at gunpoint. The colonial administration saw this as open rebellion. The response would be devastating.\", \"En debut juin, les hommes Pende refuserent enfin de livrer leurs recoltes aux agents coloniaux. Ils se rassemblerent dans les villages et declarerent qu'aucun caoutchouc ne serait plus recolte sous la menace des armes. L'administration coloniale vit cela comme une rebellion ouverte. La reponse serait devastatrice.\"),
                    (\"On June eighth, nineteen thirty-one, territorial agent Maximilien Balot arrived in Kilamba village to collect taxes. An angry crowd confronted him. Shots were fired, and Balot was killed. His death gave the colonial administration the pretext it wanted for massive retaliation.\", \"Le 8 juin 1931, l'agent territorial Maximilien Balot arriva au village de Kilamba pour collecter les impots. Une foule en colere le confronta. Des coups de feu furent tires, et Balot fut tue. Sa mort donna a l'administration coloniale le pretexte qu'elle cherchait pour une retaliation massive.\"),
                    (\"The colonial administration responded with machine guns, artillery, and mass reprisals. Columns of Force Publique soldiers swept through Pende territory. Hundreds of villagers were rounded up, beaten, and executed without trial. The violence was systematic and deliberate.\", \"L'administration coloniale repondit par des mitrailleuses, de l'artillerie et des represailles massives. Des colonnes de soldats de la Force Publique balayerent le territoire Pende. Des centaines de villageois furent rassembles, battus et executes sans proces. La violence etait systematique et deliberée.\"),
                    (\"In the weeks that followed, hundreds of Pende men, women, and children were killed. Many were shot trying to flee into the forest. Others were burned alive in their homes. The exact number of victims remains unknown, but estimates range into the thousands. Colonial records were deliberately destroyed.\", \"Dans les semaines qui suivirent, des centaines d'hommes, de femmes et d'enfants Pende furent tues. Beaucoup furent abattus en tentant de fuir dans la foret. D'autres furent brules vifs dans leurs maisons. Le nombre exact de victimes reste inconnu, mais les estimations vont jusqu'aux milliers. Les archives coloniales furent deliberement detruites.\"),
                    (\"Entire villages were burned to the ground by colonial troops. Survivors fled into the dense forest, leaving behind everything they owned. Families were separated, and many starved in hiding. The land that had sustained them for generations was now a scarred and silent wasteland.\", \"Des villages entiers furent reduits en cendres par les troupes coloniales. Les survivants s'enfuirent dans la dense foret, abandonnant tout ce qu'ils possedaient. Les familles furent separees, et beaucoup moururent de faim dans leur cachette. La terre qui les avait sustenus pendant des generations etait maintenant un terrain sterile et silencieux.\"),
                    (\"While the blood still flowed, the Leverhulme rubber and palm oil plantations continued their operations as if nothing had happened. British and Belgian businessmen profited from the forced labor that had triggered the revolt. The system of exploitation remained firmly in place, untouched by the massacre.\", \"Pendant que le sang coulait encore, les plantations de caoutchouc et d'huile de palme Leverhulme continuerent leurs operations comme si de rien n'etait. Des hommes d'affaires britanniques et belges profiterent du travail force qui avait declenche la revolte. Le systeme d'exploitation restait fermement en place, intact malgre le massacre.\"),
                    (\"The Pende revolt was systematically buried in colonial archives for decades. Belgian officials classified the records and denied the scale of the killings. It was only in the late twentieth century that historians began reconstructing the truth from scattered documents. The silence was a second violence.\", \"La revolte Pende fut systematiquement enfouie dans les archives coloniales pendant des decennies. Les fonctionnaires belges classerent les dossiers et nierent l'ampleur des tueries. Ce n'est que vers la fin du vingtieme siecle que des historiens commencerent a reconstruire la verite a partir de documents epars. Le silence fut une seconde violence.\"),
                    (\"Today, the Pende revolt remains a powerful symbol of Africa's forgotten fight for dignity. It reminds us that behind every colonial statistic, there were human beings who refused to surrender. Their resistance lives on in the memory of those who demand justice for the crimes of colonialism.\", \"Aujourd'hui, la revolte Pende reste un symbole puissant de la lutte oubliee de l'Afrique pour sa dignite. Elle nous rappelle que derriere chaque statistique coloniale, il y avait des etres humains qui refusaient de se rendre. Leur resistance survit dans la memoire de ceux qui reclament justice pour les crimes du colonialisme.\")
                ]
            }"""

if old_pende in content:
    content = content.replace(old_pende, new_pende)
    print("PENDE_TEMPLATE_REPLACED")
else:
    print("PENDE_TEMPLATE_NOT_FOUND")
    exit(1)

# Fix subtitle method to use actual WAV durations instead of scene durations
old_sig = "def _generate_aligned_subtitles(self, scenes, scene_durations, subtitles_dir):"
if old_sig in content:
    content = content.replace(old_sig, "def _generate_aligned_subtitles(self, scenes, voice_durations, subtitles_dir):")
    print("SUBTITLE_SIG_REVERTED")

# Fix the call site
old_call = """        # Sous-titres alignes sur les durees video reelles (pas WAV)
        scene_durations = [round(f / FPS, 3) for f in frames]
        ass_path, timings_json, nsubs = self._generate_aligned_subtitles(
            scenes, scene_durations, out / "subtitles"
        )"""

new_call = """        # Sous-titres alignes sur les durees phonetiques reelles du WAV
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
        )"""

if old_call in content:
    content = content.replace(old_call, new_call)
    print("SUBTITLE_CALL_FIXED")
else:
    print("SUBTITLE_CALL_NOT_FOUND")

# Fix the method body
old_body = "        for i, s in enumerate(scenes):\n            dur = scene_durations[i]"
if old_body in content:
    content = content.replace(old_body, "        for i, s in enumerate(scenes):\n            dur = voice_durations[i]")
    print("SUBTITLE_BODY_FIXED")

with open("src/v5_factory/auto_engine.py", "w", encoding="utf-8") as f:
    f.write(content)

print("ALL_PATCHES_APPLIED")
