# Converter by Lee (Video, Photo & URL Downloader)

A modern, GPU-accelerated desktop application for converting media, reducing file sizes, and downloading content from the web. Built with Python and PySide6, powered by `ffmpeg` and `yt-dlp`.

## Features

- **Media Conversion**: Convert between various video and image formats (MP4, MKV, JPG, PNG, etc.).
- **Size Reduction**: Intelligently compress videos to a target megabyte (MB) size or reduce image quality.
- **URL Downloader**: 
  - Download videos or extract audio (MP3) from YouTube and hundreds of other sites.
  - Supports direct HTTP downloads for generic files.
  - Integrated progress tracking.
- **GPU Acceleration**:
  - Auto-detects available hardware encoders (NVIDIA NVENC, Intel QSV, AMD AMF, VAAPI).
  - Manual selection or "Auto" mode to pick the best available codec.
- **Resolution Scaling**: Quickly scale videos to 1080p, 4K, or keep the original resolution.
- **Modern UI**:
  - Drag & drop support for easy file selection.
  - "Click to browse" functionality.
  - Real-time progress bars for both downloads and encoding.

## Requirements

- **Python 3.10+**
- **ffmpeg & ffprobe**: Must be installed and available on your system `PATH`.
  - [Download ffmpeg](https://ffmpeg.org/download.html)
  - Verify by running `ffmpeg -version` in your terminal.
- **Python Dependencies**:
  ```bash
  pip install -r requirements.txt
  ```
  *(Includes PySide6 and yt-dlp)*

## Running the App

1. Clone or download the repository.
2. Install the requirements.
3. Run the main script:
   ```bash
   python main.py
   ```

## Usage

### Converting or Reducing Files
1. Select **Convert format** or **Size reduce**.
2. **Drag and drop** a file onto the dashed area, or **click** it to browse your computer.
3. (Optional) Set a custom **Output format** (e.g., `webp`).
4. (Optional) For videos, set a **Target size (MB)** or choose a **Resolution**.
5. Select your preferred **GPU Encoder** (or leave as Auto).
6. Click **Start**. The new file will be saved in the same folder as the original.

### Downloading from URL
1. Select **Download URL**.
2. Paste the link into the URL field.
3. If it's a YouTube link, choose your preferred format (Default, MP4, or MP3).
4. Click **Download**.
5. Choose where to save the file once the download completes.

## GPU Support Details

The app scans `ffmpeg -encoders` to find hardware-accelerated codecs:
- **NVIDIA**: `h264_nvenc`, `hevc_nvenc`
- **Intel**: `h264_qsv`, `hevc_qsv`
- **AMD**: `h264_amf`, `hevc_amf`
- **Linux/Generic**: `vaapi`

If no GPU is found, it gracefully falls back to standard CPU encoding (`libx264`).

