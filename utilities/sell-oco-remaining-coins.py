import sys
sys.path.append('..')

import json
import os
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from binance.helpers import round_step_size
from datetime import datetime

# Load helper modules
from helpers.parameters import (
    parse_args, load_config
)

# Load creds modules
from helpers.handle_creds import (
    load_correct_creds
)

from colorama import init
init()

# for colourful logging to the console
class txcolors:
    BUY = '\033[92m'
    WARNING = '\033[93m'
    SELL_LOSS = '\033[91m'
    SELL_PROFIT = '\033[32m'
    DIM = '\033[2m\033[35m'
    DEFAULT = '\033[39m'


args = parse_args()

DEFAULT_CONFIG_FILE = '../config.yml'
DEFAULT_CREDS_FILE = '../creds.yml'

config_file = args.config if args.config else DEFAULT_CONFIG_FILE
creds_file = args.creds if args.creds else DEFAULT_CREDS_FILE
parsed_creds = load_config(creds_file)
parsed_config = load_config(config_file)

PAIR_WITH = parsed_config['trading_options']['PAIR_WITH']
TEST_MODE = parsed_config['script_options'].get('TEST_MODE')
prefix = 'live_'
if TEST_MODE:
    prefix = 'test_'

coins_bought_file_path = '../' + prefix + 'coins_bought.json'
LOG_TRADES = parsed_config['script_options'].get('LOG_TRADES')
LOG_FILE = parsed_config['script_options'].get('LOG_FILE')
LOG_FILE_PATH = '../' + prefix + LOG_FILE

# if saved coins_bought json file exists and it's not empty then load it
coins_bought = {}
if os.path.isfile(coins_bought_file_path) and os.stat(coins_bought_file_path).st_size!= 0:
    with open(coins_bought_file_path) as file:
            coins_bought = json.load(file)

access_key, secret_key = load_correct_creds(parsed_creds)

if not TEST_MODE:
    client = Client(access_key, secret_key)
else:
    client = Client(access_key, secret_key,testnet=True)

def write_log(logline):
    timestamp = datetime.now().strftime("%d/%m %H:%M:%S")
    with open(LOG_FILE_PATH,'a+') as f:
        f.write(timestamp + ' ' + logline + '\n')

def remove_from_portfolio(coins_sold):
    '''Remove coins sold due to OCO from portfolio'''
    coins_bought.pop(coins_sold)
    with open(coins_bought_file_path, 'w') as file:
        json.dump(coins_bought, file, indent=4)
    if os.path.exists('signalsell_tickers.txt'):
        os.remove('signalsell_tickers.txt')
        for coin in coins_bought:
            #write_signallsell(coin.removesuffix(PAIR_WITH))
            write_signallsell(rchop(coin, PAIR_WITH))
    
with open(coins_bought_file_path, 'r') as f:
    coins = json.load(f)
    total_profit = 0
    total_price_change = 0

    if TEST_MODE:
        #get coins and price on test exchange - otherwise hit and miss
        prices = client.get_all_tickers()
        for coin in prices:
            print(f"{coin['symbol']} - {coin['price']}")

    for coin in list(coins):

        #Get Stock Tick size to round the new prices
        info = client.get_symbol_info(coin)
        step_size = float(info['filters'][2]['stepSize'])
        tick_size = float(info['filters'][0]['tickSize'])
        
        #Get current price to check StopPx
        LastTradePrice =float(client.get_symbol_ticker(symbol=coin)['price'])
               
        #calculate the OCO prices
        BuyPrice = float(coins[coin]['bought_at'])
        SellPrice = round_step_size(((BuyPrice * (coins[coin]['take_profit']/100)) + BuyPrice),tick_size)
        StopOrderTrigger = round_step_size(((BuyPrice * (coins[coin]['stop_loss']/100)) + BuyPrice),tick_size)
        StopOrderPrice = round_step_size(((BuyPrice * (coins[coin]['stop_loss']/100)) + BuyPrice),tick_size)
        print(f"Sell OCO: {coins[coin]['volume']} {coin} - BP: {BuyPrice} - SP: {SellPrice} - SOT: {StopOrderTrigger} - SOP: {StopOrderPrice} - LP: {LastTradePrice}")

        try:
            if StopOrderPrice > LastTradePrice:
                #Stop price is higher then we can't create OCO/Stop order - create sell limit 
                sell_coin = client.create_order(
                                symbol = coin,
                                side = 'SELL',
                                type = 'LIMIT',
                                price = SellPrice,
                                timeInForce="GTC",
                                quantity = coins[coin]['volume']
                            )
                SellType = " LONG "
            else:
                sell_coin = client.create_oco_order(
                    symbol = coin,
                    side = 'SELL',        
                    quantity = coins[coin]['volume'],        
                    price = SellPrice,
                    stopPrice = StopOrderTrigger,
                    stopLimitPrice = StopOrderPrice,
                    stopLimitTimeInForce = 'GTC'
                )
                SellType = " OCO "

        except BinanceAPIException as e:
            print(e)
     
        else: 
            remove_from_portfolio(coin)

            #OCO is not executed at this time so using SellPrice for Reference 
            LastPrice = SellPrice
                
            profit = (LastPrice - BuyPrice) * coins[coin]['volume']
            PriceChange = float((LastPrice - BuyPrice) / BuyPrice * 100)

            total_profit += profit
            total_price_change += PriceChange

            text_color = txcolors.SELL_PROFIT if PriceChange >= 0. else txcolors.SELL_LOSS
            console_log_text = f"{text_color}Sell OCO: {coins[coin]['volume']} {coin} - {BuyPrice} - {LastPrice} Profit: {profit:.2f} {PriceChange:.2f}%{txcolors.DEFAULT}"
            print(console_log_text)

            if LOG_TRADES:
                write_log(f"\tSell\t{coin}\t{coins[coin]['volume']}\t{BuyPrice}\t{PAIR_WITH}\t{LastPrice}\t{profit:.2f}\t{total_price_change:.2f}\tCreate {SellType} Sell")
