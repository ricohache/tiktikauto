import json
from pathlib import Path

NEW_TEMPLATES = {
    'patrice-lumumba-assassinat': {
        'scenes': [
            (\"On January seventeenth, nineteen sixty-one, Patrice Lumumba was captured. He was the Congo's first elected prime minister.\", \"Le 17 janvier 1961, Patrice Lumumba fut capturé. Il était le premier ministre démocratiquement élu du Congo.\"),
            (\"Belgian officers and Congolese rivals had conspired against him for months. They feared his vision of a truly independent Congo.\", \"Des officiers belges et des rivaux congolais avaient conspiré contre lui pendant des mois. Ils craignaient sa vision d'un Congo véritablement indépendant.\"),
            (\"He was taken to Katanga, where separatist forces held him prisoner. Foreign mercenaries supervised his brutal detention.\", \"Il fut emmené au Katanga, où des forces séparatistes le détenaient prisonnier. Des mercenaires étrangers supervisèrent sa détention brutale.\"),
            (\"Lumumba was tortured and humiliated in front of foreign officers. A Belgian officer later admitted supervising the execution.\", \"Lumumba fut torturé et humilié devant des officiers étrangers. Un officier belge admit plus tard avoir supervisé l'exécution.\"),
            (\"Lumumba and two ministers were shot by a firing squad. Their bodies were dissolved in acid to erase all evidence.\", \"Lumumba et deux ministres furent fusillés. Leurs corps furent dissous dans l'acide pour effacer toute preuve.\"),
            (\"The CIA had targeted him as a dangerous communist threat. American and Belgian intelligence coordinated his elimination.\", \"La CIA l'avait ciblé comme une dangereuse menace communiste. Les services secrets américains et belges coordonnèrent son élimination.\"),
            (\"Belgium officially apologized only in two thousand two. No one was ever prosecuted for this state-sponsored murder.\", \"La Belgique ne s'excusa officiellement qu'en 2002. Personne ne fut jamais poursuivi pour ce meurtre commandité par l'État.\"),
            (\"His assassination ended the democratic hopes of the Congolese people. Foreign powers installed a dictator to protect mining interests.\", \"Son assassinat mit fin aux espoirs démocratiques du peuple congolais. Les puissances étrangères installèrent un dictateur pour protéger leurs intérêts miniers.\"),
            (\"His voice calling for African dignity still echoes across the continent. Pan-African movements draw inspiration from his sacrifice.\", \"Sa voix réclamant la dignité africaine résonne encore sur le continent. Les mouvements panafricanistes s'inspirent de son sacrifice.\"),
            (\"The United Nations inquiry confirmed Belgian complicity in his death. The full truth remains buried in classified archives.\", \"L'enquête des Nations Unies confirma la complicité belge dans sa mort. La vérité complète reste enfouie dans des archives classifiées.\"),
            (\"Patrice Lumumba gave his life for a vision of Africa that still inspires millions. His death remains one of colonialism's darkest chapters.\", \"Patrice Lumumba donna sa vie pour une vision de l'Afrique qui inspire encore des millions. Sa mort reste l'un des chapitres les plus sombres du colonialisme.\")
        ]
    },
    'ruben-um-nyobe': {
        'scenes': [
            (\"In nineteen forty-eight, Ruben Um Nyobè helped found the UPC. This party demanded Cameroon's independence from French colonial rule.\", \"En 1948, Ruben Um Nyobè contribua à fonder l'UPC. Ce parti exigeait l'indépendance du Cameroun face à la domination coloniale française.\"),
            (\"He was a teacher, a trade unionist, and a committed opponent. French authorities saw the UPC as a dangerous threat to their empire.\", \"Il était instituteur, syndicaliste et opposant résolu. Les autorités françaises voyaient l'UPC comme une menace dangereuse pour leur empire.\"),
            (\"The UPC demanded full independence immediately. Other parties accepted gradual autonomy that preserved French dominance.\", \"L'UPC exigeait l'indépendance totale immédiatement. Les autres partis acceptaient une autonomie progressive qui préservait la domination française.\"),
            (\"French authorities responded with brutal repression and mass arrests. Um Nyobè was forced into hiding in the bush.\", \"Les autorités françaises répondirent par une répression brutale et des arrestations massives. Um Nyobè fut contraint à se cacher dans la brousse.\"),
            (\"He became known as the invisible prime minister. From the forest, he led armed resistance against colonial forces.\", \"On le surnomma le Premier ministre invisible. Depuis la forêt, il dirigeait la résistance armée contre les forces coloniales.\"),
            (\"In nineteen fifty-eight, Um Nyobè was ambushed and killed. French forces never returned his body to his grieving family.\", \"En 1958, Um Nyobè fut tué en embuscade. Les forces françaises ne rendirent jamais son corps à sa famille endeuillée.\"),
            (\"After his death, the UPC continued its struggle for years. The French army waged a brutal war against the independence fighters.\", \"Après sa mort, l'UPC poursuivit son combat pendant des années. L'armée française mena une guerre brutale contre les combattants pour l'indépendance.\"),
            (\"Thousands of Cameroonian civilians died in the hidden repression. France classified the archives and denied the massacres.\", \"Des milliers de civils camerounais périrent dans cette répression cachée. La France classifia les archives et nia les massacres.\"),
            (\"Today, Um Nyobè is honored as a father of Cameroonian independence. His portrait finally hangs in the National Assembly.\", \"Aujourd'hui, Um Nyobè est honoré comme un père de l'indépendance camerounaise. Son portrait trône enfin à l'Assemblée nationale.\"),
            (\"His story reminds us that self-determination demands courage. The fight for justice often comes at a terrible personal cost.\", \"Son histoire nous rappelle que l'autodétermination exige du courage. La lutte pour la justice a souvent un terrible prix personnel.\"),
            (\"Ruben Um Nyobè gave his life for a Cameroon that would finally be free. His sacrifice still inspires African liberation movements.\", \"Ruben Um Nyobè donna sa vie pour un Cameroun qui serait enfin libre. Son sacrifice inspire encore les mouvements de libération africains.\")
        ]
    },
    'tirailleurs-senegalais': {
        'scenes': [
            (\"For over a century, West African tirailleurs fought in France's colonial wars. From Verdun to Indochina, they served in brutal conflicts.\", \"Pendant plus d'un siècle, les tirailleurs d'Afrique de l'Ouest combattirent dans les guerres coloniales de la France. De Verdun à l'Indochine, ils servirent dans des conflits brutaux.\"),
            (\"They were promised equality, but faced systematic discrimination. Their pensions remained frozen at colonial rates for decades.\", \"On leur avait promis l'égalité, mais ils firent face à une discrimination systématique. Leurs pensions restèrent gelées aux taux coloniaux pendant des décennies.\"),
            (\"After independence, many veterans were abandoned by France. The French state broke its promises to these loyal soldiers.\", \"Après l'indépendance, de nombreux anciens combattants furent abandonnés par la France. L'État français rompit ses promesses envers ces soldats loyaux.\"),
            (\"They marched on Paris in nineteen forty-four, demanding fair treatment. French police fired on the peaceful demonstration.\", \"Ils marchèrent sur Paris en 1944, réclamant un traitement équitable. La police française tira sur la manifestation pacifique.\"),
            (\"African soldiers were often the first to die on European battlefields. Their courage was celebrated but their dignity was denied.\", \"Les soldats africains furent souvent les premiers à mourir sur les champs de bataille européens. Leur courage fut célébré mais leur dignité fut niée.\"),
            (\"France only officially recognized their contribution in the two thousands. Decades of protests forced the state to acknowledge them.\", \"La France ne reconnut officiellement leur contribution qu'au début des années 2000. Des décennies de protestations forcèrent l'État à les reconnaître.\"),
            (\"Their pensions remained frozen at colonial rates until two thousand ten. Many veterans died in poverty, forgotten by the nation they served.\", \"Leurs pensions restèrent gelées aux taux coloniaux jusqu'en 2010. Beaucoup de vétérans moururent dans la pauvreté, oubliés par la nation qu'ils avaient servie.\"),
            (\"The last surviving tirailleurs passed away without justice. Their sacrifice symbolizes the forgotten debts of colonial powers.\", \"Les derniers tirailleurs survivants s'éteignirent sans justice. Leur sacrifice symbolise les dettes oubliées des puissances coloniales.\"),
            (\"Their story reveals the hypocrisy of the French republican promise. Liberty and equality stopped at the color line.\", \"Leur histoire révèle l'hypocrisie de la promesse républicaine française. La liberté et l'égalité s'arrêtaient à la ligne de couleur.\"),
            (\"Remembering them means recognizing colonial history is not finished. Their descendants still demand reparations today.\", \"Se souvenir d'eux, c'est reconnaître que l'histoire coloniale n'est pas terminée. Leurs descendants réclament encore des réparations aujourd'hui.\"),
            (\"The tirailleurs gave everything for France. France still owes them memory, dignity, and justice.\", \"Les tirailleurs donnèrent tout pour la France. La France leur doit encore mémoire, dignité et justice.\")
        ]
    },
    'thomas-sankara-1987': {
        'scenes': [
            (\"On October fifteenth, nineteen eighty-seven, Burkina Faso lost its president. Thomas Sankara, the upright man, was assassinated.\", \"Le 15 octobre 1987, le Burkina Faso perdait son président. Thomas Sankara, l'homme intègre, fut assassiné.\"),
            (\"Sankara had transformed his nation in just four years. He fought corruption and promoted women's rights across the country.\", \"Sankara avait transformé sa nation en seulement quatre ans. Il avait combattu la corruption et promu les droits des femmes à travers le pays.\"),
            (\"He launched a massive vaccination campaign against polio. Millions of children were saved from preventable diseases.\", \"Il lança une campagne massive de vaccination contre la polio. Des millions d'enfants furent sauvés de maladies évitables.\"),
            (\"His revolutionary policies threatened French economic influence. Paris saw his independent socialism as a dangerous example.\", \"Ses politiques révolutionnaires menaçaient l'influence économique française. Paris voyait son socialisme indépendant comme un exemple dangereux.\"),
            (\"A group of officers led by Blaise Compaoré launched a coup. Compaoré was Sankara's closest friend and comrade-in-arms.\", \"Un groupe d'officiers mené par Blaise Compaoré lança un coup d'État. Compaoré était l'ami le plus proche et le camarade d'armes de Sankara.\"),
            (\"Sankara was killed at the age of thirty-seven. Twelve of his loyal companions were also murdered that same day.\", \"Sankara fut tué à l'âge de trente-sept ans. Douze de ses compagnons loyaux furent également assassinés ce même jour.\"),
            (\"Compaoré ruled for twenty-seven years after eliminating his rival. He reversed most of Sankara's progressive reforms.\", \"Compaoré régna vingt-sept ans après avoir éliminé son rival. Il renversa la plupart des réformes progressistes de Sankara.\"),
            (\"Sankara's legacy lives on in youth movements across Africa. His ideas about self-reliance inspire new generations.\", \"L'héritage de Sankara survit dans les mouvements de jeunesse en Afrique. Ses idées d'autosuffisance inspirent les nouvelles générations.\"),
            (\"In two thousand twenty-two, a military tribunal convicted Compaoré in absentia. But Sankara's assassination remains officially unpunished.\", \"En 2022, un tribunal militaire condamna Compaoré par contumace. Mais l'assassinat de Sankara reste officiellement impuni.\"),
            (\"His revolutionary courage challenged both local elites and foreign powers. Africa still needs leaders who put people before profit.\", \"Son courage révolutionnaire défiait à la fois les élites locales et les puissances étrangères. L'Afrique a encore besoin de leaders qui placent les gens avant le profit.\"),
            (\"Thomas Sankara proved that radical change is possible in Africa. His memory belongs to everyone who fights for justice.\", \"Thomas Sankara prouva que le changement radical est possible en Afrique. Sa mémoire appartient à tous ceux qui luttent pour la justice.\")
        ]
    },
    'guerre-algerie-violences': {
        'scenes': [
            (\"Between nineteen fifty-four and nineteen sixty-two, Algeria bled. The war of independence claimed hundreds of thousands of lives.\", \"Entre 1954 et 1962, l'Algérie saignait. La guerre d'indépendance fit des centaines de milliers de morts.\"),
            (\"French forces used torture as a systematic weapon against civilians. The French army destroyed entire villages and massacred populations.\", \"Les forces françaises utilisaient la torture comme arme systématique contre les civils. L'armée française détruisit des villages entiers et massacra des populations.\"),
            (\"The FLN also carried out brutal reprisals against suspected collaborators. The violence touched every family on both sides.\", \"Le FLN mena également des représailles brutales contre des suspects de collaboration. La violence toucha chaque famille des deux côtés.\"),
            (\"The harkis, Algerian fighters who sided with France, were abandoned. Many were massacred by the FLN after independence.\", \"Les harkis, combattants algériens pro-français, furent abandonnés. Beaucoup furent massacrés par le FLN après l'indépendance.\"),
            (\"Others fled to France in poverty and discrimination. They lived in camps for decades, rejected by both nations.\", \"D'autres fuirent vers la France dans la pauvreté et la discrimination. Ils vécurent dans des camps pendant des décennies, rejetés par les deux nations.\"),
            (\"The Algerian War was kept out of French schoolbooks for forty years. An entire generation grew up without knowing this history.\", \"La guerre d'Algérie fut occultée des manuels scolaires français pendant quarante ans. Toute une génération grandit sans connaître cette histoire.\"),
            (\"In two thousand five, France passed a law recognizing colonial violence. But the wounds of colonization remain deep and open.\", \"En 2005, la France adopta une loi reconnaissant les violences coloniales. Mais les blessures de la colonisation restent profondes et ouvertes.\"),
            (\"Torture was not the act of a few rogue soldiers. It was institutionalized and covered up by the French state itself.\", \"La torture n'était pas l'acte de quelques soldats isolés. Elle fut institutionnalisée et couverte par l'État français lui-même.\"),
            (\"Survivors of the Battle of Algiers still seek truth and recognition. The French state continues to classify key documents.\", \"Les survivants de la bataille d'Alger recherchent encore la vérité et la reconnaissance. L'État français continue de classer des documents clés.\"),
            (\"The wounds of colonization run deep on both shores. Memory is not about dividing people but preventing future crimes.\", \"Les blessures de la colonisation sont profondes des deux côtés de la Méditerranée. La mémoire ne sert pas à diviser mais à prévenir de futurs crimes.\"),
            (\"History must remember so it never happens again. The Algerian War reminds us that imperialism leaves scars for generations.\", \"L'histoire doit se souvenir pour que cela ne se reproduise jamais. La guerre d'Algérie rappelle que l'impérialisme laisse des cicatrices pour des générations.\")
        ]
    },
    'pende-revolt-1931': {
        'scenes': [
            (\"In May nineteen thirty-one, the Pende people rose up. Years of forced labor and crushing taxes had destroyed their villages.\", \"En mai 1931, le peuple Pende se souleva. Des années de travail forcé et d'impôts écrasants avaient détruit leurs villages.\"),
            (\"Colonial officials demanded heavy taxes from every adult man. Workers harvested rubber while their own fields starved.\", \"Les fonctionnaires exigeaient de lourds impôts de chaque homme adulte. Les travailleurs récoltaient du caoutchouc pendant que leurs champs souffraient.\"),
            (\"Concession companies ruled with brutal efficiency. Armed guards enforced impossible quotas on the villagers.\", \"Les sociétés de concession régnaient avec une brutalité efficace. Des gardes armés imposaient des quotas impossibles aux villageois.\"),
            (\"In early June, Pende men refused to surrender rubber. They declared an end to forced collection at gunpoint.\", \"En début juin, les hommes Pende refusèrent de livrer du caoutchouc. Ils déclarèrent la fin de la collecte forcée sous la menace des armes.\"),
            (\"On June eighth, agent Balot arrived in Kilamba village. An angry crowd confronted him and he was killed.\", \"Le 8 juin, l'agent Balot arriva au village de Kilamba. Une foule en colère le confronta et il fut tué.\"),
            (\"The administration responded with machine guns and artillery. Force Publique soldiers swept through Pende territory.\", \"L'administration répondit par des mitrailleuses et de l'artillerie. Des soldats de la Force Publique balayèrent le territoire Pende.\"),
            (\"Hundreds of Pende were killed in the following weeks. Many were shot while fleeing into the dense forest.\", \"Des centaines de Pende furent tués dans les semaines suivantes. Beaucoup furent abattus en fuyant dans la forêt dense.\"),
            (\"Entire villages were burned by colonial troops. Survivors fled into the forest, abandoning everything they owned.\", \"Des villages entiers furent brûlés par les troupes coloniales. Les survivants s'enfuirent dans la forêt, abandonnant tout ce qu'ils possédaient.\"),
            (\"The Leverhulme plantations continued as if nothing had happened. British and Belgian businessmen profited from forced labor.\", \"Les plantations Leverhulme continuèrent comme si de rien n'était. Des hommes d'affaires britanniques et belges profitèrent du travail forcé.\"),
            (\"The revolt was buried in colonial archives for decades. Officials denied the scale of the systematic massacre.\", \"La révolte fut enfouie dans les archives coloniales pendant des décennies. Les fonctionnaires nièrent l'ampleur du massacre systématique.\"),
            (\"The Pende revolt symbolizes Africa's forgotten fight for dignity. Their resistance lives on in those who demand colonial justice.\", \"La révolte Pende symbolise la lutte oubliée de l'Afrique pour sa dignité. Leur résistance survit chez ceux qui réclament justice pour le colonialisme.\")
        ]
    },
    'madagascar-revolt-1947': {
        'scenes': [
            (\"On March twenty-ninth, nineteen forty-seven, the Malagasy people rose up. They rebelled against decades of French colonial exploitation.\", \"Le 29 mars 1947, le peuple malgache se souleva. Il se révolta contre des décennies d'exploitation coloniale française.\"),
            (\"Armed insurgents seized control of military posts across the island. France responded by deploying troops and bombing villages.\", \"Des insurges armés prirent le contrôle de postes militaires à travers l'île. La France répondit en déployant des troupes et en bombardant des villages.\"),
            (\"Thousands of Malagasy were killed, far more than France ever admitted. Official estimates deliberately minimized the death toll.\", \"Des milliers de Malgaches furent tués, bien plus que la France ne l'admit jamais. Les estimations officielles minimisèrent délibérément le nombre de morts.\"),
            (\"The repression lasted for months with summary executions. Entire villages were burned and survivors were sent to detention camps.\", \"La répression dura des mois avec des exécutions sommaires. Des villages entiers furent brûlés et les survivants furent envoyés dans des camps de détention.\"),
            (\"The leaders of the MDRM were arrested and tried in rigged courts. Many received harsh sentences for demanding their freedom.\", \"Les dirigeants du MDRM furent arrêtés et jugés dans des tribunaux truqués. Beaucoup reçurent des peines sévères pour avoir réclamé leur liberté.\"),
            (\"Survivors were deported to forced labor camps on Nosy Lava island. Families were torn apart and many died in captivity.\", \"Les survivants furent déportés dans des camps de travail forcé sur l'île de Nosy Lava. Des familles furent déchirées et beaucoup moururent en captivité.\"),
            (\"France maintained silence about the repression for decades. Colonial archives were classified to hide the truth from the world.\", \"La France maintint le silence sur la répression pendant des décennies. Les archives coloniales furent classifiées pour cacher la vérité au monde.\"),
            (\"It was only in nineteen ninety that France began opening its archives. Historians finally began reconstructing the truth.\", \"Ce n'est qu'en 1990 que la France commença à ouvrir ses archives. Les historiens commencèrent enfin à reconstruire la vérité.\"),
            (\"Today, the uprising remains a symbol of Malagasy independence. It reminds us that colonial archives still hide painful truths.\", \"Aujourd'hui, le soulèvement reste un symbole de l'indépendance malgache. Il nous rappelle que les archives coloniales cachent encore des vérités douloureuses.\"),
            (\"The Malagasy people paid a terrible price for daring to resist. Their sacrifice paved the way for independence in nineteen sixty.\", \"Le peuple malgache paya un terrible prix pour avoir osé résister. Leur sacrifice ouvrit la voie à l'indépendance en 1960.\"),
            (\"This story proves that colonial violence must be remembered. Only truth can heal the wounds of history.\", \"Cette histoire prouve que la violence coloniale doit être mémorisée. Seule la vérité peut guérir les blessures de l'histoire.\")
        ]
    }
}


def format_templates(templates):
    lines = []
    lines.append('        templates = {')
    for slug, data in templates.items():
        lines.append(f"            '{slug}': {{")
        lines.append("                'scenes': [")
        for en, fr in data['scenes']:
            # Escape quotes for Python source
            en_escaped = en.replace('\"', '\\\"')
            fr_escaped = fr.replace('\"', '\\\"')
            lines.append(f'                    (\"{en_escaped}\", \"{fr_escaped}\"),')
        lines.append("                ]")
        lines.append("            },")
    lines.append('        }')
    return '\n'.join(lines)


src = Path(r'C:\TikTokHistoryFactory\src\v5_factory\auto_engine.py').read_text(encoding='utf-8')

# Find start and end of templates block
start_marker = '        templates = {'
start_idx = src.find(start_marker)
if start_idx < 0:
    raise ValueError('templates block not found')

# Find the matching closing brace for templates dict
brace_count = 0
end_idx = start_idx
for i in range(start_idx, len(src)):
    if src[i] == '{':
        brace_count += 1
    if src[i] == '}':
        brace_count -= 1
    if brace_count == 0:
        end_idx = i
        break

new_block = format_templates(NEW_TEMPLATES)
new_src = src[:start_idx] + new_block + src[end_idx+1:]

# Verify by counting words
import re
total_words = {}
for slug, data in NEW_TEMPLATES.items():
    total = sum(len(en.split()) for en, fr in data['scenes'])
    total_words[slug] = total

print('Templates patched successfully.')
for slug, total in total_words.items():
    print(f'  {slug}: ~{total} EN words')

Path(r'C:\TikTokHistoryFactory\src\v5_factory\auto_engine.py').write_text(new_src, encoding='utf-8')
print('Saved to auto_engine.py')
