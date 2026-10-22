import sys
with open('src/v5_factory/auto_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'madagascar-revolt-1947' in content:
    print('ALREADY_EXISTS')
    sys.exit(0)

marker = "'pende-revolt-1931': {"
idx = content.find(marker)
if idx == -1:
    print('MARKER_NOT_FOUND')
    sys.exit(1)

search_from = idx + 1000
close_idx = content.find('            }\n        }', search_from)
if close_idx == -1:
    print('CLOSE_NOT_FOUND')
    sys.exit(1)

insert_pos = close_idx + 13
new_template = """,
            'madagascar-revolt-1947': {
                'scenes': [
                    (\"On March twenty-ninth, nineteen forty-seven, the Malagasy people rose against French colonial rule.\", \"Le 29 mars 1947, le peuple malgache se souleva contre la domination coloniale francaise.\"),
                    (\"Armed insurgents with spears and a few rifles seized control of several military posts.\", \"Des insurges armes de sagaies et de quelques fusils prirent le controle de plusieurs postes militaires.\"),
                    (\"France responded by deploying troops and bombing inland villages.\", \"La France reagit en deployant des troupes et en bombardant les villages de l'interieur.\"),
                    (\"Thousands of Malagasy were killed, far more than official French estimates admitted.\", \"Des milliers de Malgaches furent tues, bien plus que les estimations officielles francaises ne l'admettaient.\"),
                    (\"The repression lasted for months, with summary executions and detention camps.\", \"La repression dura des mois, avec des executions sommaires et des camps de detention.\"),
                    (\"The leaders of the Malagasy Democratic Renewal Movement were arrested and tried.\", \"Les leaders du Mouvement democratique de la renovation malgache furent arretes et juges.\"),
                    (\"Survivors were deported to forced labor camps on Nosy Lava island.\", \"Les survivants furent deportes dans des camps de travail force sur l'ile de Nosy Lava.\"),
                    (\"France maintained silence for decades about the scale of the repression.\", \"La France maintint le silence pendant des decennies sur l'ampleur de la repression.\"),
                    (\"It was only in nineteen ninety that France began to open its archives on the uprising.\", \"Ce n'est qu'en 1990 que la France commenca a ouvrir ses archives sur la revolte.\"),
                    (\"Today, the nineteen forty-seven uprising remains a symbol of the struggle for Malagasy independence.\", \"Aujourd'hui, la revolte de 1947 reste un symbole de la lutte pour l'independance malgache.\"),
                    (\"This story reminds us that colonial archives still hide truths.\", \"Cette histoire rappelle que les archives coloniales cachent encore des verites.\")
                ]
            }"""

content = content[:insert_pos] + new_template + content[insert_pos:]
with open('src/v5_factory/auto_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('PATCHED_OK')
