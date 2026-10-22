
"""Interface en ligne de commande pour TikTokHistoryFactory."""
import argparse
import asyncio
import sys
from pathlib import Path

from tiktok_history_factory.config.settings import Settings
from tiktok_history_factory.pipeline.orchestrator import PipelineOrchestrator
from tiktok_history_factory.monitoring.health import HealthChecker


def cmd_init(args):
    """Initialise la base de donnees et les dossiers."""
    settings = Settings()
    Settings.ensure_directories()
    from tiktok_history_factory.database.models import DatabaseManager
    db = DatabaseManager(str(settings.DB_PATH))
    print(f"Base de donnees initialisee : {settings.DB_PATH}")
    return 0


def cmd_doctor(args):
    """Lance le diagnostic systeme."""
    settings = Settings()
    checker = HealthChecker(settings)
    report = checker.check_all()
    print(f"Sante globale : {'OK' if report['overall'] else 'PROBLEMES DETECTES'}")
    for name, check in report["checks"].items():
        status = "OK" if check["ok"] else "KO"
        print(f"  [{status}] {name}")
        if not check["ok"]:
            print(f"      -> {check.get('error', 'Erreur inconnue')}")
    return 0 if report["overall"] else 1


def cmd_enqueue(args):
    """Ajoute un sujet a la file."""
    settings = Settings()
    orchestrator = PipelineOrchestrator(settings)
    task_id = orchestrator.enqueue(
        topic_slug=args.slug,
        topic_title=args.title,
        topic_description=args.description or "",
    )
    print(f"Tache enfilee : id={task_id}")
    return 0


def cmd_run(args):
    """Execute un cycle de production."""
    settings = Settings()
    orchestrator = PipelineOrchestrator(settings)
    asyncio.run(orchestrator.run())
    return 0


def cmd_pilot(args):
    """One real reviewed pilot. No scheduler, no publishing, explicit dossier."""
    import json
    import sqlite3
    from datetime import datetime
    from tiktok_history_factory.pipeline.pilot import PilotRunner, validate_dossier
    settings = Settings()
    dossier_path = Path(args.dossier or settings.PILOT_DOSSIER)
    if args.try_wan:
        settings.PILOT_TRY_WAN = True
    try:
        dossier = validate_dossier(json.loads(dossier_path.read_text(encoding='utf-8')))
        if args.resume and not args.try_wan:
            work = Path(args.work_dir or settings.PROJECT_ROOT/'work'/('pilot-'+dossier['slug'].removesuffix('-pilote')))
            if (work/'manifest.json').is_file():
                previous = json.loads((work/'manifest.json').read_text(encoding='utf-8'))
                settings.PILOT_TRY_WAN = previous.get('options', {}).get('try_wan', previous.get('animation',{}).get('mode')=='Wan+FFmpeg')
        if args.topic and args.topic not in (dossier['slug'], dossier['title']):
            raise ValueError('Topic does not match reviewed dossier; supply --dossier for another subject')
        backup = settings.PROJECT_ROOT / 'backups' / ('before-pilot-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
        backup.mkdir(parents=True, exist_ok=True)
        if settings.DB_PATH.is_file():
            with sqlite3.connect(str(settings.DB_PATH)) as source, sqlite3.connect(str(backup/'factory.db')) as target:
                source.backup(target)
        orchestrator = PipelineOrchestrator(settings)
        task_id = orchestrator.enqueue(dossier['slug'], dossier['title'])
        result = PilotRunner(settings, orchestrator.db, task_id, dossier_path, args.work_dir).run()
        print('PILOT AWAITING REVIEW:', result['output_path'])
        return 0
    except Exception as exc:
        print('PILOT BLOCKED:', str(exc), file=sys.stderr)
        return 1


def cmd_test_image(args):
    import json
    from tiktok_history_factory.providers.comfyui_images import ComfyUIImageProvider
    from tiktok_history_factory.media.prompts import build_image_prompt, build_negative_prompt
    settings = Settings()
    dossier = json.loads(Path(settings.PILOT_DOSSIER).read_text(encoding='utf-8'))
    output = settings.PROJECT_ROOT / 'work/manual-image' / 'image.png'
    result = ComfyUIImageProvider(settings.COMFYUI_BASE_URL).generate_image(
        build_image_prompt(dossier['scenes'][0]['visual']), checkpoint=settings.COMFYUI_CHECKPOINT,
        seed=19441201, output_path=str(output), negative_prompt=build_negative_prompt(), steps=28, lora=settings.COMFYUI_LORA, strength=settings.COMFYUI_LORA_STRENGTH)
    print(result.get('status'), result.get('output_path', result.get('error')))
    return 0 if result.get('status') == 'SUCCESS' else 1


def cmd_test_wan(args):
    import json
    from tiktok_history_factory.providers.comfyui_wan import ComfyUIWanProvider
    from tiktok_history_factory.pipeline.checkpoints import exclusive_lock
    settings = Settings()
    work = settings.PROJECT_ROOT / 'work' / ('pilot-' + json.loads(Path(settings.PILOT_DOSSIER).read_text(encoding='utf-8'))['slug'].removesuffix('-pilote'))
    manifest = json.loads((work/'manifest.json').read_text(encoding='utf-8'))
    with exclusive_lock(settings.PROJECT_ROOT/'work/pilot.lock'):
        result = ComfyUIWanProvider(settings.COMFYUI_BASE_URL).generate_clip(
            manifest['stages']['images']['paths'][0],
            'Preserve the original monochrome ink drawing. Very slow camera push forward, subtle tree movement. No new objects, no people.',
            output_path=str(work/'wan/clip.mp4'), timeout=600)
    print(result.get('status'), result.get('output_path', result.get('error')), flush=True)
    return 0 if result.get('status') == 'SUCCESS' else 2


def cmd_list(args):
    """Liste les taches."""
    settings = Settings()
    orchestrator = PipelineOrchestrator(settings)
    tasks = orchestrator.list_tasks(limit=args.limit)
    print(f"{'ID':<5} {'Statut':<20} {'Sujet'}")
    print("-" * 60)
    for t in tasks:
        print(f"{t['id']:<5} {t['status']:<20} {t['topic_title'][:40]}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="TikTokHistoryFactory CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="Initialise la base de donnees")
    sub.add_parser("doctor", help="Diagnostic systeme")

    enqueue_parser = sub.add_parser("enqueue", help="Ajoute un sujet")
    enqueue_parser.add_argument("--slug", required=True)
    enqueue_parser.add_argument("--title", required=True)
    enqueue_parser.add_argument("--description", default="")

    sub.add_parser("run", help="Execute un cycle")

    pilot = sub.add_parser('pilot', help='One real pilot from a reviewed historical dossier; never publishes')
    pilot.add_argument('--dossier')
    pilot.add_argument('--topic', default='')
    pilot.add_argument('--work-dir')
    pilot.add_argument('--try-wan', action='store_true', help='One optional 17-frame Wan attempt, with automatic FFmpeg fallback')
    pilot.add_argument('--resume', action='store_true', help='Preserve the saved animation mode while resuming')
    sub.add_parser('test-image', help='One real GPU illustration, resumable')
    sub.add_parser('test-wan', help='One optional real Wan 5B attempt from the pilot reference')

    list_parser = sub.add_parser("list", help="Liste les taches")
    list_parser.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "init": cmd_init,
        "doctor": cmd_doctor,
        "enqueue": cmd_enqueue,
        "run": cmd_run,
        "pilot": cmd_pilot,
        'test-image': cmd_test_image,
        'test-wan': cmd_test_wan,
        "list": cmd_list,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
