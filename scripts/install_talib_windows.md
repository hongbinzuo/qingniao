# TA-Lib Windows 安装指南

## Python 版本
- **当前版本**: Python 3.12.10
- **系统**: Windows (64位)

## 安装方法

### 方法1: 使用预编译的whl文件（推荐）

#### 步骤1: 下载whl文件

访问以下链接下载适合Python 3.12的whl文件：

**选项A: GitHub仓库**
- https://github.com/chenin-wang/ta-lib-python-wheel
- 查找: `TA_Lib-0.4.28-cp312-cp312-win_amd64.whl` 或类似版本

**选项B: 官方源**
- https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
- 查找: `TA_Lib-0.4.28-cp312-cp312-win_amd64.whl`

#### 步骤2: 安装whl文件

```bash
# 将下载的whl文件放到项目目录
# 然后运行：
pip install TA_Lib-0.4.28-cp312-cp312-win_amd64.whl
```

### 方法2: 使用conda（如果有conda）

```bash
conda install -c conda-forge ta-lib
```

### 方法3: 从源码编译（不推荐，复杂）

需要先安装TA-Lib C库，然后编译Python绑定。

## 验证安装

安装完成后，运行：

```bash
python scripts/test_talib_integration.py
```

或直接测试：

```python
python -c "import talib; print('TA-Lib版本:', talib.__version__)"
```

## 常见问题

### 问题1: 找不到适合的whl文件

**解决方案**:
- 尝试使用Python 3.11的whl文件（通常兼容）
- 或使用conda安装

### 问题2: 安装后导入失败

**解决方案**:
- 检查Python版本是否匹配
- 尝试重新安装
- 检查是否有多个Python环境



