# Elasticsearch快速启动指南

## ✅ 已完成

1. ✅ **Python客户端已安装**：`pip install elasticsearch`
2. ✅ **Elasticsearch已下载**：`elasticsearch-8.11.0` 目录
3. ✅ **代码已修复**：修复了API兼容性问题
4. ✅ **启动脚本已创建**

## 🚀 启动Elasticsearch

### 方式1：使用快速启动脚本（推荐）

**双击运行**：`启动Elasticsearch.bat`

或在命令行运行：
```cmd
启动Elasticsearch.bat
```

### 方式2：手动启动

```cmd
cd elasticsearch-8.11.0\bin
elasticsearch.bat
```

**注意**：请保持Elasticsearch窗口打开，不要关闭！

### 方式3：使用Docker（如果已安装Docker Desktop）

```cmd
docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 -e "discovery.type=single-node" -e "xpack.security.enabled=false" -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" elasticsearch:8.11.0
```

## ✅ 验证安装

### 1. 检查Elasticsearch是否运行

访问浏览器：http://localhost:9200

应该看到类似这样的JSON响应：
```json
{
  "name": "...",
  "cluster_name": "docker-cluster",
  "version": {
    "number": "8.11.0"
  }
}
```

### 2. 使用Python测试

```python
python -c "from elasticsearch import Elasticsearch; es = Elasticsearch(['http://localhost:9200']); print('✓ 连接成功' if es.ping() else '❌ 连接失败')"
```

### 3. 测试日志系统

```python
python src/elasticsearch_logger.py
```

## 📝 配置

配置文件：`config/elasticsearch_config.json`

```json
{
  "hosts": ["localhost:9200"],
  "index_prefix": "qingniao_conversations",
  "retention_days": 90
}
```

## ⚠️ 注意事项

1. **保持窗口打开**：Elasticsearch需要在后台运行，不要关闭窗口
2. **启动时间**：Elasticsearch启动需要30-60秒
3. **端口占用**：确保9200端口未被占用
4. **内存要求**：Elasticsearch需要至少512MB内存

## 🔧 故障排除

### 问题1：连接失败

**解决**：
1. 确保Elasticsearch窗口已打开
2. 等待更长时间（30-60秒）
3. 检查是否有错误信息
4. 访问 http://localhost:9200 查看状态

### 问题2：端口被占用

**解决**：
```cmd
netstat -ano | findstr :9200
```

### 问题3：内存不足

**解决**：编辑 `elasticsearch-8.11.0\config\jvm.options`，减少内存设置

## 🎯 下一步

启动Elasticsearch后：

1. ✅ 测试连接：`python src/elasticsearch_logger.py`
2. ✅ 开始使用日志系统
3. ✅ 所有对话和操作都会被记录

## 📌 快速命令

```cmd
# 启动
启动Elasticsearch.bat

# 测试
python src/elasticsearch_logger.py

# 停止（关闭Elasticsearch窗口即可）
```


