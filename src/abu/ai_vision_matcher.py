#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI视觉图表匹配器 - 使用Vision API比较两张图表图片
"""
import os
import json
import time
import requests
import base64
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

try:
    from .chart_renderer import ChartRenderer
    CHART_RENDERER_AVAILABLE = True
except ImportError:
    CHART_RENDERER_AVAILABLE = False
    print("⚠️  ChartRenderer未导入")


@dataclass
class VisionMatchResult:
    """视觉匹配结果"""
    similarity_score: float  # 0-100
    confidence: float  # 0-1
    key_matches: List[str]  # 匹配的关键特征
    differences: List[str]  # 差异点
    reasoning: str  # AI的推理过程
    ai_model: str  # 使用的模型


class AIVisionMatcher:
    """AI视觉图表匹配器"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: str = "https://openrouter.ai/api/v1",
        model: str = "google/gemini-2.5-flash-image",  # 或 "google/gemini-3-flash-preview" (如果可用)
        use_openrouter: bool = True
    ):
        """
        初始化AI视觉匹配器
        
        Args:
            api_key: OpenRouter API Key（从环境变量获取）
            api_url: API地址
            model: 使用的Vision模型
            use_openrouter: 是否使用OpenRouter
        """
        # 获取API Key
        if not api_key:
            # 尝试从环境变量获取
            api_key = os.getenv('OPENROUTER_API_KEY')
            if not api_key:
                # 尝试从openrouter_config获取
                try:
                    from openrouter_config import get_openrouter_api_key
                    api_key = get_openrouter_api_key()
                except ImportError:
                    try:
                        from src.openrouter_config import get_openrouter_api_key
                        api_key = get_openrouter_api_key()
                    except ImportError:
                        pass
        
        if not api_key:
            raise ValueError("需要设置 OPENROUTER_API_KEY 环境变量或配置openrouter_config")
        
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.use_openrouter = use_openrouter
        self.chart_renderer = ChartRenderer() if CHART_RENDERER_AVAILABLE else None
    
    def compare_two_images(
        self,
        image1_path: Path,
        image2_path: Path,
        context: Optional[str] = None
    ) -> VisionMatchResult:
        """
        比较两张图表图片的相似度
        
        Args:
            image1_path: 模式库图片路径（PDF中的图表）
            image2_path: 实时K线渲染的图片路径
            context: 额外的上下文信息（可选）
        
        Returns:
            匹配结果
        """
        # 编码两张图片
        image1_base64 = self._encode_image(image1_path)
        image2_base64 = self._encode_image(image2_path)
        
        if not image1_base64 or not image2_base64:
            return VisionMatchResult(
                similarity_score=0.0,
                confidence=0.0,
                key_matches=[],
                differences=["图片编码失败"],
                reasoning="无法读取图片",
                ai_model=self.model
            )
        
        # 构建prompt
        prompt = self._build_comparison_prompt(context)
        
        # 调用Vision API
        result = self._call_vision_api(image1_base64, image2_base64, prompt)
        
        # 解析结果
        return self._parse_match_result(result)
    
    def compare_chart_with_realtime(
        self,
        pattern_image_path: Path,
        realtime_klines: List[Dict],
        pattern_info: Optional[Dict] = None
    ) -> VisionMatchResult:
        """
        直接将模式库图片与实时K线数据比较（自动渲染实时K线）
        
        Args:
            pattern_image_path: 模式库中的图表图片
            realtime_klines: 实时K线数据
            pattern_info: 模式信息（可选，用于提供上下文）
        
        Returns:
            匹配结果
        """
        if not self.chart_renderer:
            return VisionMatchResult(
                similarity_score=0.0,
                confidence=0.0,
                key_matches=[],
                differences=["图表渲染器不可用"],
                reasoning="无法渲染实时K线图表",
                ai_model=self.model
            )
        
        # 渲染实时K线为图片
        temp_image = Path(f"/tmp/realtime_chart_{int(time.time())}.png")
        image_bytes = self.chart_renderer.render_klines_to_image(
            realtime_klines,
            output_path=temp_image,
            title="Realtime Price Chart"
        )
        
        if not image_bytes and not temp_image.exists():
            return VisionMatchResult(
                similarity_score=0.0,
                confidence=0.0,
                key_matches=[],
                differences=["实时K线渲染失败"],
                reasoning="无法渲染实时K线图表",
                ai_model=self.model
            )
        
        # 构建上下文
        context = None
        if pattern_info:
            context = f"""
            模式信息：
            - 模式名称: {pattern_info.get('pattern_name', 'Unknown')}
            - 模式类型: {pattern_info.get('pattern_type', 'Unknown')}
            - 描述: {pattern_info.get('complete_narrative', '')[:500]}
            """
        
        # 比较
        result = self.compare_two_images(pattern_image_path, temp_image, context)
        
        # 清理临时文件
        if temp_image.exists():
            try:
                temp_image.unlink()
            except Exception:
                pass
        
        return result
    
    def _build_comparison_prompt(self, context: Optional[str] = None) -> str:
        """构建比较prompt"""
        base_prompt = """你是专业的交易图表分析专家。请比较这两张价格图表，评估它们的相似度。

图片1：模式库中的标准模式图表（Al Brooks教学图表）
图片2：实时价格图表（需要匹配的图表）

请分析：
1. **整体相似度**（0-100分）：两张图表的整体形态是否相似？
2. **关键特征匹配**：哪些价格行为特征匹配？（如：趋势、模式形态、K线结构等）
3. **差异点**：有哪些明显不同？
4. **匹配置信度**（0-1）：你有多确信这两张图表匹配？

请以JSON格式输出：
{
  "similarity_score": 85,
  "confidence": 0.82,
  "key_matches": [
    "上升趋势结构相似",
    "都有small pullback形态",
    "都有breakout结构"
  ],
  "differences": [
    "实时图表波动更大",
    "模式库图表有更明确的reversal信号"
  ],
  "reasoning": "详细说明为什么给出这个相似度评分"
}"""
        
        if context:
            base_prompt += f"\n\n额外上下文：\n{context}"
        
        return base_prompt
    
    def _encode_image(self, image_path: Path) -> Optional[str]:
        """将图片编码为base64 data URL"""
        try:
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            base64_str = base64.b64encode(image_bytes).decode('utf-8')
            
            # 检测MIME类型
            suffix = image_path.suffix.lower()
            mime_type = 'image/png' if suffix == '.png' else 'image/jpeg' if suffix in ['.jpg', '.jpeg'] else 'image/png'
            
            return f"data:{mime_type};base64,{base64_str}"
        except Exception as e:
            print(f"⚠️  图片编码失败 {image_path}: {e}")
            return None
    
    def _call_vision_api(
        self,
        image1_base64: str,
        image2_base64: str,
        prompt: str
    ) -> Dict:
        """调用Vision API"""
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": image1_base64}
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": image2_base64}
                        }
                    ]
                }
            ],
            "temperature": 0.1,
            "max_tokens": 2000
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/qingniao",
            "X-Title": "QingNiao AI Vision Matcher"
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                return {"error": f"API请求失败: {response.status_code}", "response_text": response.text}
        
        except Exception as e:
            return {"error": f"API调用异常: {str(e)}"}
    
    def _parse_match_result(self, api_result: Dict) -> VisionMatchResult:
        """解析API返回结果"""
        try:
            if 'error' in api_result:
                return VisionMatchResult(
                    similarity_score=0.0,
                    confidence=0.0,
                    key_matches=[],
                    differences=[api_result['error']],
                    reasoning="API调用失败",
                    ai_model=self.model
                )
            
            if 'choices' not in api_result or len(api_result['choices']) == 0:
                return VisionMatchResult(
                    similarity_score=0.0,
                    confidence=0.0,
                    key_matches=[],
                    differences=["API响应格式异常"],
                    reasoning="API返回格式不正确",
                    ai_model=self.model
                )
            
            content = api_result['choices'][0]['message']['content']
            
            # 提取JSON
            json_str = self._extract_json_from_text(content)
            if not json_str:
                # 如果无法解析JSON，尝试从文本中提取信息
                return VisionMatchResult(
                    similarity_score=0.0,
                    confidence=0.0,
                    key_matches=[],
                    differences=["无法解析AI返回结果"],
                    reasoning=content[:500],
                    ai_model=self.model
                )
            
            data = json.loads(json_str)
            
            return VisionMatchResult(
                similarity_score=float(data.get('similarity_score', 0)),
                confidence=float(data.get('confidence', 0)),
                key_matches=data.get('key_matches', []),
                differences=data.get('differences', []),
                reasoning=data.get('reasoning', ''),
                ai_model=self.model
            )
        
        except Exception as e:
            return VisionMatchResult(
                similarity_score=0.0,
                confidence=0.0,
                key_matches=[],
                differences=[f"解析失败: {str(e)}"],
                reasoning="结果解析异常",
                ai_model=self.model
            )
    
    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """从文本中提取JSON"""
        import re
        
        # 方法1: 找```json```块
        json_block = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
        if json_block:
            return json_block.group(1).strip()
        
        # 方法2: 找第一个{...}
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return None

