"""
FFmpeg 服务模块
提供视频元数据提取和音频提取功能
"""
import os
import ffmpeg
from pathlib import Path
from typing import Dict, Any, Optional

from app.utils.file_handler import file_handler


class FFmpegService:
    """FFmpeg 服务类"""

    def get_video_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        获取视频元数据
        
        Args:
            file_path: 视频文件路径
            
        Returns:
            Dict: 包含时长、分辨率、格式等信息
        """
        try:
            probe = ffmpeg.probe(str(file_path))
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            
            if not video_stream:
                raise Exception("未找到视频流")

            duration = float(probe['format'].get('duration', 0))
            width = int(video_stream.get('width', 0))
            height = int(video_stream.get('height', 0))
            codec_name = video_stream.get('codec_name', 'unknown')
            
            return {
                "duration": duration,
                "resolution": f"{width}x{height}",
                "format": codec_name,
                "bit_rate": int(probe['format'].get('bit_rate', 0)),
                "size": int(probe['format'].get('size', 0))
            }
        except ffmpeg.Error as e:
            print(f"FFmpeg probe error: {e.stderr.decode('utf8')}")
            raise Exception(f"读取视频元数据失败: {e.stderr.decode('utf8')}")

    def extract_audio(self, video_path: Path, output_path: str = None) -> Path:
        """
        从视频提取音频（转换为 WAV 格式，16kHz，单声道，用于 Whisper 输入）
        
        Args:
            video_path: 视频文件路径
            output_path: 输出音频路径（可选，默认同目录下 audio.wav）
            
        Returns:
            Path: 提取的音频文件路径
        """
        if output_path is None:
            output_path = video_path.parent / "audio.wav"
        else:
            output_path = Path(output_path)

        try:
            # 检查输出文件是否已存在，存在则跳过（或者覆盖）
            # 这里选择覆盖，确保是对应视频的音频
            if output_path.exists():
                output_path.unlink()

            # 使用 ffmpeg 提取音频
            # -vn: 禁用视频
            # -acodec pcm_s16le: 音频编码为 pcm_s16le
            # -ar 16000: 采样率 16kHz (Whisper 推荐)
            # -ac 1: 单声道
            stream = ffmpeg.input(str(video_path))
            stream = ffmpeg.output(stream, str(output_path), vn=None, acodec='pcm_s16le', ar='16000', ac='1')
            ffmpeg.run(stream, capture_stdout=True, capture_stderr=True, overwrite_output=True)
            
            return output_path
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode('utf8') if e.stderr else str(e)
            print(f"FFmpeg extraction error: {error_msg}")
            raise Exception(f"提取音频失败: {error_msg}")

    def generate_thumbnail(self, video_path: Path, output_path: str = None, time: float = 1.0) -> Optional[Path]:
        """
        生成视缩略图
        
        Args:
            video_path: 视频文件路径
            output_path: 输出图片路径
            time: 截取时间点（秒）
            
        Returns:
            Path: 缩略图路径
        """
        if output_path is None:
            output_path = video_path.parent / "thumbnail.jpg"
        else:
            output_path = Path(output_path)
            
        try:
            (
                ffmpeg
                .input(str(video_path), ss=time)
                .output(str(output_path), vframes=1)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            return output_path
        except ffmpeg.Error as e:
            print(f"Thumbnail generation error: {e.stderr.decode('utf8')}")
            return None


# 创建全局实例
ffmpeg_service = FFmpegService()
