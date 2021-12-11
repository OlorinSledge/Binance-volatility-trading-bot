"""
The Snail v 2.1
"Buy the dips! ... then wait"

STRATEGY
1. Selects coins that are X% (percent_below) below their X day (LIMIT) maximum
2. ** NEW ** Finds movement (MOVEMENT) range over X Days
  - if MOVEMENT* > TAKE_PROFIT coins pass to 3
3. Check coins are not already owned
4. Uses MACD to check if coins are currently on an uptrend
5. Adds coins that pass all above tests to Signal file for the Bot to buy (ordered by Potential Profit from High to Low)

* MOVEMENT
  Looks at the fluctuation in price over LIMIT days and compares to your TAKE_PROFIT settings.
  i.e. if your TAKE_PROFIT is 3%, but the movement is only 1%, then you wont hit TP and will be left holding the coin
  This can be turned off if you want.

* ATR MOVEMENT
calculates Average True Range Percent (ATRP) as an alternative to the default movement

STRATEGY SETTINGS
LIMIT = 4
INTERVAL = '1d'
profit_min = 15
profit_max = 100  # only required if you want to limit max profit
percent_below = 0.6  # change risk level:  0.7 = 70% below high_price, 0.5 = 50% below high_price
MOVEMENT = True #

OTHER SETTINGS
BVT or OLORIN Fork.
Set True / False for compatibility

WINDOWS (WINDOWS OS)
Set True / False for compatibility

DISCORD
send message to Discord - Set True / False


CONFIG.YML SETTINGS
CHANGE_IN_PRICE: 100 REQUIRED
Do NOT use pausebotmod as it will prevent the_snail from buying - The Snail buys the dips

Developed by scoobie
Thanks to
@vyacheslav for optimising the code with async and adding list sorting,
@Kevin.Butters for the meticulous testing and reporting,
@OlorinSledge for the coding advice and a great fork

DISCLAIMER
CHECK YOU HAVE ALL THE REQUIRED IMPORTS INSTALLED
Developed for OlorinSledge fork - no support for any others as I don't use them.
Troubleshooting and help - please use the #troubleshooting channel
Settings - the settings in this file are what I currently use, please don't DM me for the 'best' settings - for me, these are the best so far.
There's a lot of options to adjust the strategy, test them out and share your results in #bot-strategies so others can learn from them too

Hope the Snail makes you rich!

"""

import os
import re
import aiohttp
import asyncio
import time
import json
from datetime import datetime
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
EX_PAIRS = parsed_config['trading_options']['FIATS']
TEST_MODE = parsed_config['script_options']['TEST_MODE']
TAKE_PROFIT = parsed_config['trading_options']['TAKE_PROFIT']
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

# send message to discord
DISCORD = False

# Strategy Settings
LIMIT = 4
INTERVAL = '1d'
profit_min = 15
profit_max = 100  # only required if you want to limit max profit
percent_below = 0.6  # change risk level:  0.7 = 70% below high_price, 0.5 = 50% below high_price
# movement can be either:
#  "MOVEMENT" for original movement calc
#  "ATR_MOVEMENT" for Average True Range Percentage calc
MOVEMENT = 'MOVEMENT'

# Display Setttings
all_info = True
block_info = False


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
	if os.name == 'nt':
        	# only need this line for Windows based systems
		asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
	async with aiohttp.ClientSession() as session:
		tasks = []
		for url in urls:
			link = urls[url]['url']
			tasks.append(get(session=session, url=link))
		response = await asyncio.gather(*tasks, return_exceptions=True)
		return response


def get_prices_high_low(list_coins, interval, limit):
	if os.name == 'nt':
	        # only need this line for Windows based systems
		asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
	hist_data = asyncio.run(get_historical_data(ticker_list=list_coins, interval=interval, limit=limit))
	prices_low_high = {}
	for item in hist_data:
		coin_symbol = item['symbol']
		h_p = []
		l_p = []
		atr = [] # average true range
		try:
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
				atr.append(high_price-low_price)
			prices_low_high[coin_symbol] = {'symbol': coin_symbol, 'high_price': h_p, 'low_price': l_p, 'current_potential': 0.0, 
											'atr_percentage': ((sum(atr)/len(atr)) / close_price) * 100}
		except Exception as e:
			print(f'Ignoring {coin_symbol} data issue')
			continue
	return prices_low_high


