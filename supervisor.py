import os
import sys
import time
import json
import sqlite3
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
FACTORY_PATH = Path("C:/TikTokHistoryFactory")
COMFYUI_PATH = FACTORY_PATH / "ComfyUI"
OUTPUT_PATH = FACTORY_PATH / "output"
DB_PATH = FACTORY_PATH / "data" / "factory.db"
LOG_PATH = FACTORY_PATH / "logs" / "supervisor.log"
COMFYUI_URL = "http://127.0.0.1:8188"

# Logging
os.makedirs(LOG_PATH.parent, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TikTokHistoryFactory:
    def __init__(self):
        self.db_path = DB_PATH
        self.output_path = OUTPUT_PATH
        self.comfyui_url = COMFYUI_URL
        self.running = True
        
    def init_database(self):
        """Initialise la base SQLite"""
        os.makedirs(self.db_path.parent, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS video_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_slug TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                attempts INTEGER DEFAULT 0,
                error_message TEXT,
                output_path TEXT,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pipeline_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                phase TEXT,
                status TEXT,
                message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialisee")
        
    def check_comfyui(self):
        """Verifie si ComfyUI est actif"""
        try:
            import urllib.request
            req = urllib.request.Request(f"{self.comfyui_url}/system_stats")
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                gpu = data.get('devices', [{}])[0]
                logger.info(f"ComfyUI OK - GPU: {gpu.get('name', 'N/A')}")
                return True
        except Exception as e:
            logger.warning(f"ComfyUI non accessible: {e}")
            return False
            
    def start_comfyui(self):
        """Demarre ComfyUI si necessaire"""
        if self.check_comfyui():
            return True
            
        logger.info("Demarrage ComfyUI...")
        comfyui_dir = str(COMFYUI_PATH)
        python_exe = str(COMFYUI_PATH / "python_embeded" / "python.exe")
        main_py = str(COMFYUI_PATH / "ComfyUI" / "main.py")
        
        try:
            subprocess.Popen(
                [python_exe, "-s", main_py, "--windows-standalone-build", "--listen", "127.0.0.1", "--port", "8188"],
                cwd=comfyui_dir,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            logger.info("ComfyUI demarre, attente 45s...")
            time.sleep(45)
            return self.check_comfyui()
        except Exception as e:
            logger.error(f"Echec demarrage ComfyUI: {e}")
            return False
            
    def generate_manga_image(self, prompt, output_name):
        """Genere une image manga via ComfyUI API"""
        import urllib.request
        
        # Charger le workflow
        workflow_path = FACTORY_PATH / "workflows" / "comfyui" / "manga_animagine_xl.json"
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
        
        # Modifier le prompt
        for node in workflow.get('nodes', []):
            if node.get('type') == 'CLIPTextEncode' and node.get('pos', [0, 0])[1] < 400:
                node['widgets_values'] = [prompt]
        
        # Envoyer la requete
        data = json.dumps({"prompt": workflow}).encode('utf-8')
        req = urllib.request.Request(
            f"{self.comfyui_url}/prompt",
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            prompt_id = result.get('prompt_id')
            logger.info(f"Generation lancee: {prompt_id}")
        
        # Attendre la completion
        timeout = 300
        elapsed = 0
        while elapsed < timeout:
            time.sleep(10)
            elapsed += 10
            
            try:
                req = urllib.request.Request(f"{self.comfyui_url}/history/{prompt_id}")
                with urllib.request.urlopen(req, timeout=5) as response:
                    history = json.loads(response.read().decode())
                    if prompt_id in history:
                        break
            except:
                pass
                
            if elapsed % 30 < 15:
                logger.info(f"Attente generation... {elapsed}s")
        
        # Recuperer l'image
        req = urllib.request.Request(f"{self.comfyui_url}/history/{prompt_id}")
        with urllib.request.urlopen(req, timeout=10) as response:
            history = json.loads(response.read().decode())
            outputs = history.get(prompt_id, {}).get('outputs', {})
            
            if '9' in outputs:
                image_info = outputs['9']['images'][0]
                image_url = f"{self.comfyui_url}/view?filename={image_info['filename']}&subfolder={image_info['subfolder']}&type=output"
                
                output_file = self.output_path / f"{output_name}.png"
                urllib.request.urlretrieve(image_url, str(output_file))
                logger.info(f"Image generee: {output_file}")
                return str(output_file)
        
        return None
        
    def generate_video(self, images, audio_path, output_name):
        """Assemble une video avec FFmpeg"""
        import urllib.request
        
        output_file = self.output_path / f"{output_name}.mp4"
        
        # Construction de la commande FFmpeg
        # Slideshow avec crossfade
        ffmpeg_cmd = [
            str(FACTORY_PATH / "ffmpeg" / "bin" / "ffmpeg.exe"),
            "-y"
        ]
        
        # Ajouter les images
        for img in images:
            ffmpeg_cmd.extend(["-loop", "1", "-t", "3", "-i", str(img)])
        
        # Ajouter l'audio
        if audio_path and os.path.exists(audio_path):
            ffmpeg_cmd.extend(["-i", str(audio_path)])
        
        # Filters
        filter_complex = ""
        for i in range(len(images)):
            filter_complex += f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{i}];"
        
        # Concatenation
        for i in range(len(images)):
            filter_complex += f"[v{i}]"
        filter_complex += f"concat=n={len(images)}:v=1:a=0[outv]"
        
        ffmpeg_cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "medium",
            "-crf", "23",
            "-movflags", "+faststart",
            str(output_file)
        ])
        
        try:
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
            logger.info(f"Video generee: {output_file}")
            return str(output_file)
        except subprocess.CalledProcessError as e:
            logger.error(f"Erreur FFmpeg: {e}")
            return None
            
    def run_pipeline(self):
        """Pipeline complet de generation"""
        logger.info("=== Demarrage pipeline ===")
        
        # 1. Verifier ComfyUI
        if not self.start_comfyui():
            logger.error("ComfyUI indisponible. Arret.")
            return False
        
        # 2. Generer image test
        logger.info("Generation image manga...")
        prompt = "masterpiece, best quality, highly detailed, historical manga scene, Edo period Japan, samurai warrior, traditional castle, cherry blossoms, dramatic sunset, ink wash painting style, seinen aesthetic"
        image_path = self.generate_manga_image(prompt, "test_manga")
        
        if image_path:
            logger.info(f"Image generee: {image_path}")
        else:
            logger.error("Echec generation image")
            
        logger.info("=== Pipeline termine ===")
        return True
        
    def run(self):
        """Boucle principale du superviseur"""
        logger.info("=== TikTokHistoryFactory Superviseur ===")
        logger.info("Appuyez sur Ctrl+C pour arreter")
        
        self.init_database()
        
        while self.running:
            try:
                self.run_pipeline()
                logger.info("Attente 1 heure avant prochaine execution...")
                time.sleep(3600)  # Attendre 1 heure
            except KeyboardInterrupt:
                logger.info("Arret demande par l'utilisateur")
                self.running = False
            except Exception as e:
                logger.error(f"Erreur dans la boucle principale: {e}")
                time.sleep(60)  # Attendre 1 minute avant retry
                
        logger.info("Superviseur arrete")

if __name__ == "__main__":
    factory = TikTokHistoryFactory()
    
    # Mode test rapide
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        factory.init_database()
        factory.run_pipeline()
    else:
        factory.run()