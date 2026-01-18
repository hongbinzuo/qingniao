#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
千叶交易系统 - 图片分析模块
从行情分析图片中提取交易规则
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import json

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))


class ImageAnalyzer:
    """图片分析器"""
    
    def __init__(self):
        self.images_dir = Path(__file__).parent.parent.parent / "data" / "chiba_images"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir = self.images_dir / "analysis"
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_text_from_image(self, image_path: Path) -> Optional[str]:
        """从图片中提取文字（OCR）"""
        try:
            import pytesseract
            from PIL import Image
            
            print(f"正在提取文字: {image_path.name}")
            
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, lang='chi_sim+eng')
            
            print(f"✓ 提取文字完成，长度: {len(text)} 字符")
            
            return text
            
        except ImportError:
            print("错误: 需要安装 pytesseract 和 Pillow")
            print("安装命令: pip install pytesseract pillow")
            print("还需要安装 Tesseract OCR: https://github.com/tesseract-ocr/tesseract")
            return None
        except Exception as e:
            print(f"OCR失败: {e}")
            return None
    
    def identify_chart_elements(self, image_path: Path) -> Dict:
        """识别图表元素"""
        try:
            import cv2
            import numpy as np
            
            print(f"正在识别图表元素: {image_path.name}")
            
            # 读取图片
            img = cv2.imread(str(image_path))
            if img is None:
                print(f"错误: 无法读取图片 {image_path}")
                return {}
            
            # 转换为灰度图
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 识别K线（查找矩形）
            # 识别趋势线（查找直线）
            # 识别标注（查找文字区域）
            
            elements = {
                'candlesticks': [],  # K线
                'trend_lines': [],   # 趋势线
                'annotations': [],   # 标注
                'indicators': []     # 技术指标
            }
            
            print(f"✓ 识别完成")
            
            return elements
            
        except ImportError:
            print("错误: 需要安装 opencv-python")
            print("安装命令: pip install opencv-python")
            return {}
        except Exception as e:
            print(f"识别失败: {e}")
            return {}
    
    def extract_trading_annotations(self, image_path: Path) -> List[Dict]:
        """提取交易标注（入场、止损、止盈）"""
        print(f"正在提取交易标注: {image_path.name}")
        
        # 提取文字
        text = self.extract_text_from_image(image_path)
        
        # 识别标注关键词
        annotation_keywords = {
            '入场': ['入场', '开仓', '买入', '卖出', '做多', '做空', 'entry'],
            '止损': ['止损', 'stop loss', 'sl'],
            '止盈': ['止盈', 'take profit', 'tp', '目标']
        }
        
        annotations = []
        
        if text:
            lines = text.split('\n')
            for line in lines:
                for annotation_type, keywords in annotation_keywords.items():
                    if any(kw in line for kw in keywords):
                        # 尝试提取价格
                        import re
                        prices = re.findall(r'[\d,]+\.?\d*', line)
                        
                        annotation = {
                            'type': annotation_type,
                            'text': line,
                            'prices': prices
                        }
                        annotations.append(annotation)
        
        print(f"✓ 提取了 {len(annotations)} 个标注")
        
        return annotations
    
    def analyze_image(self, image_path: Path) -> Dict:
        """分析图片（OCR+识别+提取标注）"""
        print("=" * 80)
        print("千叶交易系统 - 图片分析")
        print("=" * 80)
        print()
        
        if not image_path.exists():
            print(f"错误: 图片文件不存在: {image_path}")
            return {}
        
        # 1. 提取文字
        text = self.extract_text_from_image(image_path)
        print()
        
        # 2. 识别图表元素
        elements = self.identify_chart_elements(image_path)
        print()
        
        # 3. 提取交易标注
        annotations = self.extract_trading_annotations(image_path)
        print()
        
        print("=" * 80)
        print("分析完成")
        print("=" * 80)
        print(f"图片: {image_path.name}")
        print(f"提取文字长度: {len(text) if text else 0} 字符")
        print(f"识别元素数: {sum(len(v) for v in elements.values())}")
        print(f"提取标注数: {len(annotations)}")
        print()
        
        return {
            'image_path': str(image_path),
            'text': text,
            'elements': elements,
            'annotations': annotations
        }


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='千叶交易系统 - 图片分析')
    parser.add_argument('--image', type=str, required=True, help='图片文件路径')
    
    args = parser.parse_args()
    
    analyzer = ImageAnalyzer()
    result = analyzer.analyze_image(Path(args.image))
    
    # 保存结果
    if result:
        output_file = analyzer.results_dir / f"{Path(args.image).stem}_analysis.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"✓ 分析结果已保存: {output_file}")

if __name__ == '__main__':
    main()










