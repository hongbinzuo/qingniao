#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K线图表渲染器 - 使用mplfinance生成专业K线图
用于AI视觉比较和Brooks模式匹配
"""

import base64
import io
import os
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

try:
    if not os.environ.get("MPLBACKEND"):
        # Force non-interactive backend to avoid Tkinter thread issues
        os.environ["MPLBACKEND"] = "Agg"
    try:
        import matplotlib
        matplotlib.use("Agg", force=True)
    except Exception:
        pass
    import mplfinance as mpf

    MPLFINANCE_AVAILABLE = True
except ImportError:
    MPLFINANCE_AVAILABLE = False
    print("Warning: mplfinance not installed. Run: pip install mplfinance")


class ChartRenderer:
    """K线图表渲染器 - 基于mplfinance"""

    # 预定义样式
    STYLES = {
        "dark": "nightclouds",
        "light": "charles",
        "yahoo": "yahoo",
        "classic": "classic",
    }
    _STYLE_ALIASES = {
        "dark_background": "dark",
        "dark-bg": "dark",
        "default": "light",
        "white": "light",
        "light_background": "light",
    }

    def __init__(
        self, width: int = 1200, height: int = 800, dpi: int = 100, style: str = "dark"
    ):
        """
        初始化渲染器

        Args:
            width: 图片宽度（像素）
            height: 图片高度（像素）
            dpi: 分辨率
            style: 样式 ('dark', 'light', 'yahoo', 'classic')
        """
        if not MPLFINANCE_AVAILABLE:
            raise ImportError("需要安装mplfinance: pip install mplfinance")

        self.width = width
        self.height = height
        self.dpi = dpi
        style_key = self._STYLE_ALIASES.get(style, style)
        self.style = self.STYLES.get(style_key, style_key)

    def _prepare_dataframe(self, klines: List[Dict]) -> pd.DataFrame:
        """将K线数据转换为mplfinance所需的DataFrame格式"""
        df = pd.DataFrame(klines)

        # 处理时间戳
        if "timestamp" in df.columns:
            df["Date"] = pd.to_datetime(df["timestamp"], unit="s")
        elif "time" in df.columns:
            df["Date"] = pd.to_datetime(df["time"], unit="s")
        else:
            df["Date"] = pd.to_datetime(df.index)

        df = df.set_index("Date")

        # 重命名列为mplfinance标准格式
        column_map = {
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
        df = df.rename(columns=column_map)

        # 确保数值类型
        for col in ["Open", "High", "Low", "Close"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if "Volume" in df.columns:
            df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce").fillna(0)

        return df[["Open", "High", "Low", "Close", "Volume"]]

    def render_klines_to_image(
        self,
        klines: List[Dict],
        output_path: Optional[Path] = None,
        title: str = "",
        include_volume: bool = True,
        include_ema: bool = True,
        ema_periods: List[int] = [20, 50],
        show_grid: bool = True,
        show_axes: bool = True,
        show_title: bool = True,
        show_legend: bool = True,
    ) -> Optional[bytes]:
        """
        将K线数据渲染成图片

        Args:
            klines: K线数据列表
            output_path: 保存路径（可选）
            title: 图表标题
            include_volume: 是否包含成交量
            include_ema: 是否包含EMA
            ema_periods: EMA周期列表
            show_grid: 是否显示网格
            show_axes: 是否显示坐标轴
            show_title: 是否显示标题
            show_legend: 是否显示图例

        Returns:
            图片的字节数据（PNG格式），如果指定output_path则返回None
        """
        if not klines or len(klines) < 2:
            return None

        try:
            df = self._prepare_dataframe(klines)

            # 构建mplfinance参数
            kwargs = {
                "type": "candle",
                "style": self.style,
                "volume": include_volume,
                "figsize": (self.width / self.dpi, self.height / self.dpi),
            }

            # 网格样式
            if not show_grid:
                try:
                    kwargs["style"] = mpf.make_mpf_style(
                        base_mpf_style=self.style,
                        gridstyle="",
                        gridcolor="none",
                    )
                except Exception:
                    # 如果style构建失败，忽略网格控制
                    pass

            # 坐标轴显示
            if not show_axes:
                kwargs["axisoff"] = True

            # 添加EMA
            if include_ema and ema_periods:
                kwargs["mav"] = tuple(p for p in ema_periods if p < len(df))

            # 标题
            if show_title and title:
                kwargs["title"] = title

            # 保存到文件或内存
            if output_path:
                kwargs["savefig"] = str(output_path)
                try:
                    mpf.plot(df, **kwargs)
                except TypeError:
                    # 兼容旧版本mplfinance参数
                    kwargs.pop("axisoff", None)
                    mpf.plot(df, **kwargs)
                return None
            else:
                buf = io.BytesIO()
                kwargs["savefig"] = dict(fname=buf, dpi=self.dpi, bbox_inches="tight")
                try:
                    mpf.plot(df, **kwargs)
                except TypeError:
                    kwargs.pop("axisoff", None)
                    mpf.plot(df, **kwargs)
                buf.seek(0)
                return buf.read()

        except Exception as e:
            print(f"Chart render failed: {e}")
            return None

    def render_to_base64(self, klines: List[Dict], **kwargs) -> Optional[str]:
        """
        渲染K线并返回base64编码的图片

        Returns:
            base64编码的图片字符串（data URL格式）
        """
        image_bytes = self.render_klines_to_image(klines, **kwargs)
        if not image_bytes:
            return None

        base64_str = base64.b64encode(image_bytes).decode("utf-8")
        return f"data:image/png;base64,{base64_str}"

    def render_clean(
        self,
        klines: List[Dict],
        output_path: Optional[Path] = None,
    ) -> Optional[bytes]:
        """
        渲染干净的K线图（无标题、无指标）- 用于AI视觉比较

        Args:
            klines: K线数据列表
            output_path: 保存路径（可选）

        Returns:
            图片字节数据
        """
        return self.render_klines_to_image(
            klines,
            output_path=output_path,
            title="",
            include_volume=False,
            include_ema=False,
            show_grid=False,
            show_axes=False,
            show_title=False,
            show_legend=False,
        )
