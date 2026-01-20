#!/usr/bin/env python3
"""Check stock data age in Redis"""
import redis
import os
from datetime import datetime

r = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'localhost'),
    port=int(os.environ.get('REDIS_PORT', 10000)),
    password=os.environ.get('REDIS_PASSWORD', ''),
    ssl=os.environ.get('REDIS_SSL', 'true').lower() == 'true',
    decode_responses=True
)

# Check MSFT and AAPL latest price and timestamp
print("=== Aktuellste Kurse ===")
for ticker in ['MSFT', 'AAPL', 'GOOGL']:
    key = f'stock:{ticker}:Close'
    try:
        result = r.execute_command('TS.GET', key)
        if result:
            ts, val = result
            dt = datetime.fromtimestamp(ts/1000)
            age_days = (datetime.now() - dt).days
            print(f'{ticker}: ${val:.2f} vom {dt.strftime("%Y-%m-%d")} ({age_days} Tage alt)')
    except Exception as e:
        print(f'{ticker}: Fehler - {e}')

# Check date range for MSFT
print("\n=== MSFT TimeSeries Details ===")
key = 'stock:MSFT:Close'
try:
    info = r.execute_command('TS.INFO', key)
    info_dict = dict(zip(info[::2], info[1::2]))
    first_ts = info_dict.get('firstTimestamp', 0)
    last_ts = info_dict.get('lastTimestamp', 0)
    total = info_dict.get('totalSamples', 0)
    print(f'Datenpunkte: {total}')
    print(f'Erster: {datetime.fromtimestamp(first_ts/1000).strftime("%Y-%m-%d")}')
    print(f'Letzter: {datetime.fromtimestamp(last_ts/1000).strftime("%Y-%m-%d")}')
except Exception as e:
    print(f'Fehler: {e}')
