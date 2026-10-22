"""Consistent media-provider contracts; every success requires a real output."""
from pathlib import Path


class VideoCompositor:
    def __init__(self, ffmpeg_provider):
        self.ffmpeg = ffmpeg_provider

    def compose(self, image_paths, audio_path, subtitles_srt, output_path, duration=30):
        result = self.ffmpeg.assemble_slideshow(image_paths, audio_path, output_path)
        if not result.get('success'):
            return {'status': 'FAILED', **result}
        if subtitles_srt:
            final = str(Path(output_path).with_suffix('.subtitled.mp4'))
            result = self.ffmpeg.burn_subtitles(output_path, subtitles_srt, final)
            if not result.get('success'):
                return {'status': 'FAILED', **result}
            output_path = final
        if not Path(output_path).is_file():
            return {'status': 'FAILED', 'error': 'No output file'}
        return {'status': 'SUCCESS', 'output_path': output_path}

    def compose_pilot(self, image_paths, audio_paths, subtitles_srt, output_path, work_dir):
        result = self.ffmpeg.render_pilot(image_paths, audio_paths, subtitles_srt, output_path, work_dir)
        return {**result, 'status': 'SUCCESS' if result.get('success') else 'FAILED'}
