# Video & Photo Converter (GPU-Accelerated)

Python desktop app for converting and size-reducing videos and images, with optional GPU-accelerated encoding via `ffmpeg`.  
Tested on Windows 10+.

## Features

- Simple GUI built with **PySide6**
- Drag & drop one file at a time onto the window
- Choose **Video** or **Image**
- Choose **Convert** (format change) or **Size reduce** (lower bitrate/quality)
- Auto-detect available GPU encoders from `ffmpeg` and let the user choose
- Saves output next to the original file

## Requirements

- **Python 3.10+**
- **ffmpeg** installed and available on `PATH`
  - Download from the official site or a Windows build provider
  - Make sure `ffmpeg.exe` is accessible from a normal terminal (`ffmpeg -version`)
- Python packages (install via `requirements.txt`):

```bash
pip install -r requirements.txt
```

## Running the app

From the project folder:

```bash
python main.py
```

## Usage

1. Start the app.
2. Choose **Video** or **Image**.
3. Choose **Convert** or **Size reduce**.
4. Drag & drop a single file onto the window.
5. Choose which GPU encoder to use (if any are detected), or fall back to CPU.
6. Wait for encoding to finish; the new file will be saved into the **same folder** as the original.

## Notes on GPU support

- The app does **not** implement low-level CUDA/OpenCL itself; it relies on `ffmpeg` hardware encoders:
  - NVIDIA: `h264_nvenc`, `hevc_nvenc`, etc.
  - Intel: `h264_qsv`, `hevc_qsv`, etc.
  - AMD: `h264_amf`, `hevc_amf`, etc.
- The app scans `ffmpeg -encoders` output to build a list of available GPU encoders.
- If no GPU encoders are found or the chosen encoder fails, the app can fall back to CPU encoding.

