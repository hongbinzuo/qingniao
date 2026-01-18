#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接视觉分析器 - 使用Gemini Vision直接分析实时图表

方案1：不使用模式库图片对比，直接让Gemini Vision分析实时图表，
识别模式并与模式库的特征描述匹配。
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
    ChartRenderer = None


@dataclass
class DirectVisionResult:
    """直接视觉分析结果"""
    pattern_name: str  # 识别的模式名称
    pattern_type: str  # 模式类型
    direction: str  # 'long' or 'short'
    confidence: float  # 0-1
    key_features: List[str]  # 识别的关键特征
    trading_signals: List[str]  # 交易信号
    reasoning: str  # AI的推理过程
    ai_model: str  # 使用的模型
    estimated_cost: float  # 估算成本（USD）


class DirectVisionAnalyzer:
    """直接视觉分析器 - 使用Gemini Vision直接分析实时图表"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: str = "https://openrouter.ai/api/v1",
        model: str = "google/gemini-2.5-flash-image",
        use_openrouter: bool = True
    ):
        """
        初始化直接视觉分析器
        
        Args:
            api_key: OpenRouter API Key
            api_url: API地址
            model: 使用的Vision模型
            use_openrouter: 是否使用OpenRouter
        """
        # 获取API Key
        if not api_key:
            api_key = os.getenv('OPENROUTER_API_KEY')
            if not api_key:
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
        
        # 成本统计
        self.total_calls = 0
        self.total_cost = 0.0
    
    def analyze_chart_directly(
        self,
        chart_image_path: Path,
        pattern_candidates: Optional[List[Dict]] = None,
        symbol: str = "BTC",
        timeframe: str = "15m"
    ) -> DirectVisionResult:
        """
        直接分析实时图表，识别模式
        
        Args:
            chart_image_path: 实时图表图片路径
            pattern_candidates: 模式候选列表（可选，用于提供上下文）
            symbol: 币种符号
            timeframe: 时间框架
        
        Returns:
            分析结果
        """
        # 编码图片
        image_base64 = self._encode_image(chart_image_path)
        if not image_base64:
            return DirectVisionResult(
                pattern_name="Unknown",
                pattern_type="unknown",
                direction="neutral",
                confidence=0.0,
                key_features=[],
                trading_signals=[],
                reasoning="图片编码失败",
                ai_model=self.model,
                estimated_cost=0.0
            )
        
        # 构建prompt
        prompt = self._build_analysis_prompt(symbol, timeframe, pattern_candidates)
        
        # 调用Vision API
        start_time = time.time()
        api_result = self._call_vision_api(image_base64, prompt)
        elapsed = time.time() - start_time
        
        # 估算成本
        cost = self._estimate_cost(1)
        self.total_calls += 1
        self.total_cost += cost
        
        # 解析结果
        result = self._parse_analysis_result(api_result)
        result.estimated_cost = cost
        
        return result
    
    def _build_analysis_prompt(
        self,
        symbol: str,
        timeframe: str,
        pattern_candidates: Optional[List[Dict]] = None
    ) -> str:
        """构建分析prompt"""
        base_prompt = f"""你是专业的交易图表分析专家。请分析这张{symbol}的{timeframe}价格图表，识别其中的交易模式。

请分析以下内容：

1. **模式识别**：
   - 识别图表中的主要模式（如：Wedge, Triangle, Channel, Double Top/Bottom等）
   - 判断模式类型（反转模式、延续模式等）
   - 评估模式的完成度（是否形成、是否突破等）

2. **趋势分析**：
   - 当前趋势方向（上升、下降、横盘）
   - 趋势强度（强、中、弱）
   - 是否有趋势反转信号

3. **价格行为特征**：
   - K线结构（如：engulfing, inside bar等）
   - 支撑阻力位
   - 关键价格水平

4. **交易方向**：
   - 基于模式识别，判断交易方向（long/short）
   - 给出置信度（0-1）

5. **交易信号**：
   - 入场条件
   - 止损位置建议
   - 止盈目标建议

"""
        
        # 如果提供了模式候选，添加上下文
        if pattern_candidates:
            base_prompt += "\n**模式库候选**（供参考）：\n"
            for i, candidate in enumerate(pattern_candidates[:5], 1):  # 只显示Top 5
                base_prompt += f"{i}. {candidate.get('pattern_name', 'Unknown')} "
                base_prompt += f"({candidate.get('pattern_type', 'unknown')})\n"
            base_prompt += "\n请判断实时图表最匹配哪个模式，或识别出新的模式。\n"
        
        base_prompt += """
