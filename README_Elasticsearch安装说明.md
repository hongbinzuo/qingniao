# Elasticsearch安装和启动说明

## 🚀 快速开始

### 方式1：使用Docker（推荐）

#### 步骤1：安装Docker Desktop

1. 下载Docker Desktop for Windows：
   - 访问：https://www.docker.com/products/docker-desktop
   - 下载并安装

2. 启动Docker Desktop

#### 步骤2：运行安装脚本

```powershell
# 以管理员身份运行PowerShell
.\scripts\install_elasticsearch.ps1
```

或者手动运行：

```powershell
docker run -d `
    --name elasticsearch `
    -p 9200:9200 `
    -p 9300:9300 `
    -e "discovery.type=single-node" `
    -e "xpack.security.enabled=false" `
    -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" `
    elasticsearch:8.11.0
```

#### 步骤3：测试连接

```powershell
curl http://localhost:9200
```

或访问浏览器：http://localhost:9200

### 方式2：Windows直接安装（如果没有Docker）

1. 下载Elasticsearch：
   - 访问：https://www.elastic.co/downloads/elasticsearch
   - 下载Windows版本（ZIP）

2. 解压并运行：
   ```powershell
   cd elasticsearch-8.11.0\bin
   .\elasticsearch.bat
   ```

## 📋 常用命令

### 启动Elasticsearch

```powershell
.\scripts\start_elasticsearch.ps1
```

或手动：
```powershell
docker start elasticsearch
```

### 停止Elasticsearch

```powershell
.\scripts\stop_elasticsearch.ps1
```

或手动：
```powershell
docker stop elasticsearch
```

### 查看日志

```powershell
docker logs elasticsearch
```

### 查看状态

```powershell
docker ps | findstr elasticsearch
```

## ✅ 验证安装

### 1. 测试连接

```powershell
curl http://localhost:9200
```

应该返回：
```json
{
  "name": "...",
  "cluster_name": "docker-cluster",
  "cluster_uuid": "...",
  "version": {
    "number": "8.11.0",
    ...
  }
}
```

### 2. 测试Python客户端

```powershell
python -c "from elasticsearch import Elasticsearch; es = Elasticsearch(['localhost:9200']); print('✓ 连接成功' if es.ping() else '❌ 连接失败')"
```

### 3. 运行测试脚本

```powershell
python src/elasticsearch_logger.py
```

## 🔧 配置

配置文件：`config/elasticsearch_config.json`

```json
{
  "hosts": ["localhost:9200"],
  "index_prefix": "qingniao_conversations",
  "retention_days": 90
}
```

## ⚠️ 注意事项

1. **内存要求**：Elasticsearch需要至少512MB内存
2. **端口占用**：确保9200和9300端口未被占用
3. **防火墙**：确保防火墙允许访问9200端口
4. **Docker Desktop**：如果使用Docker，确保Docker Desktop正在运行

## 🐛 故障排除

### 问题1：Docker未安装

**解决**：安装Docker Desktop
- 下载：https://www.docker.com/products/docker-desktop

### 问题2：端口被占用

**解决**：
```powershell
# 查看占用9200端口的进程
netstat -ano | findstr :9200

# 停止进程或修改端口
```

### 问题3：内存不足

**解决**：调整内存设置
```powershell
docker run -d `
    --name elasticsearch `
    -p 9200:9200 `
    -e "discovery.type=single-node" `
    -e "xpack.security.enabled=false" `
    -e "ES_JAVA_OPTS=-Xms256m -Xmx256m" `
    elasticsearch:8.11.0
```

### 问题4：连接失败

**解决**：
1. 检查容器是否运行：`docker ps`
2. 查看日志：`docker logs elasticsearch`
3. 等待更长时间（Elasticsearch启动需要时间）

## 📝 下一步

安装完成后：

1. 安装Python客户端：
   ```powershell
   pip install elasticsearch
   ```

2. 测试连接：
   ```powershell
   python src/elasticsearch_logger.py
   ```

3. 开始使用日志系统！



