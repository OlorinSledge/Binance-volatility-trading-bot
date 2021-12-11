"""
The Snail v 1.2.2
"Buy the dips! ... then wait"
A simple signal that waits for a coin to be X% below its X day high AND below a calculated price (buy_below), then buys it.
Change profit_min to your required potential profit amount
i.e. 20 = 20% potential profit (room for coin to increase by 20%)
profit_max can be used to limit the maximum profit to avoid pump and dumps

Recommended Snail Settings:
Limit = NUmber of days to look back.
Interval = timeframe (leave at 1d)
profit_min, profit_max  as described above

BVT or OLORIN Fork.
If using the Olorin fork (or a variation of it) you must set Olorin to True and BVT to False to change the signal format to work with Olorin.

Windows or Unix / Linux
If NOT using Windows, comment out the following
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
in both places

Recommended config.yml settings
CHANGE_IN_PRICE: 100
STOP_LOSS: 100
TAKE_PROFIT: 2.5 #3.5 if after a large drop in the market
CUSTOM_LIST_AUTORELOAD: False
USE_TRAILING_STOP_LOSS: True
TRAILING_STOP_LOSS: 1 # 1.5 if you want bigger gains
TRAILING_TAKE_PROFIT: .1
Do NOT use pausebotmod as it will prevent the_snail from buying - The Snail buys the dips

Developed by scoobie
Big thank you to @vyacheslav for optimising the code with async and adding list sorting,
and Kevin.Butters for the meticulous testing and reporting

Good luck, but use The Snail LIVE at your own risk - TEST TEST TEST

v1.2 Update
New colour for "The Snail is checking..." to make it easier to spot if you're scrolling through the screen to see last results
Now does not show coins that you already hold
Added variable to change the 'Risk'
- It was previously hardcoded to buy at 70% below the high_price, this is now adjustable.
- e.g. percent_below  0.7 = 70% below high_price, 0.5 = 50% below high_price

v1.2.1
Added MACD filter to further qualify coins before buying
- no way to turn it off (yet).
- checks that 1m, 5m, 15m and 1Day MACD, for each coin in snail list, are all positive - if NOT, it doesnt get added to the signal file.
- also checks BTC on the 1m just to make sure BTC isn't starting a downtrend.

v 1.2.2
Error checking on the MACD

"""

import os
import re
import aiohttp
import asyncio
import time
import json
from datetime import datetime, date
from binance.client import Client
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

USE_MOST_VOLUME_COINS = parsed_config['trading_options']['USE_MOST_VOLUME_COINS']

DISCORD_WEBHOOK = load_discord_creds(parsed_creds)

# Load creds for correct environment
access_key, secret_key = load_correct_creds(parsed_creds)
client = Client(access_key, secret_key)

# If True, an updated list of coins will be generated from the site - http://edgesforledges.com/watchlists/binance.
# If False, then the list you create in TICKERS_LIST = 'tickers.txt' will be used.
CREATE_TICKER_LIST = False

# When creating a ticker list from the source site:
# http://edgesforledges.com you can use the parameter (all or innovation-zone).
# ticker_type = 'innovation-zone'
# ticker_type = 'all'
# if CREATE_TICKER_LIST:
	# TICKERS_LIST = 'tickers_all_USDT.txt'
# else:
	# TICKERS_LIST = 'tickers_all_USDT.txt'
    
if USE_MOST_VOLUME_COINS == True:
    TICKERS_LIST = "volatile_volume_" + str(date.today()) + ".txt"
else:
    TICKERS_LIST = "tickers.txt"
    
BVT = False
#OLORIN = True

if BVT:
	signal_file_type = '.exs'
else:
	signal_file_type = '.buy'

LIMIT = 4
INTERVAL = '1d'

profit_min = 15
profit_max = 100
# change risk level:  0.7 = 70% below high_price, 0.5 = 50% below high_price
percent_below = 0.6
all_info = False


# not available yet
# extra_filter = False


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

def msg_discord(msg):

	message = msg + '\n\n'

	mUrl = "https://discordapp.com/api/webhooks/"+DISCORD_WEBHOOK
	data = {"content": message}
	response = requests.post(mUrl, json=data)


def get_price(client_api):
	initial_price = {}
	tickers = [line.strip() for line in open(TICKERS_LIST)]
	prices = client_api.get_all_tickers()

	for coin in prices:
		for item in tickers:
			if item + PAIR_WITH == coin['symbol'] and all(item + PAIR_WITH not in coin['symbol'] for item in EX_PAIRS):
				initial_price[coin['symbol']] = {'symbol': coin['symbol'],
												 'price': coin['price'],
												 'time': datetime.now(),
												 'price_list': [],
												 'change_price': 0.0,
												 'cov': 0.0}
	return initial_price


