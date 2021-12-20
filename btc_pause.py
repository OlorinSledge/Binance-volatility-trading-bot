"""
BTC Pause
Prevents buying when BTC is heading down.
Uses ma2, ma3, ma4, ma5, ma10, ma20

Add to Config as signal

Changes required to Bot Code:
def pause_bot()
while os.path.exists("signals/btc_pause.pause")

Helping you out?
Buy me a Beer ;)

nano.to/dano
(fast and feeless)
algo: 7S7UIKHMAO6WVA3VENMGZWPDHVG6FSKVVUYBZNGWNZXMDZSRDHXT43JOKM
(almost as fast, almost as feeless)





"""

import os
import re
import aiohttp
import asyncio
import time
import json
import time as t
from datetime import datetime 

from binance.client import Client, BinanceAPIException
from helpers.parameters import parse_args, load_config
import pandas as pd
import pandas_ta as ta
import ccxt
import requests


# Load creds modules
from helpers.handle_creds import (
	load_correct_creds, load_discord_creds
)

# Settings
SIGNAL_NAME = 'btc_pause'
args = parse_args()
DEFAULT_CONFIG_FILE = 'config.yml'
DEFAULT_CREDS_FILE = 'creds.yml'

config_file = args.config if args.config else DEFAULT_CONFIG_FILE
creds_file = args.creds if args.creds else DEFAULT_CREDS_FILE
parsed_creds = load_config(creds_file)
parsed_config = load_config(config_file)

# Load trading vars
PAIR_WITH = parsed_config['trading_options']['PAIR_WITH']
EX_PAIRS = parsed_config['trading_options']['EX_PAIRS']
TEST_MODE = parsed_config['script_options']['TEST_MODE']
TAKE_PROFIT = parsed_config['trading_options']['TAKE_PROFIT']
DISCORD_WEBHOOK = load_discord_creds(parsed_creds)

# Load creds for correct environment
access_key, secret_key = load_correct_creds(parsed_creds)
client = Client(access_key, secret_key)


CREATE_TICKER_LIST = True
ticker_type = 'all'
if CREATE_TICKER_LIST:
	TICKERS_LIST = 'tickers_all_USDT.txt'
else:
	TICKERS_LIST = 'tickers.txt'

# System Settings
BVT = False
OLORIN = True  # if not using Olorin Sledge Fork set to False
if OLORIN:
	signal_file_type = '.buy'
else:
	signal_file_type = '.exs'

# if using Windows OS set to True, else set to False
WINDOWS = True

# send message to discord
DISCORD = True

# Strategy Settings

LIMIT = 6
INTERVAL = '1m'
percent = 1

websocket_server_url = 'https://api.binance.com/api/v1/'
timestamp_log = datetime.now().strftime("%y-%m-%d %H:%M:%S")
SIGNAL_NAME = 'btc_pause'
SIGNAL_TYPE = 'pause'

class TextColors:
	BUY = '\033[92m'
	WARNING = '\033[93m'
	SELL_LOSS = '\033[91m'
	SELL_PROFIT = '\033[32m'
	DIM = '\033[2m\033[35m'
	DEFAULT = '\033[39m'
	YELLOW = '\033[33m'
	TURQUOISE = '\033[36m'
	UNDERLINE = '\033[4m'
	END = '\033[0m'
	ITALICS = '\033[3m'
	TCR = '\033[91m'
	TCG = '\033[32m'
	TCD = '\033[39m'

def msg_discord(msg):

	message = msg + '\n\n'

	mUrl = "https://discordapp.com/api/webhooks/"+DISCORD_WEBHOOK
	data = {"content": message}
	response = requests.post(mUrl, json=data)

def analyse_btc():

	# Normal Scan for LIMIT and INTERVAL
	exchange = ccxt.binance()
	try:
		btc = exchange.fetch_ohlcv("BTCUSDT", timeframe='1m', limit=25)
		btc = pd.DataFrame(btc, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
		btc['VWAP'] = ((((btc.high + btc.low + btc.close) / 3) * btc.volume) / btc.volume)
		#print(btc)
	except BinanceAPIException as e:
		print('CCXT Error')
		print(e.status_code)
		print(e.message)
		print(e.code)

	btc2 = btc.ta.sma(length=2)
	btc3 = btc.ta.sma(length=3)
	btc4 = btc.ta.sma(length=4)
	btc5 = btc.ta.sma(length=5)
	btc10 = btc.ta.sma(length=10)
	btc20 = btc.ta.sma(length=20)

	btc2 = btc2.iloc[-1]
	btc3 = btc3.iloc[-1]
	btc4 = btc4.iloc[-1]
	btc5 = btc5.iloc[-1]
	btc10 = btc10.iloc[-1]
	btc20 = btc20.iloc[-1]
	print(f"{btc2:.2f} {btc3:.2f} {btc4:.2f} {btc5:.2f} {btc10:.2f} {btc20:.2f}")

	paused = False

	now = datetime.now()

	if 0 <= now.weekday() <= 4:
                if btc2 > btc3 > btc4 > btc5 > btc10 > btc20:
                    paused = False
                    print(f'{SIGNAL_NAME}: Market looks OK')
                else:
                    print(f'{SIGNAL_NAME}: Market not looking good')
                    paused = True
		#if (time(9) <= now.time() <= time(15,30)) or (time(18) <= now.time() <= time(21)) or (time(22) <= now.time() <= time(7)):
		#else:
		#print (f'Outside the range  - {now}')
		#paused = False
	else:
		print (f'its a weekend - {now}')
		paused = True

	return paused

def do_work():
	while True:
		paused = analyse_btc()
		if paused:
			with open(f'signals/{SIGNAL_NAME}.{SIGNAL_TYPE}', 'a+') as f:
				f.write('yes')
			print(f"paused by BTC")

		else:
			if os.path.isfile(f'signals/{SIGNAL_NAME}.{SIGNAL_TYPE}'):
				os.remove(f'signals/{SIGNAL_NAME}.{SIGNAL_TYPE}')
			print(f"Running")
		t.sleep(30)





