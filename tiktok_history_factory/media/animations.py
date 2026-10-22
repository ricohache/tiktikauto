
"""Animations et effets de transition FFmpeg (fallback Wan)."""
from typing import Dict, Any, List


class AnimationFallback:
    """Animations par FFmpeg quand Wan n'est pas disponible."""

    def __init__(self, ffmpeg_provider):
        self.ffmpeg = ffmpeg_provider

    def create_ken_burns(self, image_path: str, output_path: str, duration: int = 5) -> Dict[str, Any]:
        """Effet Ken Burns (pan/zoom) sur une image statique."""
        from pathlib import Path
        if not Path(image_path).is_file() or duration <= 0:
            return {'status': 'BLOCKED', 'error': 'Image missing or duration invalid'}
        frames = round(duration * 30)
        result = self.ffmpeg._run(['-i', image_path, '-vf',
            f"scale=1200:2134:force_original_aspect_ratio=increase,crop=1200:2134,zoompan=z='1+0.04*on/{frames}':d={frames}:s=1080x1920:fps=30,format=yuv420p",
            '-frames:v', str(frames), '-an', '-c:v','libx264','-preset','fast','-y',output_path])
        return {**result, 'status': 'SUCCESS' if result['success'] and Path(output_path).is_file() else 'FAILED'}

    def create_crossfade_slideshow(self, image_paths: List[str], output_path: str, duration: int = 30) -> Dict[str, Any]:
        """Diaporama avec crossfade entre les images."""
        if not 2 <= len(image_paths) <= 6 or duration <= 1:
            return {'status':'BLOCKED','error':'Need 2..6 images and positive duration'}
        transition = .35
        per_image = (duration + transition*(len(image_paths)-1))/len(image_paths)
        args, filters = [], []
        for index,path in enumerate(image_paths):
            args += ['-loop','1','-t',str(per_image),'-i',path]
            filters.append(f'[{index}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,format=yuv420p[v{index}]')
        previous='v0'
        for index in range(1,len(image_paths)):
            output=f'x{index}'
            filters.append(f'[{previous}][v{index}]xfade=transition=fade:duration={transition}:offset={index*(per_image-transition)}[{output}]')
            previous=output
        args += ['-filter_complex',';'.join(filters),'-map',f'[{previous}]','-t',str(duration),'-an',
                 '-c:v','libx264','-preset','fast','-pix_fmt','yuv420p','-y',output_path]
        result=self.ffmpeg._run(args)
        return {**result,'status':'SUCCESS' if result['success'] else 'FAILED'}

