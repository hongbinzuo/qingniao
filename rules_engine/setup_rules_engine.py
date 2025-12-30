"""
规则引擎安装和测试脚本
"""

import subprocess
import sys

def install_dependencies():
    """安装依赖包"""
    print("正在安装依赖包...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements_rules.txt"])
        print("✅ 依赖包安装成功！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 安装失败: {e}")
        return False

def test_imports():
    """测试导入"""
    print("\n正在测试导入...")
    try:
        import experta
        print(f"✅ experta 导入成功 (版本: {experta.__version__})")
        
        import yaml
        print("✅ PyYAML 导入成功")
        
        print("\n✅ 所有依赖包已正确安装！")
        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_rules_engine():
    """测试规则引擎"""
    print("\n正在测试规则引擎...")
    try:
        from trading_rules_engine import analyze_with_rules_engine, TradingSignal
        
        # 测试数据
        market_data = {
            'current_price': 87000,
            'ema_144': 86800,
            'ema_169': 86900,
            'vwap': 87050,
            'rsi': 55.0,
            'timeframe': '15m',
            'timestamp': 0.0
        }
        
        patterns = [
            {
                'pattern_type': 'm_top',
                'is_valid': True,
                'price_level': 88000,
                'confidence': 0.85
            }
        ]
        
        support_resistance = {
            'nearest_support': 86500,
            'nearest_resistance': 87500,
            'support_levels': [86500, 86000],
            'resistance_levels': [87500, 88000]
        }
        
        signals = analyze_with_rules_engine(
            market_data=market_data,
            patterns=patterns,
            support_resistance=support_resistance
        )
        
        print(f"✅ 规则引擎测试成功！生成了 {len(signals)} 个信号")
        for signal in signals:
            print(f"   - {signal.rule_name}: {signal.signal_type} @ ${signal.entry:.2f}")
        
        return True
    except Exception as e:
        print(f"❌ 规则引擎测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("智能交易规则引擎 - 安装和测试")
    print("=" * 60)
    
    # 安装依赖
    if not install_dependencies():
        print("\n❌ 安装失败，请手动运行: pip install -r requirements_rules.txt")
        sys.exit(1)
    
    # 测试导入
    if not test_imports():
        print("\n❌ 导入测试失败")
        sys.exit(1)
    
    # 测试规则引擎
    if not test_rules_engine():
        print("\n❌ 规则引擎测试失败")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！规则引擎已准备就绪。")
    print("=" * 60)
    print("\n下一步：")
    print("1. 运行 python integrate_rules_engine.py 测试集成")
    print("2. 编辑 trading_rules_config.yaml 配置规则")
    print("3. 查看 README_RULES_ENGINE.md 了解详细用法")


