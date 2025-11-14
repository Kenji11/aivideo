import subprocess

class FFmpegService:
    def run_command(self, command: list) -> str:
        """Run FFmpeg command"""
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout

ffmpeg_service = FFmpegService()
