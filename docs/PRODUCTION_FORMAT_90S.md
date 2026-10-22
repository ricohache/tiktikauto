# Format de production définitif — décision du 19 octobre 2026

La cible définitive est désormais **90 secondes**, narration anglaise et sous-titres français :

| Partie | Fenêtre cible | Texte anglais indicatif à 120–145 mots/minute |
|---|---|---|
| Introduction accrocheuse et vérifiable | 0–15 s | 30–36 mots |
| Développement historique explicatif | 15–75 s | 120–145 mots |
| Conclusion marquante et sourcée | 75–90 s | 30–36 mots |

Le profil version3 est dans `data/production/format-v3-90s.json` et son chargeur/validateur
dans `tiktok_history_factory/config/production.py`. `writer_brief()` fournit les fenêtres
et budgets indicatifs à un futur scénario de production. Ces budgets ne remplacent pas
la mesure du WAV anglais. Aucune accélération artificielle n’est autorisée.

Ce contrat prépare le format futur : il n’active ni moteur de production90s, ni planificateur,
ni publication. L’adaptation du montage et du scénario90s reste postérieure à l’acceptation
du style et à un dossier historique adéquat. Le pilote court, ses commandes de reprise,
ses critères techniques, son audio et ses sous-titres restent conservés.

La décision graphique est enregistrée séparément : aucune variante A/B/C approuvée,
B uniquement référence comparative, C écartée. Un nouveau checkpoint spécialisé reste
un candidat expérimental jusqu’à validation explicite du propriétaire.
