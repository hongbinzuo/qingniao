import requests
r=requests.get('https://api.gateio.ws/api/v4/spot/tickers?currency_pair=BTC_USDT',timeout=12)
print('net ok', r.status_code)
