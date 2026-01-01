# X (Twitter) 推文下载工具使用指南

## 当前可用工具推荐

由于 `snscrape` 已失效，以下是目前最实用的替代方案：

### 方案1: twscrape（推荐，需要账号）

**优点：**
- 功能强大，支持多种操作
- 可以下载大量历史推文
- 支持搜索、用户推文等

**安装：**
```bash
pip install twscrape
```

**使用前准备：**
```bash
# 添加账号（需要Twitter账号和密码）
twscrape add_accounts accounts.txt username:password:email:email_password

# 或使用cookie登录（更推荐，更安全）
# 需要从浏览器获取cookie
```

**使用示例：**
```python
from src.ml_dl.twitter_downloader import TwitterDownloader

downloader = TwitterDownloader()
tweets = downloader.download_user_tweets('elonmusk', limit=100)
downloader.save_tweets(tweets)
```

### 方案2: 蓝鸟猎手（桌面工具，最简单）

**优点：**
- 图形界面，操作简单
- 无需编程
- 支持批量下载

**下载地址：**
- https://bh.keli.moe/download

**使用：**
1. 下载并安装
2. 输入用户名或推文链接
3. 选择下载选项
4. 开始下载

### 方案3: X-Spider（桌面工具）

**优点：**
- 支持图片和视频下载
- 支持日期范围筛选
- 支持Cookie登录

**下载地址：**
- https://www.ghxi.com/xspider.html

### 方案4: 浏览器扩展（最简单，适合少量下载）

**X媒体下载器：**
- Chrome扩展：https://chromewebstore.google.com/detail/x-%E5%AA%92%E4%BD%93%E4%B8%8B%E8%BD%BD%E5%99%A8-twitter-%E5%9B%BE%E7%89%87%E5%92%8C%E8%A7%86%E9%A2%91%E4%B8%8B%E8%BD%BD%E5%99%A8/akhckkpbjonlaacapohphmdfoikibkbg

**使用：**
1. 安装扩展
2. 访问X网站
3. 在推文下方点击下载按钮

### 方案5: 官方数据导出（最安全，但只能下载自己的）

**步骤：**
1. 登录X
2. 设置 → 账户 → 您的X数据
3. 请求数据下载
4. 等待邮件通知
5. 下载ZIP文件

## 推荐选择

- **需要批量下载大量推文** → 使用 **twscrape**（需要账号）
- **偶尔下载，不想编程** → 使用 **蓝鸟猎手** 或 **X-Spider**
- **只下载自己的推文** → 使用 **官方数据导出**
- **只下载少量媒体** → 使用 **浏览器扩展**

## 注意事项

1. 遵守X的使用条款
2. 不要用于商业用途（除非有授权）
3. 注意版权问题
4. 某些工具可能需要登录，注意账号安全

## 当前工具脚本

已创建 `twitter_downloader.py`，支持多种方法自动切换。

**快速开始：**
```bash
# 安装依赖
pip install twscrape

# 使用工具
python src/ml_dl/twitter_downloader.py elonmusk 100
```



