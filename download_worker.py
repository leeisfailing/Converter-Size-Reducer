import yt_dlp
from PySide6.QtCore import QThread, Signal
from pathlib import Path
from typing import Optional

class DownloadWorker(QThread):
    progress = Signal(int)
    finished = Signal(bool, str, str)  # ok, error_message, file_path

    def __init__(self, url: str, output_dir: Path, format_type: str = "bestvideo+bestaudio/best", parent=None):
        super().__init__(parent)
        self.url = url
        self.output_dir = output_dir
        self.format_type = format_type

    def run(self):
        def progress_hook(d):
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate')
                if total:
                    downloaded = d.get('downloaded_bytes', 0)
                    pct = int(downloaded / total * 100)
                    self.progress.emit(pct)

        ydl_opts = {
            'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
            'format': 'bestvideo+bestaudio/best',
            'progress_hooks': [progress_hook],
            'nocheckcertificate': True,
            'quiet': True,
            'no_warnings': True,
        }

        if self.format_type == "mp4":
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            ydl_opts['merge_output_format'] = 'mp4'
        elif self.format_type == "mp3":
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        elif self.format_type != "bestvideo+bestaudio/best":
            ydl_opts['format'] = self.format_type

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=True)
                # prepare_filename gives us the output path as predicted by outtmpl
                # but if merged (e.g. mp4 + m4a -> mkv/mp4), the final path could differ slightly in extension,
                # though yt-dlp tries to be accurate. 
                # A safe bet is info['requested_downloads'][0]['filepath'] if present,
                # else prepare_filename.
                if 'requested_downloads' in info and len(info['requested_downloads']) > 0: # Check if merged
                     final_path = info['requested_downloads'][0].get('filepath', ydl.prepare_filename(info))
                else:
                     final_path = ydl.prepare_filename(info)
                     
                self.progress.emit(100)
                self.finished.emit(True, "", final_path)
        except Exception as e:
            # Fallback to general HTTP download for plain files (PDFs, images, etc.)
            try:
                import urllib.request
                import urllib.parse
                import os
                
                parsed = urllib.parse.urlparse(self.url)
                filename = os.path.basename(parsed.path)
                if not filename:
                    filename = "downloaded_file"
                
                final_path = self.output_dir / filename
                
                def reporthook(blocknum, blocksize, totalsize):
                    if totalsize > 0:
                        read_so_far = blocknum * blocksize
                        if read_so_far > totalsize:
                            read_so_far = totalsize
                        pct = int((read_so_far / totalsize) * 100)
                        self.progress.emit(pct)
                
                # Setup a basic user agent so some sites don't block us immediately
                req = urllib.request.Request(
                    self.url, 
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                with urllib.request.urlopen(req) as response:
                    with open(final_path, 'wb') as out_file:
                        info = response.info()
                        totalsize = int(info.get("Content-Length", -1))
                        
                        blocksize = 8192
                        blocknum = 0
                        while True:
                            buffer = response.read(blocksize)
                            if not buffer:
                                break
                            blocknum += 1
                            out_file.write(buffer)
                            reporthook(blocknum, blocksize, totalsize)

                self.progress.emit(100)
                self.finished.emit(True, "", str(final_path))
            except Exception as fallback_e:
                self.finished.emit(False, f"yt-dlp error: {e}\nFallback HTTP error: {fallback_e}", "")
