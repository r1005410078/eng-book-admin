"""
文件处理工具模块
"""
import os
import shutil
from pathlib import Path
from typing import Optional
import hashlib
from datetime import datetime

from app.core.config import settings


class FileHandler:
    """文件处理工具类"""
    
    def __init__(self):
        """初始化文件处理器"""
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.videos_dir = self.upload_dir / "videos"
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir.mkdir(parents=True, exist_ok=True)
    
    def get_video_directory(self, video_id: int) -> Path:
        """Video directory path"""
        video_dir = self.videos_dir / str(video_id)
        video_dir.mkdir(parents=True, exist_ok=True)
        return video_dir
    
    def save_uploaded_file(
        self,
        file_content: bytes,
        video_id: int,
        filename: str
    ) -> str:
        """
        保存上传的文件 (Bytes)
        """
        video_dir = self.get_video_directory(video_id)
        file_ext = Path(filename).suffix
        save_filename = f"original{file_ext}"
        save_path = video_dir / save_filename
        
        with open(save_path, "wb") as f:
            f.write(file_content)
        
        return str(save_path.relative_to(self.upload_dir))
    
    def save_file_stream(
        self,
        file_obj,
        video_id: int,
        filename: str
    ) -> str:
        """
        Stream save uploaded file (File-like Object)
        Efficient for large files as it avoids loading everything into RAM.
        """
        video_dir = self.get_video_directory(video_id)
        file_ext = Path(filename).suffix
        save_filename = f"original{file_ext}"
        save_path = video_dir / save_filename
        
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file_obj, buffer)
            
        return str(save_path.relative_to(self.upload_dir))
    
    def get_file_path(self, relative_path: str) -> Path:
        return self.upload_dir / relative_path
    
    def get_audio_path(self, video_id: int) -> Path:
        video_dir = self.get_video_directory(video_id)
        return video_dir / "audio.wav"
    
    def get_subtitle_path(self, video_id: int) -> Path:
        video_dir = self.get_video_directory(video_id)
        return video_dir / "subtitles.srt"
    
    def get_thumbnail_path(self, video_id: int) -> Path:
        video_dir = self.get_video_directory(video_id)
        return video_dir / "thumbnail.jpg"
    
    def delete_video_files(self, video_id: int) -> bool:
        try:
            video_dir = self.get_video_directory(video_id)
            if video_dir.exists():
                shutil.rmtree(video_dir)
            return True
        except Exception as e:
            print(f"删除视频文件失败: {e}")
            return False
    
    def get_file_size(self, file_path: Path) -> int:
        if file_path.exists():
            return file_path.stat().st_size
        return 0
    
    def calculate_file_hash(self, file_path: Path) -> Optional[str]:
        if not file_path.exists():
            return None
        
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        
        return md5_hash.hexdigest()
    
    def get_file_extension(self, filename: str) -> str:
        return Path(filename).suffix.lstrip(".")
    
    def is_video_format_supported(self, filename: str) -> bool:
        supported_formats = {"mp4", "avi", "mov", "mkv", "webm"}
        ext = self.get_file_extension(filename).lower()
        return ext in supported_formats
    
    def format_file_size(self, size_bytes: int) -> str:
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"


# 创建全局实例
file_handler = FileHandler()
