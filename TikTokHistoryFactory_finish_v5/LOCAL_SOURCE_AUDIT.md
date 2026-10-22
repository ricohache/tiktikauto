# Limitation d'accès et état vérifié (20 octobre 2026)

- Le disque Windows `C:\TikTokHistoryFactory` **n'est pas monté** dans l'environnement de travail actuel. Aucun programme de ce paquet n'a modifié le PC Windows.
- Le fichier de Bibliothèque `concat_video_v2.mp4` a été effectivement analysé par `ffprobe` : 83,166667 secondes, une piste H.264 1080 × 1920 à 30 ips et **aucune piste audio**. Des captures aux secondes 20, 55 et 75 montrent des sous-titres déjà incrustés. **Il est interdit de l'employer comme source de montage.**
- `TikTokHistoryFactory_finish_v4.zip` a été récupéré et son code inspecté ; celui-ci ne contenait pas les 11 PNG Emi2 originaux ni les fichiers de narration WAV du PC.
- `TikTokHistoryFactory_finish_v5` est une révision de ce programme ; les tests ont été exécutés ici sur des médias synthétiques uniquement.
- Le résultat demandé, `C:\TikTokHistoryFactory\output\pilot-thiaroye-1944-90s-v5\thiaroye-1944-90s-v5-final.mp4`, est un **chemin attendu, non un fichier final observé**.
- Les prérequis bloquants pour une vraie production sont l'accès aux médias sources sur Windows, à la voix Piper et à ComfyUI/Emi2 installés localement.