async def create_urls(ticker_list, interval, limit) -> dict:
	coins_urls = {}
	for coin in ticker_list:
		if type(coin) == dict:
			if all(item + PAIR_WITH not in coin['symbol'] for item in EX_PAIRS):
				coins_urls[coin['symbol']] = {'symbol': coin['symbol'],
											  'url': f"https://api.binance.com/api/v1/klines?symbol="
													 f"{coin['symbol']}&interval={interval}&limit={limit}"}
		else:
			coins_urls[coin] = {'symbol': coin,
								'url': f"https://api.binance.com/api/v1/klines?symbol={coin}&interval={interval}&limit={limit}"}

	return coins_urls


async def get(session: aiohttp.ClientSession, url) -> dict:
	data = {}
	symbol = re.findall(r'=\w+', url)[0][1:]
	try:
		resp = await session.request('GET', url=url)
		data['symbol'] = symbol
		# data['last_price'] = await get_last_price(session=session, symbol=symbol)
		data['data'] = await resp.json()
	except Exception as e:
		print(e)
	return data


async def get_historical_data(ticker_list, interval, limit):
	urls = await create_urls(ticker_list=ticker_list, interval=interval, limit=limit)
	asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
	async with aiohttp.ClientSession() as session:
		tasks = []
		for url in urls:
			link = urls[url]['url']
			tasks.append(get(session=session, url=link))
		response = await asyncio.gather(*tasks, return_exceptions=True)
		return response


def get_prices_high_low(list_coins, interval, limit):
	asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
	hist_data = asyncio.run(get_historical_data(ticker_list=list_coins,
												interval=interval,
												limit=limit))
	prices_low_high = {}
	for item in hist_data:
		coin_symbol = item['symbol']
		h_p = []
		l_p = []
		for i in item['data']:
			close_time = i[0]
			open_price = float(i[1])
			high_price = float(i[2])
			low_price = float(i[3])
			close_price = float(i[4])
			volume = float(i[5])
			quote_volume = i[6]
			h_p.append(high_price)
			l_p.append(low_price)
		prices_low_high[coin_symbol] = {'symbol': coin_symbol, 'high_price': h_p, 'low_price': l_p,
										'current_potential': 0.0}

	return prices_low_high


