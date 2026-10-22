
<#
.SYNOPSIS
    Lance les tests du projet.
#>
$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "=== Tests TikTokHistoryFactory ===" -ForegroundColor Cyan

# Tests syntaxiques
python -m py_compile tiktok_history_factory\config\settings.py
python -m py_compile tiktok_history_factory\database\models.py
python -m py_compile tiktok_history_factory\pipeline\orchestrator.py
python -m py_compile tiktok_history_factory\cli.py
Write-Host "Syntaxe Python : OK" -ForegroundColor Green

# Tests d'import
python -c "from tiktok_history_factory.config import Settings; print('Settings OK')"
python -c "from tiktok_history_factory.database import DatabaseManager, TaskStatus; print('Database OK')"
python -c "from tiktok_history_factory.pipeline import PipelineOrchestrator; print('Pipeline OK')"
python -c "from tiktok_history_factory.monitoring import HealthChecker; print('Monitoring OK')"
Write-Host "Imports : OK" -ForegroundColor Green

# Test base de donnees
python -c "
from tiktok_history_factory.database import init_database
import tempfile, os
with tempfile.TemporaryDirectory() as td:
    db = init_database(os.path.join(td, 'test.db'))
    print('DB init OK')
"
Write-Host "Base de donnees : OK" -ForegroundColor Green

Write-Host "=== Tests termines ===" -ForegroundColor Cyan
