"""
SRT 字幕处理工具
"""
import re
from typing import List, Dict, Any
from datetime import timedelta
import srt

class SRTParser:
    """SRT 字幕解析器"""

    @staticmethod
    def parse_srt_file(file_path: str) -> List[Dict[str, Any]]:
        """
        解析 SRT 文件
        
        Args:
            file_path: SRT 文件路径
            
        Returns:
            List[Dict]: 字幕列表 [{'index': 1, 'start': 0.0, 'end': 1.0, 'content': 'text'}]
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return SRTParser.parse_srt_content(content)
        except Exception as e:
            print(f"Error parsing SRT file: {e}")
            raise

    @staticmethod
    def parse_srt_content(content: str) -> List[Dict[str, Any]]:
        """
        解析 SRT 文本内容
        
        Args:
            content: SRT 格式文本
            
        Returns:
            List[Dict]: 解析后的字幕列表
        """
        subtitles = []
        try:
            # 使用 srt 库解析
            parsed_subs = list(srt.parse(content))
            
            for sub in parsed_subs:
                subtitles.append({
                    "sequence_number": sub.index,
                    "start_time": sub.start.total_seconds(),
                    "end_time": sub.end.total_seconds(),
                    "original_text": sub.content.strip()
                })
        except Exception as e:
            # 如果 srt 库解析失败，尝试手动解析作为后备方案
            print(f"srt library parse failed: {e}, using fallback parser")
            subtitles = SRTParser._fallback_parser(content)
            
        return subtitles

    @staticmethod
    def _fallback_parser(content: str) -> List[Dict[str, Any]]:
        """
        手 SRT 解析器（后备方案）
        """
        # 标准化换行符
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        # 分割块（两个换行符）
        blocks = content.strip().split('\n\n')
        
        subtitles = []
        
        for block in blocks:
            lines = block.split('\n')
            if len(lines) >= 3:
                try:
                    # 序号
                    index = int(lines[0])
                    
                    # 时间轴: 00:00:00,000 --> 00:00:02,000
                    time_line = lines[1]
                    start_str, end_str = time_line.split(' --> ')
                    start_time = SRTParser._parse_timestamp(start_str)
                    end_time = SRTParser._parse_timestamp(end_str)
                    
                    # 内容 (可能有多行)
                    text = '\n'.join(lines[2:])
                    
                    subtitles.append({
                        "sequence_number": index,
                        "start_time": start_time,
                        "end_time": end_time,
                        "original_text": text
                    })
                except Exception as e:
                    print(f"Error parsing subtitle block: {block[:50]}... Error: {e}")
                    continue
                    
        return subtitles

    @staticmethod
    def _parse_timestamp(timestamp_str: str) -> float:
        """解析 SRT 时间戳为秒数 (00:00:01,500 -> 1.5)"""
        timestamp_str = timestamp_str.replace(',', '.')
        h, m, s = timestamp_str.split(':')
        seconds = float(s) + int(m) * 60 + int(h) * 3600
        return seconds

    @staticmethod
    def generate_srt(subtitles: List[Dict[str, Any]]) -> str:
        """
        生成 SRT 文本
        
        Args:
            subtitles: 字幕字典列表
            
        Returns:
            str: SRT 格式文本
        """
        srt_subs = []
        for sub in subtitles:
            srt_sub = srt.Subtitle(
                index=sub.get('sequence_number', 0),
                start=timedelta(seconds=float(sub['start_time'])),
                end=timedelta(seconds=float(sub['end_time'])),
                content=sub['original_text']
            )
            srt_subs.append(srt_sub)
            
        return srt.compose(srt_subs)
