"""
TikTokHistoryFactory - Documentary Assembler Module
Reusable module for building 1080x1920 TikTok documentaries from images + audio.
Usage: from tiktok_assembler import DocumentaryAssembler
"""
import os, subprocess, json, wave, math
from PIL import Image, ImageDraw, ImageFont

class DocumentaryAssembler:
    def __init__(self, ffmpeg_path, width=1080, height=1920, fps=30, preset="ultrafast"):
        self.ffmpeg = ffmpeg_path
        self.width = width
        self.height = height
        self.fps = fps
        self.preset = preset
        self.font_candidates = [
            r"C:\Windows\Fonts\impact.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\segoeuib.ttf",
        ]
    
    def _get_font(self, size):
        for f in self.font_candidates:
            if os.path.exists(f):
                try:
                    return ImageFont.truetype(f, size)
                except:
                    pass
        return ImageFont.load_default()
    
    def wrap_text_to_two_lines(self, text, draw, font, max_width):
        words = text.split()
        if not words:
            return []
        bbox = draw.textbbox((0,0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return [text]
        best = None
        best_diff = float('inf')
        for i in range(1, len(words)):
            l1 = " ".join(words[:i])
            l2 = " ".join(words[i:])
            b1 = draw.textbbox((0,0), l1, font=font)
            b2 = draw.textbbox((0,0), l2, font=font)
            w1 = b1[2]-b1[0]; w2 = b2[2]-b2[0]
            if max(w1, w2) <= max_width:
                diff = abs(w1 - w2)
                if diff < best_diff:
                    best_diff = diff
                    best = (l1, l2)
        if best:
            return list(best)
        mid = len(words) // 2
        return [" ".join(words[:mid]), " ".join(words[mid:])]
    
    def draw_outlined_text(self, draw, pos, text, font, fill, outline_color, outline_width=4):
        x, y = pos
        for dx in range(-outline_width, outline_width+1):
            for dy in range(-outline_width, outline_width+1):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x+dx, y+dy), text, font=font, fill=outline_color)
        draw.text((x, y), text, font=font, fill=fill)
    
    def burn_subtitle(self, image_path, subtitle, font_size=72, outline_width=5, 
                      fill=(255,255,255), outline=(0,0,0), bottom_margin=220):
        """Burn subtitle into image. Returns new image path."""
        img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        font = self._get_font(font_size)
        lines = self.wrap_text_to_two_lines(subtitle, draw, font, self.width - 120)
        line_height = int(font_size * 1.25)
        total_h = len(lines) * line_height
        base_y = self.height - bottom_margin - total_h
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0,0), line, font=font)
            tw = bbox[2] - bbox[0]
            x = (self.width - tw) // 2
            y = base_y + i * line_height
            self.draw_outlined_text(draw, (x, y), line, font, fill, outline, outline_width)
        return img
    
    def build_clip(self, image_path, duration, output_path, motion=(1.0, 1.0, 0, 0, 0, 0), fade_out=0.5):
        """Build a single clip from image with motion and fade."""
        zs, ze, xs, xe, ys, ye = motion
        total_frames = int(round(duration * self.fps))
        zoom_expr = f"{zs}+({ze}-{zs})*in/{total_frames}"
        x_expr = f"(iw-iw/zoom)/2+iw*({xs}+({xe}-{xs})*in/{total_frames})/2"
        y_expr = f"(ih-ih/zoom)/2+ih*({ys}+({ye}-{ys})*in/{total_frames})/2"
        vf = f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':d={total_frames}:s={self.width}x{self.height},fade=t=out:st={duration-fade_out}:d={fade_out}"
        cmd = [
            self.ffmpeg, "-y", "-loop", "1", "-i", image_path,
            "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-r", str(self.fps), "-t", str(duration), "-an", "-preset", self.preset, output_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0, res.stderr
    
    def build_clip_static(self, image_path, duration, output_path, fade_out=0.5):
        """Fallback: static image with fade."""
        cmd = [
            self.ffmpeg, "-y", "-loop", "1", "-i", image_path,
            "-vf", f"fade=t=out:st={duration-fade_out}:d={fade_out}",
            "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
            "-r", str(self.fps), "-t", str(duration), "-an", "-preset", self.preset, output_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0, res.stderr
    
    def concatenate(self, clip_paths, output_path):
        """Concatenate clips into single video."""
        concat_file = output_path.replace(".mp4", "_concat.txt")
        with open(concat_file, "w") as f:
            for c in clip_paths:
                f.write(f"file '{c}'\n")
        cmd = [self.ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", concat_file, "-c", "copy", output_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0, res.stderr
    
    def mix_audio(self, video_path, audio_path, output_path, duration=None):
        """Mix audio into video."""
        cmd = [self.ffmpeg, "-y", "-i", video_path, "-i", audio_path,
               "-c:v", "copy", "-c:a", "aac", "-b:a", "192k"]
        if duration:
            cmd += ["-t", str(duration)]
        cmd.append(output_path)
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0, res.stderr
    
    def extend_audio(self, audio_path, target_duration, output_path):
        """Pad audio with silence to target duration."""
        cmd = [self.ffmpeg, "-y", "-i", audio_path, "-af", f"apad=pad_dur={target_duration}", "-t", str(target_duration), output_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0, res.stderr
    
    def concat_wav_files(self, wav_paths, output_path):
        """Concatenate WAV files."""
        if not wav_paths:
            return False
        with wave.open(wav_paths[0], 'rb') as w:
            nc = w.getnchannels(); sw = w.getsampwidth(); fr = w.getframerate()
        with wave.open(output_path, 'wb') as out:
            out.setnchannels(nc); out.setsampwidth(sw); out.setframerate(fr)
            for p in wav_paths:
                with wave.open(p, 'rb') as w:
                    out.writeframes(w.readframes(w.getnframes()))
        return True
    
    def verify(self, video_path):
        """Return dict with video metadata."""
        ffprobe = self.ffmpeg.replace("ffmpeg.exe", "ffprobe.exe")
        result = {"video": {}, "audio": {}, "format": {}}
        for stream, sel in [("video", "v:0"), ("audio", "a:0")]:
            res = subprocess.run([ffprobe, "-v", "error", "-select_streams", sel,
                                   "-show_entries", "stream=codec_name,width,height,duration,avg_frame_rate",
                                   "-of", "json", video_path], capture_output=True, text=True)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                result[stream] = data.get("streams", [{}])[0]
        res = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration,size,bit_rate",
                              "-of", "json", video_path], capture_output=True, text=True)
        if res.returncode == 0:
            result["format"] = json.loads(res.stdout).get("format", {})
        return result
