import json
from pathlib import Path

TEMPLATES = {
    'maji-maji-rebellion-1905': {
        'title': 'The Maji Maji Rebellion and German Colonial Genocide',
        'title_fr': 'La rebellion Maji Maji et le genocide colonial allemand',
        'event_date': '1905-1907',
        'scenes': [
            {
                'narration_en': 'In nineteen o five, an anticolonial rebellion erupted in German East Africa. Spiritual leader Kinjikitile Ngwale convinced fighters that sacred water would turn bullets to water.',
                'narration_fr': 'En 1905, une rebellion anticoloniale eclata en Afrique de l\'Est allemande. Le leader spirituel Kinjikitile Ngwale convainquit les combattants que l\'eau sacree transformerait les balles en eau.',
                'image_prompt': 'Japanese 2D seinen manga panel of an African spiritual leader in traditional robes holding water in a ritual, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 8.0
            },
            {
                'narration_en': 'Ngwale united tribes suffering under brutal forced labor and heavy German taxation for over a decade.',
                'narration_fr': 'Ngwale unit des tribus qui souffraient du travail force brutal et de la lourde taxation allemande depuis plus d\'une decennie.',
                'image_prompt': 'Japanese 2D seinen manga panel of diverse African tribal warriors gathering around a central figure, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'In July nineteen o five, rebels attacked German plantations and military outposts across southern Tanganyika.',
                'narration_fr': 'En juillet 1905, les rebelles attaquerent les plantations et postes militaires allemands dans le sud de la Tanganyika.',
                'image_prompt': 'Japanese 2D seinen manga panel of African warriors charging a colonial plantation, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'Rebels destroyed cotton fields, severed telegraph lines, and repeatedly ambushed German patrols.',
                'narration_fr': 'Les rebelles detruisirent les champs de coton, couperent les lignes telegraphiques et tendirent des embuscades aux patrouilles allemandes.',
                'image_prompt': 'Japanese 2D seinen manga panel of warriors ambushing a German patrol in dense forest, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'The Germans responded with machine guns and scorched earth tactics, destroying entire villages and food supplies.',
                'narration_fr': 'Les Allemands repondirent avec des mitrailleuses et des tactiques de la terre brulee, detruisant des villages entiers et les reserves de nourriture.',
                'image_prompt': 'Japanese 2D seinen manga panel of German colonial soldiers with machine guns attacking a village, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'Germans destroyed crops and herded people into concentration camps, causing mass starvation that killed far more than combat.',
                'narration_fr': 'Les Allemands detruisirent les recoltes et rassemblerent les populations dans des camps de concentration, causant une famine de masse.',
                'image_prompt': 'Japanese 2D seinen manga panel of starving villagers in a colonial concentration camp, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'Historians estimate two hundred thousand to three hundred thousand Africans died during the two-year conflict.',
                'narration_fr': 'Les historiens estiment que deux cent mille a trois cent mille Africains perirent pendant les deux annees du conflit.',
                'image_prompt': 'Japanese 2D seinen manga panel of a devastated African landscape with skeletons and ruins, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'Ngwale was captured and hanged by the Germans in August nineteen o five, but the rebellion continued until nineteen o seven.',
                'narration_fr': 'Ngwale fut capture et pendu par les Allemands en aout 1905, mais la rebellion continua jusqu\'en 1907.',
                'image_prompt': 'Japanese 2D seinen manga panel of a captured African leader standing defiant before colonial soldiers, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'German colonial authorities faced international criticism, but little changed until Germany lost the colony after World War One.',
                'narration_fr': 'Les autorites coloniales allemandes furent critiquees a l\'international, mais peu changea jusqu\'a ce que l\'Allemagne perde la colonie apres la Premiere Guerre mondiale.',
                'image_prompt': 'Japanese 2D seinen manga panel of German colonial officials in an office, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'The Maji Maji Rebellion became a foundational symbol of Tanzanian nationalism and resistance against colonialism.',
                'narration_fr': 'La rebellion Maji Maji devint un symbole fondateur du nationalisme tanzanien et de la resistance contre le colonialisme.',
                'image_prompt': 'Japanese 2D seinen manga panel of Tanzanian people honoring a memorial statue, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'Today it is remembered as one of Africa\'s largest anticolonial uprisings, a tragic chapter of resistance and genocide.',
                'narration_fr': 'Aujourd\'hui elle est souvenir comme l\'un des plus grands soulevements anticoloniaux de l\'histoire africaine, un chapitre tragique de resistance et de genocide.',
                'image_prompt': 'Japanese 2D seinen manga panel of a modern African memorial site with people paying respects, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            }
        ]
    },
    'sharpeville-massacre-1960': {
        'title': 'The Sharpeville Massacre and the End of Nonviolence',
        'title_fr': 'Le massacre de Sharpeville et la fin de la non-violence',
        'event_date': '1960-03-21',
        'scenes': [
            {
                'narration_en': 'On March twenty-first, nineteen sixty, thousands of black South Africans gathered in Sharpeville to protest the hated pass laws.',
                'narration_fr': 'Le 21 mars 1960, des milliers de Sud-Africains noirs se rassemblerent a Sharpeville pour protester contre les lois sur les passeports.',
                'image_prompt': 'Japanese 2D seinen manga panel of a massive crowd of black South Africans gathered for protest, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'The protest was organized by the Pan Africanist Congress, calling for black people to leave passes at home and surrender at police stations.',
                'narration_fr': 'La manifestation fut organisee par le Congres panafricaniste, appelant les Noirs a laisser leurs passeports chez eux et a se rendre a la police.',
                'image_prompt': 'Japanese 2D seinen manga panel of organizers speaking to a crowd, distributing pamphlets, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'Between five thousand and seven thousand unarmed demonstrators assembled peacefully at the Sharpeville police station to face arrest.',
                'narration_fr': 'Entre cinq mille et sept mille manifestants desarmes s\'assemblerent paisiblement au poste de police de Sharpeville.',
                'image_prompt': 'Japanese 2D seinen manga panel of unarmed protesters standing peacefully before a police station, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'The heavily armed and nervous police opened fire without warning when some protesters pressed forward.',
                'narration_fr': 'La police lourdement armee et nerveuse ouvrit le feu sans avertissement quand certains manifestants avancerent.',
                'image_prompt': 'Japanese 2D seinen manga panel of police raising rifles at protesters, dramatic moment of tension, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'They fired for forty seconds, shooting most people in the back as they fled. Sixty-nine were killed, including eight women and ten children.',
                'narration_fr': 'Ils tirerent pendant quarante secondes, touchant la plupart dans le dos en fuyant. Soixante-neuf furent tues, dont huit femmes et dix enfants.',
                'image_prompt': 'Japanese 2D seinen manga panel of protesters falling while fleeing from gunfire, dramatic action, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 8.0
            },
            {
                'narration_en': 'One hundred eighty were wounded, many shot in the back. The massacre shocked the world and exposed apartheid brutality.',
                'narration_fr': 'Cent quatre-vingts furent blesses, beaucoup touches dans le dos. Le massacre choqua le monde et exposa la brutalite de l\'apartheid.',
                'image_prompt': 'Japanese 2D seinen manga panel of wounded people lying on the ground while others help them, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'The South African government declared a state of emergency and banned both the African National Congress and the Pan Africanist Congress.',
                'narration_fr': 'Le gouvernement declara l\'etat d\'urgence et interdit le Congres national africain et le Congres panafricaniste.',
                'image_prompt': 'Japanese 2D seinen manga panel of government officials signing emergency decrees, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'The massacre convinced Nelson Mandela that nonviolent resistance had failed. He began organizing armed resistance through Umkhonto we Sizwe.',
                'narration_fr': 'Le massacre convainquit Nelson Mandela que la resistance non violente avait echoue. Il commenca a organiser la resistance armee.',
                'image_prompt': 'Japanese 2D seinen manga panel of Nelson Mandela in a secret meeting planning armed resistance, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'International condemnation followed. South Africa withdrew from the Commonwealth and faced economic sanctions and sporting boycotts.',
                'narration_fr': 'La condamnation internationale suivit. L\'Afrique du Sud se retira du Commonwealth et fut confrontee a des sanctions et boycotts.',
                'image_prompt': 'Japanese 2D seinen manga panel of international diplomats discussing sanctions, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'March twenty-first became the International Day for the Elimination of Racial Discrimination, transforming the global struggle.',
                'narration_fr': 'Le 21 mars devint la Journee internationale pour l\'elimination de la discrimination raciale, transformant la lutte mondiale.',
                'image_prompt': 'Japanese 2D seinen manga panel of a memorial plaque being unveiled, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'Today Sharpeville is remembered as the turning point that ended peaceful protest and launched three decades of armed struggle.',
                'narration_fr': 'Aujourd\'hui Sharpeville est souvenir comme le tournant qui mit fin a la protestation pacifique et lanca trois decennies de lutte armee.',
                'image_prompt': 'Japanese 2D seinen manga panel of a modern South African monument with people paying tribute, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            }
        ]
    },
    'chilembwe-uprising-1915': {
        'title': 'The Chilembwe Uprising Against British Colonial Rule',
        'title_fr': 'Le soulevement Chilembwe contre la domination britannique',
        'event_date': '1915-01-15',
        'scenes': [
            {
                'narration_en': 'In January nineteen fifteen, John Chilembwe, a Baptist minister in Nyasaland, led the first major uprising against British colonial rule in Central Africa.',
                'narration_fr': 'En janvier 1915, John Chilembwe, ministre baptiste au Nyassaland, mena le premier grand soulevement contre la domination britannique en Afrique centrale.',
                'image_prompt': 'Japanese 2D seinen manga panel of an African Baptist minister in early twentieth century clothing, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'Chilembwe had studied in the United States and returned deeply influenced by African American ideas of equality and self-determination.',
                'narration_fr': 'Chilembwe avait etudie aux Etats-Unis et etait revenu influence par les idees afro-americaines d\'egalite et d\'autodetermination.',
                'image_prompt': 'Japanese 2D seinen manga panel of an African man studying in an American classroom, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'Under British rule, Africans faced forced labor, racial discrimination, and heavy taxation. When World War One began, Britain conscripted African laborers.',
                'narration_fr': 'Sous la domination britannique, les Africains faisaient face au travail force, a la discrimination et a une lourde taxation. La Grande-Bretagne requisitionna aussi des travailleurs.',
                'image_prompt': 'Japanese 2D seinen manga panel of African laborers being forced to work on a colonial plantation, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'Chilembwe protested African conscription for a European war while Africans had no rights at home. His protests were ignored.',
                'narration_fr': 'Chilembwe protesta contre la conscription d\'Africains pour une guerre europeenne alors qu\'ils n\'avaient aucun droit. Ses protestations furent ignorees.',
                'image_prompt': 'Japanese 2D seinen manga panel of Chilembwe writing protest letters, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'On the night of January twenty-third, Chilembwe and two hundred followers attacked three British plantation estates, killing three owners.',
                'narration_fr': 'Dans la nuit du 23 janvier, Chilembwe et deux cents partisans attaquerent trois plantations britanniques, tuant trois proprietaires.',
                'image_prompt': 'Japanese 2D seinen manga panel of armed African rebels attacking a colonial plantation house at night, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'The rebels seized weapons, but colonial troops quickly suppressed the uprising. Chilembwe fled into the bush.',
                'narration_fr': 'Les rebelles saisirent des armes, mais les troupes coloniales reprimerent rapidement le soulevement. Chilembwe s\'enfuit dans la brousse.',
                'image_prompt': 'Japanese 2D seinen manga panel of rebels retreating into the African bush while colonial soldiers pursue, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'On February third, nineteen fifteen, Chilembwe was killed by police. His severed head was publicly displayed as a warning.',
                'narration_fr': 'Le 3 fevrier 1915, Chilembwe fut tue par la police. Sa tete tranchee fut exposee publiquement comme avertissement.',
                'image_prompt': 'Japanese 2D seinen manga panel of a defiant leader standing before armed police in the bush, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'Thirty-six rebels were killed and many imprisoned. The colonial authorities deported his congregation and destroyed his church.',
                'narration_fr': 'Trente-six rebelles furent tues et beaucoup d\'autres emprisonnes. Les autorites coloniales deportent sa congregation et detruisirent son eglise.',
                'image_prompt': 'Japanese 2D seinen manga panel of a destroyed church and dispersed African villagers, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'The British government was shocked and created the Nyasaland Native Rising Commission, acknowledging grievances but blaming African ignorance.',
                'narration_fr': 'Le gouvernement britannique fut choque et crea la Commission des soulevements indigenes, reconnaissant certains griefs mais blamant l\'ignorance africaine.',
                'image_prompt': 'Japanese 2D seinen manga panel of British officials in a formal commission hearing, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'Despite defeat, Chilembwe became a national hero of Malawi. His uprising inspired independence movements across Central Africa.',
                'narration_fr': 'Malgre la defaite, Chilembwe devint un heros national du Malawi. Son soulevement inspira les mouvements d\'independance en Afrique centrale.',
                'image_prompt': 'Japanese 2D seinen manga panel of Malawian independence leaders citing Chilembwe as inspiration, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            },
            {
                'narration_en': 'Today John Chilembwe is honored on Malawian currency. His portrait adorns the nation\'s banknotes, a symbol of resistance and dignity.',
                'narration_fr': 'Aujourd\'hui John Chilembwe est honore sur la monnaie malawienne. Son portrait orne les billets, un symbole de resistance et de dignite.',
                'image_prompt': 'Japanese 2D seinen manga panel of a modern African banknote being held, with Chilembwe\'s portrait, bold ink lines, dramatic contrast, halftone screentone dots, black and white, no text, vertical composition',
                'duration': 7.0
            }
        ]
    }
}

# Sauvegarder
with open(r'C:\TikTokHistoryFactory\tmp_templates.json', 'w', encoding='utf-8') as f:
    json.dump(TEMPLATES, f, indent=2, ensure_ascii=False)

# Verifier les comptages
for slug, data in TEMPLATES.items():
    words_en = sum(len(s['narration_en'].split()) for s in data['scenes'])
    words_fr = sum(len(s['narration_fr'].split()) for s in data['scenes'])
    print(slug + ': EN=' + str(words_en) + ' words, FR=' + str(words_fr) + ' words, scenes=' + str(len(data['scenes'])))

print('Templates updated successfully')
