#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K线图表渲染器 - 将K线数据渲染成图片，用于AI视觉比较
"""
import io
import base64
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

try:
    import matplotlib
    matplotlib.use('Agg')  # 非GUI后端
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.patches import Rectangle
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️  matplotlib未安装，图表渲染功能不可用。安装: pip install matplotlib")


class ChartRenderer:
    """K线图表渲染器"""
    
    def __init__(
        self,
        width: int = 1200,
        height: int = 800,
        dpi: int = 100,
        style: str = 'dark_background'  # 或 'default'
    ):
        """
        初始化渲染器
        
        Args:
            width: 图片宽度（像素）
            height: 图片高度（像素）
            dpi: 分辨率
            style: matplotlib样式
        """
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("需要安装matplotlib: pip install matplotlib")
        
        self.width = width
        self.height = height
        self.dpi = dpi
        self.style = style
    
    def render_klines_to_image(
        self,
        klines: List[Dict],
        output_path: Optional[Path] = None,
        title: str = "Price Chart",
        include_volume: bool = True,
        include_ema: bool = True,
        ema_periods: List[int] = [20, 50, 144]
    ) -> Optional[bytes]:
        """
        将K线数据渲染成图片
        
        Args:
            klines: K线数据列表，格式: [
                {"timestamp": 1234567890, "open": 90000, "high": 91000, 
                 "low": 89000, "close": 90500, "volume": 1000},
                ...
            ]
            output_path: 保存路径（可选）
            title: 图表标题
            include_volume: 是否包含成交量
            include_ema: 是否包含EMA
            ema_periods: EMA周期列表
        
        Returns:
            图片的字节数据（PNG格式）
        """
        if not klines or len(klines) < 2:
            return None
        
        try:
            # 设置样式
            plt.style.use(self.style)
            
            # 创建图表
            if include_volume:
                fig, (ax1, ax2) = plt.subplots(
                    2, 1, 
                    figsize=(self.width/self.dpi, self.height/self.dpi),
                    dpi=self.dpi,
                    gridspec_kw={'height_ratios': [3, 1], 'hspace': 0.1}
                )
            else:
                fig, ax1 = plt.subplots(
                    1, 1,
                    figsize=(self.width/self.dpi, self.height/self.dpi),
                    dpi=self.dpi
                )
                ax2 = None
            
            # 准备数据
            dates = [datetime.fromtimestamp(k['timestamp']) for k in klines]
            opens = [k['open'] for k in klines]
            highs = [k['high'] for k in klines]
            lows = [k['low'] for k in klines]
            closes = [k['close'] for k in klines]
            volumes = [k.get('volume', 0) for k in klines]
            
            # 绘制K线（主图）
            self._plot_candlesticks(ax1, dates, opens, highs, lows, closes)
            
            # 绘制EMA
            if include_ema:
                for period in ema_periods:
                    if len(closes) >= period:
                        ema_values = self._calculate_ema(closes, period)
                        ax1.plot(dates, ema_values, label=f'EMA{period}', 
                                linewidth=1.5, alpha=0.7)
            
            # 设置主图
            ax1.set_title(title, fontsize=14, fontweight='bold')
            ax1.set_ylabel('Price', fontsize=12)
            ax1.grid(True, alpha=0.3)
            if include_ema:
                ax1.legend(loc='upper left', fontsize=8)
            
            # 绘制成交量（副图）
            if include_volume and ax2:
                colors = ['#26a69a' if closes[i] >= opens[i] else '#ef5350' 
                         for i in range(len(closes))]
                ax2.bar(dates, volumes, color=colors, alpha=0.6)
                ax2.set_ylabel('Volume', fontsize=10)
                ax2.grid(True, alpha=0.3)
            
            # 格式化x轴日期
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
            ax1.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, len(dates)//10)))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            if ax2:
                ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
            
            plt.tight_layout()
            
            # 保存或返回
            if output_path:
                plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
                plt.close()
                return None
            else:
                # 保存到内存
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=self.dpi, bbox_inches='tight')
                plt.close()
                buf.seek(0)
                return buf.read()
        
        except Exception as e:
            print(f"⚠️  图表渲染失败: {e}")
            if 'fig' in locals():
                plt.close(fig)
            return None
    
    def _plot_candlesticks(self, ax, dates, opens, highs, lows, closes):
        """绘制K线"""
        for i, date in enumerate(dates):
            color = '#26a69a' if closes[i] >= opens[i] else '#ef5350'
            
            # 影线
            ax.plot([date, date], [lows[i], highs[i]], color=color, linewidth=1)
            
            # 实体
            body_height = abs(closes[i] - opens[i])
            body_bottom = min(opens[i], closes[i])
            
            rect = Rectangle(
                (mdates.date2num(date) - 0.3, body_bottom),
                0.6,
                body_height if body_height > 0 else 0.01,
                facecolor=color,
                edgecolor=color,
                alpha=0.8
            )
            ax.add_patch(rect)
    
    def _calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """计算EMA"""
        if len(prices) < period:
            return [None] * len(prices)
        
        multiplier = 2.0 / (period + 1)
        ema = [None] * (period - 1)
        ema.append(sum(prices[:period]) / period)  # 初始值用SMA
        
        for i in range(period, len(prices)):
            ema.append((prices[i] * multiplier) + (ema[-1] * (1 - multiplier)))
        
        return ema
    
    def render_to_base64(self, klines: List[Dict], **kwargs) -> Optional[str]:
        """
        渲染K线并返回base64编码的图片
        
        Returns:
            base64编码的图片字符串（data URL格式）
        """
        image_bytes = self.render_klines_to_image(klines, **kwargs)
        if not image_bytes:
            return None
        
        base64_str = base64.b64encode(image_bytes).decode('utf-8')
        return f"data:image/png;base64,{base64_str}"