请以JSON格式输出：
{
  "pattern_name": "识别的模式名称",
  "pattern_type": "模式类型（如：wedge, triangle, channel等）",
  "direction": "long 或 short",
  "confidence": 0.85,
  "key_features": [
    "关键特征1",
    "关键特征2"
  ],
  "trading_signals": [
    "交易信号1",
    "交易信号2"
  ],
  "reasoning": "详细说明识别过程和判断依据"
}"""
        
        return base_prompt
    
    def _encode_image(self, image_path: Path) -> Optional[str]:
        """将图片编码为base64 data URL"""
        try:
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            base64_str = base64.b64encode(image_bytes).decode('utf-8')
            
            suffix = image_path.suffix.lower()
            mime_type = 'image/png' if suffix == '.png' else 'image/jpeg' if suffix in ['.jpg', '.jpeg'] else 'image/png'
            
            return f"data:{mime_type};base64,{base64_str}"
        except Exception as e:
            print(f"⚠️  图片编码失败 {image_path}: {e}")
            return None
    
    def _call_vision_api(self, image_base64: str, prompt: str) -> Dict:
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
                            "image_url": {"url": image_base64}
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
            "X-Title": "QingNiao Direct Vision Analyzer"
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"API请求失败: {response.status_code}", "response_text": response.text}
        
        except Exception as e:
            return {"error": f"API调用异常: {str(e)}"}
    
    def _parse_analysis_result(self, api_result: Dict) -> DirectVisionResult:
        """解析API返回结果"""
        try:
            if 'error' in api_result:
                return DirectVisionResult(
                    pattern_name="Unknown",
                    pattern_type="unknown",
                    direction="neutral",
                    confidence=0.0,
                    key_features=[],
                    trading_signals=[],
                    reasoning=f"API调用失败: {api_result['error']}",
                    ai_model=self.model,
                    estimated_cost=0.0
                )
            
            if 'choices' not in api_result or len(api_result['choices']) == 0:
                return DirectVisionResult(
                    pattern_name="Unknown",
                    pattern_type="unknown",
                    direction="neutral",
                    confidence=0.0,
                    key_features=[],
                    trading_signals=[],
                    reasoning="API响应格式异常",
                    ai_model=self.model,
                    estimated_cost=0.0
                )
            
            content = api_result['choices'][0]['message']['content']
            
            # 提取JSON
            json_str = self._extract_json_from_text(content)
            if not json_str:
                return DirectVisionResult(
                    pattern_name="Unknown",
                    pattern_type="unknown",
                    direction="neutral",
                    confidence=0.0,
                    key_features=[],
                    trading_signals=[],
                    reasoning=content[:500],
                    ai_model=self.model,
                    estimated_cost=0.0
                )
            
            data = json.loads(json_str)
            
            return DirectVisionResult(
                pattern_name=data.get('pattern_name', 'Unknown'),
                pattern_type=data.get('pattern_type', 'unknown'),
                direction=data.get('direction', 'neutral'),
                confidence=float(data.get('confidence', 0.0)),
                key_features=data.get('key_features', []),
                trading_signals=data.get('trading_signals', []),
                reasoning=data.get('reasoning', ''),
                ai_model=self.model,
                estimated_cost=0.0  # 将在外部设置
            )
        
        except Exception as e:
            return DirectVisionResult(
                pattern_name="Unknown",
                pattern_type="unknown",
                direction="neutral",
                confidence=0.0,
                key_features=[],
                trading_signals=[],
                reasoning=f"解析失败: {str(e)}",
                ai_model=self.model,
                estimated_cost=0.0
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
    
    def _estimate_cost(self, image_count: int) -> float:
        """
        估算API成本
        
        基于实际使用数据：
        - 单张成本: $0.0088/张（基于之前的测试数据）
        - 但这是对比两张图片的成本
        - 单张图片分析成本应该更低，估算为 $0.005/张
        """
        return image_count * 0.005
    
    def get_cost_summary(self) -> Dict:
        """获取成本统计"""
        return {
            'total_calls': self.total_calls,
            'total_cost_usd': self.total_cost,
            'avg_cost_per_call': self.total_cost / self.total_calls if self.total_calls > 0 else 0.0
        }
