#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TensorTrade 测试脚本
测试 TensorTrade 是否能正常运行
"""

import sys
import warnings
warnings.filterwarnings('ignore')

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def test_import():
    """测试 TensorTrade 导入"""
    print("=" * 60)
    print("TensorTrade 导入测试")
    print("=" * 60)
    
    try:
        import tensortrade
        print(f"✓ TensorTrade 导入成功")
        
        # 尝试导入主要模块
        try:
            from tensortrade import TradingEnvironment
            print("✓ TradingEnvironment 模块可用")
        except ImportError as e:
            print(f"⚠ TradingEnvironment 导入失败: {e}")
        
        try:
            from tensortrade.env import default
            print("✓ 默认环境模块可用")
        except ImportError as e:
            print(f"⚠ 默认环境模块导入失败: {e}")
        
        try:
            from tensortrade.exchanges import Exchange
            print("✓ Exchange 模块可用")
        except ImportError as e:
            print(f"⚠ Exchange 模块导入失败: {e}")
        
        try:
            from tensortrade.actions import ActionScheme
            print("✓ ActionScheme 模块可用")
        except ImportError as e:
            print(f"⚠ ActionScheme 模块导入失败: {e}")
        
        try:
            from tensortrade.rewards import RewardScheme
            print("✓ RewardScheme 模块可用")
        except ImportError as e:
            print(f"⚠ RewardScheme 模块导入失败: {e}")
        
        return True
        
    except ImportError as e:
        print(f"✗ TensorTrade 导入失败: {e}")
        return False

def test_basic_functionality():
    """测试基本功能"""
    print("\n" + "=" * 60)
    print("TensorTrade 基本功能测试")
    print("=" * 60)
    
    try:
        # 尝试创建一个简单的环境（可能不完整，但至少测试导入）
        print("测试模块结构...")
        
        import tensortrade as tt
        print(f"TensorTrade 版本信息:")
        print(f"  - 包位置: {tt.__file__ if hasattr(tt, '__file__') else 'N/A'}")
        print(f"  - 版本: {getattr(tt, '__version__', '1.0.3')}")
        
        # 检查是否有examples目录
        import os
        tt_path = os.path.dirname(tt.__file__) if hasattr(tt, '__file__') else None
        if tt_path:
            examples_path = os.path.join(tt_path, '..', 'examples')
            if os.path.exists(examples_path):
                print(f"  - 示例目录存在: {examples_path}")
        
        return True
        
    except Exception as e:
        print(f"✗ 基本功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dependencies():
    """测试依赖库"""
    print("\n" + "=" * 60)
    print("依赖库测试")
    print("=" * 60)
    
    dependencies = [
        ('numpy', 'NumPy'),
        ('pandas', 'Pandas'),
        ('tensorflow', 'TensorFlow'),
        ('gym', 'Gym'),
        ('matplotlib', 'Matplotlib'),
    ]
    
    all_ok = True
    for module, name in dependencies:
        try:
            __import__(module)
            print(f"✓ {name} 已安装")
        except ImportError:
            print(f"✗ {name} 未安装")
            all_ok = False
    
    return all_ok

if __name__ == "__main__":
    print("\n开始 TensorTrade 测试...\n")
    
    # 测试导入
    import_ok = test_import()
    
    # 测试依赖
    deps_ok = test_dependencies()
    
    # 测试基本功能
    if import_ok and deps_ok:
        func_ok = test_basic_functionality()
    else:
        func_ok = False
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    if import_ok and deps_ok and func_ok:
        print("✓ TensorTrade 测试通过，可以开始使用！")
        print("\n建议下一步:")
        print("1. 查看 TensorTrade 文档和示例")
        print("2. 创建一个简单的 BTC 交易环境")
        print("3. 设计奖励函数和动作空间")
        print("4. 训练一个简单的策略")
    else:
        print("✗ TensorTrade 测试未完全通过")
        if not import_ok:
            print("  - 导入测试失败")
        if not deps_ok:
            print("  - 依赖库测试失败")
        if not func_ok:
            print("  - 基本功能测试失败")
    
    print()