def do_work():

	while True:
		init_price = get_price(client)
		coins = get_prices_high_low(init_price, INTERVAL, LIMIT)
		print(f'{TextColors.TURQUOISE}The Snail is checking for potential profit and buy signals{TextColors.DEFAULT}')
		if os.path.exists(f'signals/snail_scan{signal_file_type}'):
			os.remove(f'signals/snail_scan{signal_file_type}')

		current_potential_list = []
		held_coins_list = {}

		if TEST_MODE:
			coin_path = 'test_coins_bought.json'
		elif BVT:
			coin_path = 'coins_bought.json'
		else:
			coin_path = 'live_coins_bought.json'
		if os.path.isfile(coin_path) and os.stat(coin_path).st_size != 0:
			with open(coin_path) as file:
				held_coins_list = json.load(file)

		for coin in coins:
			if len(coins[coin]['high_price']) == LIMIT:
				high_price = float(max(coins[coin]['high_price']))
				low_price = float(min(coins[coin]['low_price']))
				last_price = float(init_price[coin]['price'])

				# Calculation
				diapason = high_price - low_price
				potential = (low_price / high_price) * 100
				buy_above = low_price * 1.00
				buy_below = high_price - (diapason * percent_below)  # percent below affects Risk
				max_potential = potential * 0.98
				min_potential = potential * 0.6
				safe_potential = potential - 12
				current_range = high_price - last_price
				current_potential = ((high_price / last_price) * 100) - 100
				coins[coin]['current_potential'] = current_potential

				if profit_min < current_potential < profit_max and last_price < buy_below and coin not in held_coins_list:
					current_potential_list.append(coins[coin])
					# print(f'{TextColors.TURQUOISE}{coin}{TextColors.DEFAULT} Potential profit: {TextColors.TURQUOISE}{current_potential:.0f}%{TextColors.DEFAULT}\n')

		if current_potential_list:
			#print(current_potential_list)
			exchange = ccxt.binance()
			macd_list = []
			macdbtc = exchange.fetch_ohlcv('BTCUSDT', timeframe='1m', limit=36)
			for i in current_potential_list:
				coin = i['symbol']
				current_potential = i['current_potential']
				try:
					macd1 = exchange.fetch_ohlcv(coin, timeframe='1m', limit=36)
					macd5 = exchange.fetch_ohlcv(coin, timeframe='5m', limit=36)
					macd15 = exchange.fetch_ohlcv(coin, timeframe='15m', limit=36)
					macd1day = exchange.fetch_ohlcv(coin, timeframe='1d', limit=36)
				except Exception as e:
					print(f'{coin} Exception {e}')
					continue


				df1 = pd.DataFrame(macd1, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
				df5 = pd.DataFrame(macd5, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
				df15 = pd.DataFrame(macd15, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
				df1day = pd.DataFrame(macd1day, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
				dfbtc = pd.DataFrame(macdbtc, columns=['time', 'open', 'high', 'low', 'close', 'volume'])

				macd1 = df1.ta.macd(fast=12, slow=26)
				macd5 = df5.ta.macd(fast=12, slow=26)
				macd15 = df15.ta.macd(fast=12, slow=26)
				try:
					macd1day = df1day.ta.macd(fast=12, slow=26)
				except Exception as e:
					print(f'{coin} Exception {e}')
					continue
				macdbtc = dfbtc.ta.macd(fast=12, slow=26)


				get_hist1 = macd1.iloc[35, 1]
				get_hist5 = macd5.iloc[35, 1]
				get_hist15 = macd15.iloc[35, 1]
				try:
					get_hist1day = macd1day.iloc[35, 1]
				except Exception as e:
					print(f'{coin} Exception {e}')
					continue
				get_histbtc = macdbtc.iloc[35, 1]

				#print(f'MACD HIST {coin} {get_hist1} {get_hist5} {get_hist15} {get_hist1day} {get_histbtc}')

				if get_hist1 >= 0 and get_hist5 >= 0 and get_hist15 >= 0 and get_hist1day >= 0 and get_histbtc >= 0:
					# Add to coins for Snail to scan
					print(f'{TextColors.TURQUOISE}{coin}{TextColors.DEFAULT} Potential profit: {TextColors.TURQUOISE}{current_potential:.0f}%{TextColors.DEFAULT}\n')
					macd_list.append(coins[coin])
				# else:
				#     print(f'Do NOT buy {coin}')

			if macd_list:
				#print(macd_list)
				sort_list = sorted(macd_list, key=lambda x: x[f'current_potential'], reverse=True)
				for i in sort_list:
					coin = i['symbol']
					current_potential = i['current_potential']
					last_price = float(init_price[coin]['price'])
					# print(f'list {coin} {last_price}')
					high_price = float(max(coins[coin]['high_price']))
					# print(f'list {coin} {high_price}')
					low_price = float(min(coins[coin]['low_price']))
					# print(f'list {coin} {low_price}')
					diapason = high_price - low_price
					potential = (low_price / high_price) * 100
					buy_above = low_price * 1.00
					buy_below = high_price - (diapason * percent_below)
					current_range = high_price - last_price

					if all_info:
						print(f'\nPrice:            ${last_price:.3f}\n'
							  f'High:             ${high_price:.3f}\n'
							  # f'Plan: TP {TP}% TTP {TTP}%\n'
							  f'Day Max Range:    ${diapason:.3f}\n'
							  f'Current Range:    ${current_range:.3f} \n'
							  # f'Daily Range:      ${diapason:.3f}\n'
							  # f'Current Range     ${current_range:.3f} \n'
							  # f'Potential profit before safety: {potential:.0f}%\n'
							  # f'Buy above:        ${buy_above:.3f}\n'
							  f'Buy Below:        ${buy_below:.3f}\n'
							  f'Potential profit: {TextColors.TURQUOISE}{current_potential:.0f}%{TextColors.DEFAULT}'
							  # f'Max Profit {max_potential:.2f}%\n'
							  # f'Min Profit {min_potential:.2f}%\n'
							  )
					# print(f'Adding {TextColors.TURQUOISE}{coin}{TextColors.DEFAULT} to buy list')

					# add to signal
					with open(f'signals/snail_scan{signal_file_type}', 'a+') as f:
						f.write(str(coin) + '\n')

			# else:
			# print(f'{TextColors.TURQUOISE}{coin}{TextColors.DEFAULT} may not be profitable at this time')
			snail_coins = len(current_potential_list)
			macd_coins = len(macd_list)
			snail_discord = f'Snail found {snail_coins} coins and MACD approved {macd_coins}'
			msg_discord(snail_discord)
			print(f'{TextColors.TURQUOISE}Snail found {snail_coins} coins and MACD approved {macd_coins} coins. L: {LIMIT}days Min: {profit_min}% Risk: {percent_below * 100}% {TextColors.DEFAULT}')
			time.sleep(180)
