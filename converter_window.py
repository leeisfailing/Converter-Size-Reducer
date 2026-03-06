from __future__ import annotations

from pathlib import Path
from typing import List, Set

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
    QProgressBar,
    QFileDialog,
)

from encoder_worker import EncoderWorker
from download_worker import DownloadWorker
from ffmpeg_utils import build_ffmpeg_command, detect_gpu_encoders


class DropArea(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("\n\nDrop a file here or click to browse\n")
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            "QLabel { border: 2px dashed #888; border-radius: 8px; color: #555; }"
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.parent().browse_file()  # type: ignore[attr-defined]

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if not urls:
            return
        local_path = urls[0].toLocalFile()
        if local_path:
            self.parent().on_file_dropped(local_path)  # type: ignore[call-arg]


class ConverterWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Converter by Lee")
        self.setFixedSize(520, 440)

        self.current_file: Path | None = None
        self.worker: EncoderWorker | None = None
        self.download_worker: DownloadWorker | None = None
        self.available_gpu_encoders: Set[str] = set()

        self._build_ui()
        self._populate_gpu_encoders()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        mode_box = QGroupBox("What do you want to do?")
        mode_layout = QGridLayout()
        self.convert_radio = QRadioButton("Convert format")
        self.reduce_radio = QRadioButton("Size reduce")
        self.download_radio = QRadioButton("Download URL")
        self.reduce_radio.setChecked(True)
        mode_layout.addWidget(self.convert_radio, 0, 0)
        mode_layout.addWidget(self.reduce_radio, 0, 1)
        mode_layout.addWidget(self.download_radio, 1, 0, 1, 2)
        mode_box.setLayout(mode_layout)

        self.gpu_box = QGroupBox("GPU / Encoder (video only)")
        gpu_layout = QVBoxLayout()
        self.gpu_combo = QComboBox()
        self.gpu_combo.setEditable(False)
        self.gpu_combo.addItem("Auto (CPU or best available)", "auto")
        gpu_layout.addWidget(self.gpu_combo)
        self.gpu_box.setLayout(gpu_layout)

        self.url_box = QGroupBox("Download Media from URL")
        url_layout = QGridLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Paste video/audio URL here...")
        self.download_button = QPushButton("Download")
        self.download_button.clicked.connect(self.start_downloading)
        url_layout.addWidget(self.url_edit, 0, 0)
        url_layout.addWidget(self.download_button, 0, 1)

        self.url_format_combo = QComboBox()
        self.url_format_combo.addItem("Best available (Default)", "default")
        self.url_format_combo.addItem("Video (MP4)", "mp4")
        self.url_format_combo.addItem("Audio only (MP3)", "mp3")
        self.url_format_combo.setVisible(False)
        url_layout.addWidget(self.url_format_combo, 1, 0, 1, 2)

        self.url_edit.textChanged.connect(self._check_url_type)

        self.url_box.setLayout(url_layout)

        self.drop_area = DropArea(self)

        self.file_info_widget = QWidget()
        file_info_layout = QGridLayout(self.file_info_widget)
        file_info_layout.setContentsMargins(0, 0, 0, 0)
        file_info_layout.addWidget(QLabel("Selected file:"), 0, 0)
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        file_info_layout.addWidget(self.file_path_edit, 0, 1)

        self.format_label = QLabel("Output format (optional):")
        file_info_layout.addWidget(self.format_label, 1, 0)
        self.format_edit = QLineEdit()
        self.format_edit.setPlaceholderText("e.g. mp4, mkv, jpg, png (optional)")
        file_info_layout.addWidget(self.format_edit, 1, 1)

        self.target_size_label = QLabel("Target size MB (size reduce, optional):")
        file_info_layout.addWidget(self.target_size_label, 2, 0)
        self.target_size_edit = QLineEdit()
        self.target_size_edit.setPlaceholderText("e.g. 50  (approx. output size in MB)")
        file_info_layout.addWidget(self.target_size_edit, 2, 1)

        self.resolution_label = QLabel("Resolution (video):")
        file_info_layout.addWidget(self.resolution_label, 3, 0)
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItem("Original", None)
        self.resolution_combo.addItem("1080p (1920x1080)", "1920:1080")
        self.resolution_combo.addItem("4K (3840x2160)", "3840:2160")
        file_info_layout.addWidget(self.resolution_combo, 3, 1)

        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_encoding)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        main_layout.addWidget(mode_box)
        main_layout.addWidget(self.url_box)
        main_layout.addWidget(self.gpu_box)
        main_layout.addWidget(self.drop_area)
        main_layout.addWidget(self.file_info_widget)
        main_layout.addWidget(self.start_button)
        main_layout.addWidget(self.progress_bar)

        self.convert_radio.toggled.connect(self._update_mode_visibility)
        self.reduce_radio.toggled.connect(self._update_mode_visibility)
        self.download_radio.toggled.connect(self._update_mode_visibility)

        self._update_mode_visibility()

    def _set_ui_enabled(self, enabled: bool):
        self.convert_radio.setEnabled(enabled)
        self.reduce_radio.setEnabled(enabled)
        self.download_radio.setEnabled(enabled)
        self.gpu_combo.setEnabled(enabled)
        self.drop_area.setEnabled(enabled)
        self.drop_area.setAcceptDrops(enabled)
        self.format_edit.setEnabled(enabled)
        self.target_size_edit.setEnabled(enabled)
        self.resolution_combo.setEnabled(enabled)
        self.start_button.setEnabled(enabled)
        self.url_edit.setEnabled(enabled)
        self.download_button.setEnabled(enabled)
        self.url_format_combo.setEnabled(enabled)

    def _populate_gpu_encoders(self):
        encoders = detect_gpu_encoders()

        for name, desc in encoders:
            label = f"{name} - {desc}"
            self.gpu_combo.addItem(label, name)
            self.available_gpu_encoders.add(name)

        if not encoders:
            self.gpu_combo.addItem("No GPU encoders found (CPU only)", "cpu_only")

    def on_file_dropped(self, path_str: str):
        p = Path(path_str)
        if not p.exists() or not p.is_file():
            QMessageBox.warning(self, "Invalid file", "The dropped item is not a valid file.")
            return
        self.current_file = p
        self.file_path_edit.setText(str(p))
        self._update_mode_visibility()
    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select a file",
            "",
            "All Files (*.*)"
        )
        if file_path:
            self.on_file_dropped(file_path)

    def _check_url_type(self, text: str):
        is_youtube = "youtube.com" in text.lower() or "youtu.be" in text.lower()
        self.url_format_combo.setVisible(is_youtube)

    def start_downloading(self):
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.information(self, "No URL", "Please enter a valid URL.")
            return

        self._set_ui_enabled(False)
        self.progress_bar.setValue(0)
        
        import tempfile
        temp_dir = Path(tempfile.gettempdir())
        
        format_type = "bestvideo+bestaudio/best"
        if "youtube.com" in url.lower() or "youtu.be" in url.lower():
            combo_data = self.url_format_combo.currentData()
            if combo_data in ("mp4", "mp3"):
                format_type = combo_data
                
        self.download_worker = DownloadWorker(url, output_dir=temp_dir, format_type=format_type)
        self.download_worker.progress.connect(self.progress_bar.setValue)
        self.download_worker.finished.connect(self._on_download_finished)
        self.download_worker.start()

    def _on_download_finished(self, ok: bool, message: str, file_path: str):
        self._set_ui_enabled(True)
        if ok and file_path:
            import os
            import shutil
            
            default_name = os.path.basename(file_path)
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Downloaded File As...",
                default_name,
                "All Files (*.*)"
            )
            
            if save_path:
                try:
                    # Move the file from the temporary directory to the user's chosen location
                    shutil.move(file_path, save_path)
                    QMessageBox.information(self, "Download Complete", f"Saved to: {save_path}")
                    self.on_file_dropped(save_path)
                    self.url_edit.clear()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to save file:\n{e}")
            else:
                # The user cancelled the save dialog, delete the temporary file
                try:
                    os.remove(file_path)
                except OSError:
                    pass
        else:
            QMessageBox.critical(self, "Download Error", f"Failed to download:\n{message}")

    def start_encoding(self):
        if not self.current_file:
            QMessageBox.information(self, "No file", "Please drag and drop a file first.")
            return

        is_video = self._is_current_file_video()
        is_convert = self.convert_radio.isChecked()

        output_ext = self._determine_output_extension(is_video, is_convert)
        input_path = self.current_file
        output_path = self._build_output_path(input_path, output_ext)

        gpu_choice = self.gpu_combo.currentData()
        if not isinstance(gpu_choice, str):
            gpu_choice = "auto"

        target_size_mb = None
        if is_video and not is_convert:
            raw = self.target_size_edit.text().strip()
            if raw:
                try:
                    value = float(raw)
                    if value <= 0:
                        raise ValueError
                    target_size_mb = value
                except ValueError:
                    QMessageBox.warning(
                        self,
                        "Invalid size",
                        "Please enter a positive number for target size in MB, "
                        "or leave it empty.",
                    )
                    return

        target_resolution = None
        if is_video:
            target_resolution = self.resolution_combo.currentData()
            if not isinstance(target_resolution, str):
                target_resolution = None

        cmd = build_ffmpeg_command(
            input_path=input_path,
            output_path=output_path,
            is_video=is_video,
            is_convert=is_convert,
            gpu_choice=gpu_choice,
            available_gpu_encoders=self.available_gpu_encoders,
            target_size_mb=target_size_mb,
            target_resolution=target_resolution,
        )

        self._set_ui_enabled(False)
        self.progress_bar.setValue(0)

        self.worker = EncoderWorker(cmd, cwd=str(input_path.parent))
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self._on_encoding_finished)
        self.worker.start()

    def _determine_output_extension(self, is_video: bool, is_convert: bool) -> str:
        custom = self.format_edit.text().strip().lstrip(".")
        if custom:
            return "." + custom

        if is_video:
            return ".mp4"
        if is_convert:
            return ".jpg"
        return self.current_file.suffix or ".jpg"  # type: ignore[union-attr]

    def _build_output_path(self, input_path: Path, ext: str) -> Path:
        parent = input_path.parent
        stem = input_path.stem
        suffix = ext if ext.startswith(".") else "." + ext

        candidate = parent / f"{stem}_converted{suffix}"
        idx = 1
        while candidate.exists():
            candidate = parent / f"{stem}_converted_{idx}{suffix}"
            idx += 1
        return candidate

    def _update_mode_visibility(self):
        is_convert = self.convert_radio.isChecked()
        is_video = self._is_current_file_video()
        is_download = self.download_radio.isChecked()

        self.url_box.setVisible(is_download)
        self.gpu_box.setVisible(is_video and not is_download)
        self.drop_area.setVisible(not is_download)
        self.file_info_widget.setVisible(not is_download)
        self.start_button.setVisible(not is_download)

        if not is_download:
            show_format = is_convert
            self.format_label.setVisible(show_format)
            self.format_edit.setVisible(show_format)

            show_target_size = (not is_convert) and is_video
            self.target_size_label.setVisible(show_target_size)
            self.target_size_edit.setVisible(show_target_size)

            self.resolution_label.setVisible(is_video)
            self.resolution_combo.setVisible(is_video)

    def _is_current_file_video(self) -> bool:
        if not self.current_file:
            return False
        video_exts = {
            ".mp4",
            ".mkv",
            ".mov",
            ".avi",
            ".wmv",
            ".flv",
            ".webm",
        }
        return self.current_file.suffix.lower() in video_exts

    def _on_encoding_finished(self, ok: bool, message: str):
        self._set_ui_enabled(True)
        if ok:
            QMessageBox.information(self, "Done", "Encoding finished successfully.")
        else:
            QMessageBox.critical(self, "Error", f"Encoding failed:\n{message}")

