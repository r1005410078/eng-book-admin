"""
Whisper 服务模块
使用本地 Whisper 模型进行语音识别
"""
import os
import torch
import whisper
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import timedelta
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WhisperService:
    """Whisper 服务类"""
    
    _model = None
    _model_name = "medium"  # 默认模型
    _device = None

    @classmethod
    def get_device(cls) -> str:
        """获取计算设备 (cuda 或 cpu)"""
        if cls._device is None:
            cls._device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {cls._device}")
        return cls._device

    @classmethod
    def load_model(cls, model_name: str = None) -> Any:
        """
        加载 Whisper 模型（单例模式）
        
        Args:
            model_name: 模型名称 (tiny, base, small, medium, large)
        
        Returns:
            加载的模型实例
        """
        model_to_load = model_name or cls._model_name
        
        # 如果模型已加载且名称相同，直接返回
        if cls._model is not None and cls._model_name == model_to_load:
            return cls._model
            
        logger.info(f"Loading Whisper model: {model_to_load} on {cls.get_device()}...")
        try:
            cls._model = whisper.load_model(model_to_load, device=cls.get_device())
            cls._model_name = model_to_load
            logger.info("Model loaded successfully")
            return cls._model
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise

    def transcribe(
        self,
        audio_path: Path,
        model_name: str = "medium",
        language: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        转录音频文件
        
        Args:
            audio_path: 音频文件路径
            model_name: 模型名称 (默认 medium)
            language: 语言代码 (默认 en)
            
        Returns:
            List[Dict]: 转录结果列表
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
        try:
            model = self.load_model(model_name)
            
            # 转录选项
            options = {
                "language": language,
                "task": "transcribe",
                "verbose": False
            }
            
            logger.info(f"Starting transcription for {audio_path}...")
            result = model.transcribe(str(audio_path), **options)
            
            segments = result.get("segments", [])
            logger.info(f"Transcription completed. Found {len(segments)} segments.")
            
            # 格式化结果
            formatted_segments = []
            for i, segment in enumerate(segments, 1):
                formatted_segments.append({
                    "sequence_number": i,
                    "start_time": segment["start"],
                    "end_time": segment["end"],
                    "original_text": segment["text"].strip(),
                    "confidence": segment.get("avg_logprob", 0.0)  # 可选：置信度
                })
                
            return formatted_segments
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise

    def generate_srt_content(self, segments: List[Dict[str, Any]]) -> str:
        """
        将转录结果生成 SRT 格式内容
        
        Args:
            segments: 转录片段列表
            
        Returns:
            str: SRT 格式文本
        """
        from app.utils.srt_parser import SRTParser
        return SRTParser.generate_srt(segments)


# 创建全局实例
whisper_service = WhisperService()