def do_work():
	while True:
		try:
			init_price = get_price(client)
			coins = get_prices_high_low(init_price, INTERVAL, LIMIT)
			print(f'{TextColors.TURQUOISE}The Snail is checking for potential profit and buy signals{TextColors.DEFAULT}')
			if os.path.exists(f'signals/snail_scan{signal_file_type}'):
				os.remove(f'signals/snail_scan{signal_file_type}')

			current_potential_list = []
			held_coins_list = {}

			if TEST_MODE:
				coin_path = 'test_coins_bought.json'
			else:
				if BVT:
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
					range = high_price - low_price
					potential = (low_price / high_price) * 100
					buy_above = low_price * 1.00
					buy_below = high_price - (range * percent_below)  # percent below affects Risk
					max_potential = potential * 0.98
					min_potential = potential * 0.6
					safe_potential = potential - 12
					current_range = high_price - last_price
					current_potential = ((high_price / last_price) * 100) - 100
					coins[coin]['current_potential'] = current_potential
					movement = (low_price / range)
					print(f'{coin} {current_potential:.2f}% M:{movement:.2f}% ATRP:{coins[coin]["atr_percentage"]:.2f}%')

					if MOVEMENT == "MOVEMENT":
						if profit_min < current_potential < profit_max and last_price < buy_below and movement >= (TAKE_PROFIT + 0.2) and coin not in held_coins_list:
							current_potential_list.append(coins[coin])
					elif MOVEMENT ==  "ATR_MOVEMENT":
						if profit_min < current_potential < profit_max and last_price < buy_below and coins[coin]["atr_percentage"] >= (TAKE_PROFIT) and coin not in held_coins_list:
							current_potential_list.append(coins[coin])						
					else:
						if profit_min < current_potential < profit_max and last_price < buy_below and coin not in held_coins_list:
							current_potential_list.append(coins[coin])

					if block_info:
						print(f'\nPrice:            ${last_price:.3f}\n'
							f'High:             ${high_price:.3f}\n'
							f'Low:              ${low_price:.3f}\n'
							# f'Plan: TP {TP}% TTP {TTP}%\n'
							f'Day Max Range:    ${range:.3f}\n'
							f'Current Range:    ${current_range:.3f} \n'
							# f'Daily Range:      ${range:.3f}\n'
							# f'Current Range     ${current_range:.3f} \n' 
							# f'Potential profit before safety: {potential:.0f}%\n'
							f'Buy above:        ${buy_above:.3f}\n'
							f'Buy Below:        ${buy_below:.3f}\n'
							f'Potential profit: {TextColors.TURQUOISE}{current_potential:.0f}%{TextColors.DEFAULT}'
							# f'Max Profit {max_potential:.2f}%\n'
							# f'Min Profit {min_potential:.2f}%\n'
						)

			if current_potential_list:
				# print(current_potential_list)
				exchange = ccxt.binance()
				macd_list = []

				for i in current_potential_list:
					coin = i['symbol']
					current_potential = i['current_potential']
					macd1 = exchange.fetch_ohlcv(coin, timeframe='1m', limit=36)
					macd5 = exchange.fetch_ohlcv(coin, timeframe='5m', limit=36)
					macd15 = exchange.fetch_ohlcv(coin, timeframe='15m', limit=36)
					macd4h = exchange.fetch_ohlcv(coin, timeframe='15m', limit=36)
					try:
						macd1day = exchange.fetch_ohlcv(coin, timeframe='1d', limit=36)
					except Exception as e:
						print(f'{coin} Exception {e}')
						continue
					macdbtc = exchange.fetch_ohlcv('BTCUSDT', timeframe='1m', limit=36)

					df1 = pd.DataFrame(macd1, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
					df5 = pd.DataFrame(macd5, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
					df15 = pd.DataFrame(macd15, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
					df4h = pd.DataFrame(macd4h, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
					df1day = pd.DataFrame(macd1day, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
					dfbtc = pd.DataFrame(macdbtc, columns=['time', 'open', 'high', 'low', 'close', 'volume'])


					macd1 = df1.ta.macd(fast=12, slow=26)
					macd5 = df5.ta.macd(fast=12, slow=26)
					macd15 = df15.ta.macd(fast=12, slow=26)
					macd1day = df1day.ta.macd(fast=12, slow=26)
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


					if all_info:
						if get_hist1 >= 0 and get_hist5 >= 0 and get_hist15 >= 0 and get_hist1day >= 0 and get_histbtc >= 0:
							print(f'MACD HIST {coin} {current_potential:.0f}% {TextColors.SELL_PROFIT}{get_hist1:.4f} {get_hist5:.4f} {get_hist15:.4f} {get_hist1day:.4f} {get_histbtc:.4f} ')
						else:
							print(f'MACD HIST {coin} {current_potential:.0f}% {get_hist1:.4f} {get_hist5:.4f} {get_hist15:.4f} {get_hist1day:.4f} {get_histbtc:.4f}')

					if get_hist1 >= 0 and get_hist5 >= 0 and get_hist15 >= 0 and get_hist1day >= 0 and get_histbtc >= 0:
						# Add to coins for Snail to scan
						print(f'{TextColors.TURQUOISE}{coin}{TextColors.DEFAULT} Potential profit: {TextColors.TURQUOISE}{current_potential:.0f}%{TextColors.DEFAULT}\n')
						macd_list.append(coins[coin])
					# else:
					#     print(f'Do NOT buy {coin}')

				if macd_list:

					# print(macd_list)
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
						range = high_price - low_price
						potential = (low_price / high_price) * 100
						buy_above = low_price * 1.00
						buy_below = high_price - (range * percent_below)
						current_range = high_price - last_price

						if all_info:
							print(f'\nPrice:            ${last_price:.3f}\n'
								  f'High:             ${high_price:.3f}\n'
								  # f'Plan: TP {TP}% TTP {TTP}%\n'
								  f'Day Max Range:    ${range:.3f}\n'
								  f'Current Range:    ${current_range:.3f} \n'
								  # f'Daily Range:      ${range:.3f}\n'
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
				if DISCORD:
					msg_discord(snail_discord)
				print(f'{TextColors.TURQUOISE}Snail found {snail_coins} coins and MACD approved {macd_coins} coins. L: {LIMIT}days Min: {profit_min}% Risk: {percent_below * 100}% {TextColors.DEFAULT}')
			time.sleep(180)
		except Exception as e:
			print(f'The Snail: Exception do_work() 1: {e}')
			time.sleep(60)
			continue
		except KeyboardInterrupt as ki:
			continue

if __name__ == '__main__':
	# Testing 
	do_work()