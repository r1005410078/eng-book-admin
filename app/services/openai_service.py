"""
OpenAI 服务封装
"""
from typing import Optional, List, Dict, Any
from openai import OpenAI
from app.core.config import settings


class OpenAIService:
    """OpenAI API 服务封装类"""
    
    def __init__(self):
        """初始化 OpenAI 客户端"""
        self.client = OpenAI(
            base_url=settings.OPENAI_BASE_URL,
            api_key=settings.OPENAI_API_KEY
        )
    
    async def translate_text(
        self, 
        text: str, 
        target_language: str = "中文",
        model: str = "gpt-4"
    ) -> str:
        """
        翻译文本
        
        参数:
            text: 要翻译的文本
            target_language: 目标语言，默认为中文
            model: 使用的模型，默认为 gpt-4
            
        返回:
            翻译后的文本
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": f"你是一个专业的翻译助手，请将用户输入的文本翻译成{target_language}。只返回翻译结果，不要添加任何解释。"
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"翻译失败: {str(e)}")
    
    async def analyze_grammar(
        self, 
        sentence: str,
        model: str = "gpt-4"
    ) -> Dict[str, Any]:
        """
        分析句子语法
        
        参数:
            sentence: 要分析的句子
            model: 使用的模型
            
        返回:
            包含语法分析结果的字典
        """
        try:
            prompt = f"""
请分析以下英语句子的语法结构，并以JSON格式返回结果：

句子: {sentence}

请返回以下信息：
1. sentence_structure: 句子结构类型（简单句/复合句/复杂句）
2. grammar_points: 重点语法点列表
3. difficult_words: 难点词汇及解释
4. phrases: 常用短语列表
5. explanation: 整体语法解释

请严格按照JSON格式返回，不要添加其他内容。
"""
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的英语语法分析助手。请以JSON格式返回分析结果。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            raise Exception(f"语法分析失败: {str(e)}")
    
    async def generate_phonetic(
        self, 
        text: str,
        accent: str = "美式",
        model: str = "gpt-4"
    ) -> str:
        """
        生成音标
        
        参数:
            text: 要标注音标的文本
            accent: 口音类型（美式/英式）
            model: 使用的模型
            
        返回:
            带音标的文本
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": f"你是一个专业的英语发音助手，请为用户输入的英文文本标注{accent}发音的国际音标(IPA)。只返回音标，不要添加其他内容。"
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                temperature=0.1
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"音标生成失败: {str(e)}")
    
    async def extract_vocabulary(
        self, 
        text: str,
        difficulty_level: str = "中级",
        model: str = "gpt-4"
    ) -> List[Dict[str, str]]:
        """
        从文本中提取生词
        
        参数:
            text: 要分析的文本
            difficulty_level: 难度级别（初级/中级/高级）
            model: 使用的模型
            
        返回:
            生词列表，每个生词包含单词、音标、释义等信息
        """
        try:
            prompt = f"""
请从以下英文文本中提取适合{difficulty_level}学习者的生词，并以JSON格式返回：

文本: {text}

对于每个生词，请提供：
1. word: 单词
2. phonetic: 音标
3. definition: 中文释义
4. part_of_speech: 词性
5. example: 例句

请以JSON数组格式返回，不要添加其他内容。
"""
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的英语词汇分析助手。请以JSON格式返回生词列表。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            # 假设返回的JSON有一个 "vocabulary" 键
            return result.get("vocabulary", [])
        except Exception as e:
            raise Exception(f"生词提取失败: {str(e)}")
    
    def test_connection(self) -> bool:
        """
        测试 OpenAI API 连接
        
        返回:
            连接是否成功
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": "Hello"}
                ],
                max_tokens=10
            )
            return True
        except Exception as e:
            print(f"OpenAI API 连接失败: {str(e)}")
            return False


# 创建全局服务实例
openai_service = OpenAIService()
