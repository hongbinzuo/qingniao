# De.对话录入系统使用说明

## 📋 系统功能

1. **自动记录处理进度**: 记录上次处理到哪条消息
2. **断点续传**: 下次运行自动从上次停止的地方继续
3. **交易信息提取**: 自动识别和提取交易相关消息
4. **进度查询**: 随时查看当前处理进度

## 🚀 使用方法

### 1. 查看当前进度

```bash
python src/record_de_dialog_progress.py show
```

或者

```bash
python src/import_de_dialog_to_qingniao.py show
```

### 2. 开始录入对话

```bash
python src/import_de_dialog_to_qingniao.py
```

**功能说明**:
- 首次运行：从第一条消息开始处理
- 后续运行：自动从上次处理的位置继续
- 可以手动选择是否从上次位置继续

### 3. 手动设置起始时间

如果需要从特定时间开始处理，可以：

1. 编辑 `src/de_dialog_progress.json`
2. 设置 `last_processed_timestamp` 为你想要的时间戳
3. 运行录入脚本

## 📊 进度文件

**位置**: `src/de_dialog_progress.json`

**内容**:
```json
{
  "last_processed_timestamp": "2025-12-20T00:39:15.261+08:00",
  "last_processed_time": "2025-12-20 00:39:15",
  "total_processed": 150,
  "last_processed_content": "如果价格875-884区间，看空",
  "processing_history": [...]
}
```

## 🔍 查找最新对话的方法

### 方法1: 使用检查脚本

```bash
python src/check_de_last_message_time.py
```

这会显示：
- 第一条消息时间
- 最后一条消息时间
- 最后5条消息内容

### 方法2: 手动查找

1. 打开对话文件: `C:\Users\zuoho\Downloads\discord-msg\梦之队 - 梦梦 - 青沐 [1428778462981918951].html`
2. 查找De.的最新消息
3. 记录时间戳
4. 在进度文件中设置该时间戳

### 方法3: 查看处理历史

运行 `python src/record_de_dialog_progress.py show` 查看最近的处理历史

## 📝 录入内容

系统会自动提取：

1. **交易相关消息**: 包含交易关键词的消息
   - 关键词: 多单、空单、做多、做空、挂单、开、平、止损、止盈等

2. **交易记录**: 包含价格和方向的交易信息

3. **交易规则**: 包含交易系统规则的消息

## ⚙️ 配置

### 对话文件路径

默认路径: `C:\Users\zuoho\Downloads\discord-msg\梦之队 - 梦梦 - 青沐 [1428778462981918951].html`

如需修改，编辑 `src/import_de_dialog_to_qingniao.py` 中的 `DIALOG_FILE` 变量

## 📈 处理报告

每次处理完成后，会生成报告文件：
- 文件名: `De_对话录入报告_YYYYMMDD_HHMMSS.md`
- 包含: 处理统计、交易相关消息、交易记录等

## 🔄 工作流程

1. **首次使用**:
   - 运行 `python src/import_de_dialog_to_qingniao.py`
   - 系统从第一条消息开始处理
   - 处理完成后自动保存进度

2. **后续使用**:
   - 运行 `python src/import_de_dialog_to_qingniao.py`
   - 系统自动从上次停止的地方继续
   - 可以查看进度确认

3. **查看进度**:
   - 运行 `python src/record_de_dialog_progress.py show`
   - 查看最后处理的时间和内容

## 💡 提示

- 系统会自动保存进度，无需手动操作
- 每处理100条消息会自动更新进度（防止中断丢失）
- 处理历史会保留最近20条记录
- 可以随时查看进度，了解处理状态

## 🛠️ 故障排除

### 问题1: 找不到对话文件

**解决**: 检查文件路径是否正确，或修改 `DIALOG_FILE` 变量

### 问题2: 想重新开始处理

**解决**: 删除或清空 `src/de_dialog_progress.json` 文件

### 问题3: 想从特定时间开始

**解决**: 编辑 `src/de_dialog_progress.json`，设置 `last_processed_timestamp`

---

**创建时间**: 2025-12-30  
**系统版本**: 1.0

