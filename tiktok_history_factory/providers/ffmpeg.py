"""Wrapper FFmpeg pour montage video et animations de secours."""
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, List


class FFmpegProvider:
    """Montage video CPU/GPU via FFmpeg."""

    def __init__(self, ffmpeg_path: str = r"C:\TikTokHistoryFactory\ffmpeg\bin\ffmpeg.exe",
                 ffprobe_path: str = r"C:\TikTokHistoryFactory\ffmpeg\bin\ffprobe.exe"):
        self.ffmpeg = ffmpeg_path
        self.ffprobe = ffprobe_path

    def _run(self, args: List[str], timeout: int = 300) -> Dict[str, Any]:
        """Execute une commande FFmpeg et retourne le resultat."""
        cmd = [self.ffmpeg] + args
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0,
            }
        except subprocess.TimeoutExpired:
            return {"returncode": -1, "error": f"Timeout apres {timeout}s", "success": False}
        except Exception as e:
            return {"returncode": -1, "error": str(e), "success": False}

    def create_test_image(self, output_path: str, width: int = 1080, height: int = 1920,
                          color: str = "#8B4513") -> Dict[str, Any]:
        """Genere une image de couleur unie via FFmpeg."""
        args = [
            "-f", "lavfi",
            "-i", f"color=c={color}:s={width}x{height}",
            "-frames:v", "1",
            "-y", output_path,
        ]
        return self._run(args, timeout=30)

    def create_test_audio(self, output_path: str, duration: int = 3) -> Dict[str, Any]:
        """Genere un audio test (beep) via FFmpeg."""
        args = [
            "-f", "lavfi",
            "-i", f"sine=frequency=1000:duration={duration}",
            "-ar", "44100",
            "-ac", "2",
            "-y", output_path,
        ]
        return self._run(args, timeout=30)

    def assemble_slideshow(self, image_paths: List[str], audio_path: str, output_path: str,
                           duration_per_image: float = 1.5, transition_duration: float = 0.5) -> Dict[str, Any]:
        """Assemble un slideshow d'images + audio en MP4 vertical 9:16."""
        if not image_paths:
            return {"success": False, "error": "Aucune image fournie"}
        if len(image_paths) == 1:
            args = [
                "-loop", "1", "-i", image_paths[0],
                "-i", audio_path,
                "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,format=yuv420p",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
                "-shortest", "-y", output_path,
            ]
            return self._run(args)
        if len(image_paths) == 2:
            offset = duration_per_image - transition_duration
            args = [
                "-loop", "1", "-t", str(duration_per_image), "-i", image_paths[0],
                "-loop", "1", "-t", str(duration_per_image), "-i", image_paths[1],
                "-i", audio_path,
                "-filter_complex",
                f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,format=yuv420p[v0];[1:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,format=yuv420p[v1];[v0][v1]xfade=transition=fade:duration={transition_duration}:offset={offset}[video]",
                "-map", "[video]", "-map", "2:a",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
                "-shortest", "-y", output_path,
            ]
            return self._run(args)
        return {"success": False, "error": f"{len(image_paths)} images non supportees (max 2)"}

    def probe_file(self, file_path: str) -> Dict[str, Any]:
        """Analyse un fichier avec ffprobe."""
        try:
            result = subprocess.run(
                [self.ffprobe, "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", file_path],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
            return {"error": result.stderr}
        except Exception as e:
            return {"error": str(e)}

    def burn_subtitles(self, video_path: str, srt_path: str, output_path: str) -> Dict[str, Any]:
        """Superpose des sous-titres SRT sur la video (hardcoded pour TikTok)."""
        args = [
            "-i", video_path,
            "-vf", "subtitles='" + str(Path(srt_path).resolve()).replace('\\', '/').replace(':', r'\:').replace("'", r"\'") + "':force_style='FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2'",
            "-c:a", "copy",
            "-y", output_path,
        ]
        return self._run(args)

    def render_pilot(self, images, audio_paths, subtitles, output_path, work_dir):
        """Render 3..6 real illustrations with camera movement, fades and French audio."""
        import math
        import wave
        from tiktok_history_factory.providers.piper_tts import inspect_wav
        work = Path(work_dir).resolve()
        work.mkdir(parents=True, exist_ok=True)
        if not 3 <= len(images) <= 6 or len(images) != len(audio_paths):
            return {'success': False, 'error': 'Pilot requires 3..6 paired images and voice files'}
        logs, clips, durations = [], [], []
        try:
            combined = work / 'narration.wav'
            with wave.open(str(combined), 'wb') as out:
                out.setnchannels(1)
                out.setsampwidth(2)
                out.setframerate(22050)
                for audio in audio_paths:
                    info = inspect_wav(audio)
                    if info['sample_rate'] != 22050 or info['channels'] != 1:
                        raise ValueError('All Piper segments must be mono 22050 Hz')
                    duration = math.ceil(info['duration'] * 30) / 30
                    durations.append(duration)
                    with wave.open(str(audio), 'rb') as source:
                        pcm = source.readframes(source.getnframes())
                    wanted = round(duration * 22050)
                    out.writeframes(pcm + b'\x00\x00' * max(0, wanted - len(pcm) // 2))
            for index, (image, duration) in enumerate(zip(images, durations)):
                clip = work / f'clip-{index + 1:02d}.mp4'
                frames = round(duration * 30)
                # Slow centered zoom with small horizontal drift; never invent motion between frames.
                vf = ("scale=1200:2134:force_original_aspect_ratio=increase,crop=1200:2134,"
                      f"zoompan=z='1+0.045*on/{frames}':x='iw/2-iw/zoom/2+8*sin(on/{frames}*PI)':"
                      f"y='ih/2-ih/zoom/2':d={frames}:s=1080x1920:fps=30,setsar=1,"
                      "format=yuv420p")
                if Path(image).suffix.lower() == '.mp4':
                    vf = (f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,"
                          f"tpad=stop_mode=clone:stop_duration={duration},format=yuv420p")
                result = self._run(['-i', str(image), '-vf', vf, '-frames:v', str(frames),
                                    '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '20', '-y', str(clip)])
                logs.append(result)
                if not result['success']:
                    raise RuntimeError(result.get('error', result.get('stderr', ''))[-2000:])
                clips.append(clip)
            listing = work / 'clips.txt'
            listing.write_text(''.join(f"file '{clip.name}'\n" for clip in clips), encoding='utf-8')
            subtitle_copy = work / 'captions.srt'
            import shutil
            shutil.copyfile(subtitles, subtitle_copy)
            # Explicit ASS script resolution avoids libass' implicit 384x288 SRT
            # canvas, which makes vertical captions far too large.
            header = ('[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\n'
                      '\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n'
                      'Style: Default,Arial,54,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,70,70,260,1\n'
                      '\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n')
            events = []
            for block in subtitle_copy.read_text(encoding='utf-8').strip().split('\n\n'):
                lines = block.splitlines()
                if len(lines) < 3:
                    raise ValueError('Invalid subtitle block')
                times = lines[1].split(' --> ')
                def ass_time(value):
                    return value.replace(',', '.')[:-1].lstrip('0') if not value.startswith('00:') else value[1:].replace(',', '.')[:-1]
                text = r'\N'.join(lines[2:]).replace('{','(').replace('}',')')
                events.append(f'Dialogue: 0,{ass_time(times[0])},{ass_time(times[1])},Default,,0,0,0,,{text}\n')
            (work/'captions.ass').write_text(header + ''.join(events), encoding='utf-8')
            vf = 'ass=captions.ass'
            cmd = [self.ffmpeg, '-f', 'concat', '-safe', '1', '-i', listing.name, '-i', combined.name,
                   '-vf', vf, '-map', '0:v:0', '-map', '1:a:0', '-t', str(sum(durations)),
                   '-c:v', 'libx264', '-preset', 'fast', '-crf', '20', '-pix_fmt', 'yuv420p',
                   '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-movflags', '+faststart',
                   '-metadata', 'comment=Reconstitution historique generee par IA; images non documentaires; narration EN; sous-titres FR',
                   '-y', str(Path(output_path).resolve())]
            rendered = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=300)
            logs.append({'returncode': rendered.returncode, 'stderr': rendered.stderr, 'command': cmd})
            (work / 'ffmpeg-log.json').write_text(json.dumps(logs, indent=2), encoding='utf-8')
            if rendered.returncode:
                raise RuntimeError(rendered.stderr[-2000:])
            return {'success': True, 'status': 'SUCCESS', 'output_path': str(output_path),
                    'durations': durations, 'duration': sum(durations), 'audio_path': str(combined),
                    'subtitles_ass': str(work/'captions.ass'),
                    'animation': 'FFmpeg slow zoom, pan, fades; Wan not used'}
        except Exception as exc:
            return {'success': False, 'status': 'FAILED', 'error': str(exc)}
