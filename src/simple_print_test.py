import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

print("测试输出", flush=True)
print("如果看到这行，说明输出正常", flush=True)

import requests
print("requests模块已导入", flush=True)

url = "https://api.gateio.ws/api/v4/spot/tickers"
print("开始请求API...", flush=True)
response = requests.get(url, timeout=10)
print(f"响应状态码: {response.status_code}", flush=True)

if response.status_code == 200:
    data = response.json()
    print(f"获取到 {len(data)} 个ticker", flush=True)
else:
    print("API请求失败", flush=True)


