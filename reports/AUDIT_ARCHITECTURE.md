# AUDIT ARCHITECTURAL — TikTokHistoryFactory
Date : 2026-10-16 21:27:59

## A. ENVIRONNEMENTS IDENTIFIES

| Environnement | Description | Acces Codex | Acces Hote |
|---------------|-------------|-------------|------------|
| A. Codex (dev) | Environnement execution IA | Controle total | Aucun |
| B. Windows Hote | PC Windows 11, RTX 4060 | RESTREINT | Controle total |
| C. Python Projet | .venv dans TikTokHistoryFactory | OUI | OUI (si venv active) |
| D. Python ComfyUI | python_embeded dans ComfyUI | NON (socket bloque) | OUI |
| E. Services locaux | 127.0.0.1:8188, :11434 | BLOQUE (WinError 10013) | OUI |
| F. Internet | PyPI, HuggingFace, CivitAI | BLOQUE (getaddrinfo failed) | OUI |

## B. ARCHITECTURE EXISTANTE vs CIBLE

| Composant | Cible | Existant | Ecart | Statut |
|-----------|-------|----------|-------|--------|
| Structure modulaire | 10 packages Python | 10 packages OK | Aucun | RÉUSSI |
| SQLite natif | 7 tables, migrations | 7 tables, pas de migrations explicites | Mineur | RÉUSSI |
| Config .env | Variables completes | Variables OK | Aucun | RÉUSSI |
| Settings Python | Relecture dynamique | Classe avec __init__ | Aucun | RÉUSSI |
| Orchestrateur | Pipeline 22 etats | Pipeline 22 etats | Aucun | RÉUSSI |
| CLI Python | argparse complet | argparse OK | Aucun | RÉUSSI |
| Scripts PS | 13 scripts | 13 scripts OK | Aucun | RÉUSSI |
| FFmpeg | Montage video | MP4 1080x1920 genere | Aucun | RÉUSSI |
| ComfyUI | Serveur API actif | Installe, modeles vides | Modeles manquants | À VALIDER SUR HÔTE |
| Checkpoint manga | Modele sein historique | Aucun | Modele a telecharger | À VALIDER SUR HÔTE |
| Wan 2.2 | Animation TI2V-5B | Non installe | Modele a telecharger | À VALIDER SUR HÔTE |
| Piper TTS | Voix fr_FR | Non installe | Binaire + modele a telecharger | À VALIDER SUR HÔTE |
| Ollama Cloud | kimi-k3:cloud | Configurable, pas de cle API | Cle API a renseigner | À VALIDER SUR HÔTE |
| Planificateur Windows | 3 taches/jour | Script schedule.ps1 | Non active | À VALIDER SUR HÔTE |
| Publication TikTok | LOCAL_EXPORT defaut | LOCAL_EXPORT defaut | Aucun | RÉUSSI |

## C. PROBLEMES IDENTIFIES

1. **Confusion environnements** : Codex a traite le PC hote comme un environnement mono-block.
   Correction : separer clairement dev (Codex) et runtime (hote).

2. **Pas de script bootstrap autonome** : L'installation repose sur des etapes manuelles.
   Correction : creer bootstrap-host.ps1 idempotent.

3. **Modeles non telecharges** : ComfyUI est vide.
   Correction : script de telechargement avec verification d'integrite.

4. **Piper non installe** : Aucun binaire ni modele.
   Correction : telechargement et configuration automatiques.

5. **Ollama Cloud** : Pas de cle API configuree.
   Correction : detecter l'authentification existante, ne pas imposer de nouvelle cle.

6. **Pas de validation E2E** : Tests unitaires mais pas de test video complet.
   Correction : script de test d'integration complet.

## D. ARCHITECTURE CORRIGEE

`
Environnement Codex (Dev)          Environnement Windows Hote (Runtime)
    |                                        |
    | Git push / pull                        | Git clone / pull
    | Code review                            |
    | Architecture                           | Execution
    | Tests statiques                        | Tests reels
    |                                        |
    v                                        v
[Code Python, PS, docs]  ----------->  [PC Windows 11]
                                           |
         .---------------------------------.
         |                                   |
    [Python Projet]                    [ComfyUI Portable]
    - Orchestrateur                    - Python 3.13 embarque
    - SQLite                           - PyTorch CUDA
    - FFmpeg                           - Checkpoint manga
    - Ollama Cloud API                 - Wan 2.2
    - Piper TTS                        - Generation GPU
    - CLI / Scripts                    - API HTTP 127.0.0.1:8188
`

## E. SEPARATION DES RESPONSABILITES

Codex (ce que je fais) :
- Architecture, code, tests statiques
- Scripts d'installation autonomes
- Documentation, workflows JSON
- Configuration templates

Hote Windows (ce que tu fais) :
- Executer bootstrap-host.ps1 UNE FOIS
- Renseigner .env avec secrets
- Télécharger les modèles (si auto-telechargement impossible)
- Lancer le pilote

## F. MATRICE DE CONFORMITE

| ID | Exigence | Statut Codex | Statut Hote | Action |
|----|----------|-------------|-------------|--------|
| A1 | Architecture modulaire | RÉUSSI | À VALIDER | Verifier imports |
| A2 | SQLite persistence | RÉUSSI | À VALIDER | Test transactions |
| A3 | FFmpeg montage | RÉUSSI | À VALIDER | Generer video |
| B1 | ComfyUI demarrage | SIMULÉ | À VALIDER | Executer bootstrap |
| B2 | Checkpoint manga | NON FAIT | À VALIDER | Telecharger |
| B3 | Wan 2.2 | NON FAIT | À VALIDER | Telecharger + tester |
| C1 | Piper TTS fr_FR | NON FAIT | À VALIDER | Installer + tester |
| C2 | Ollama Cloud | CONFIGURÉ | À VALIDER | Tester avec cle |
| D1 | Planificateur | SCRIPTS OK | À VALIDER | Activer |
| E1 | Publication TikTok | LOCAL_EXPORT | À VALIDER | Verifier modes |
| F1 | Video pilote complete | SIMULÉ | À VALIDER | Assembler E2E |
