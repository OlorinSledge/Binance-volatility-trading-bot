"""
Horacio Oscar Fanelli - Pantersxx3
Version: 6.1

Disclaimer

All investment strategies and investments involve risk of loss.
Nothing contained in this program, scripts, code or repositoy should be
construed as investment advice.Any reference to an investment's past or
potential performance is not, and should not be construed as, a recommendation
or as a guarantee of any specific outcome or profit.

By using this program you accept all liabilities,
and that no claims can be made against the developers,
or others connected with the program.

See requirements.txt for versions of modules needed

Notes:
- Requires Python version 3.9.x to run

"""

# use for environment variables
import os

# use if needed to pass args to external modules
import sys

#for clear screen console
from os import system, name

# used for math functions
import math

# used to create threads & dynamic loading of modules
import threading
import multiprocessing
import importlib

# used for directory handling
import glob

#discord needs import request
import requests

# Needed for colorful console output Install with: python3 -m pip install colorama (Mac/Linux) or pip install colorama (PC)
from colorama import init
init()

# needed for the binance API / websockets / Exception handling
from binance.client import Client
from binance.exceptions import BinanceAPIException
from binance.helpers import round_step_size
from requests.exceptions import ReadTimeout, ConnectionError

# used for dates
from datetime import date, datetime, timedelta
import time

# used to repeatedly execute the code
from itertools import count

# used to store trades and sell assets
import json

#print output tables
from prettytable import PrettyTable, from_html_one
#from pretty_html_table import build_table

# Load helper modules
from helpers.parameters import (
    parse_args, load_config
)

# Load creds modules
from helpers.handle_creds import (
    load_correct_creds, test_api_key,
    load_discord_creds
)


# for colourful logging to the console
class txcolors:
    BUY = '\033[92m'
    WARNING = '\033[93m'
    SELL_LOSS = '\033[94m'
    SELL_PROFIT = '\033[32m'
    DIM = '\033[2m\033[35m'
    BORDER = '\033[33m'
    DEFAULT = '\033[39m'
    BOT_LOSSES = '\033[91m'
    BOT_WINS = '\033[92m'
    RED = '\033[91m'
    #Blue = '\033[94m'
    #Cyan = '\033[96m'
    #White = '\033[97m'
    #Yellow = '\033[93m'
    #Magenta = '\033[95m'
    #Grey = '\033[90m'
    #Black = '\033[90m'


# tracks profit/loss each session
global session_profit_incfees_perc, session_profit_incfees_total, session_tpsl_override_msg, is_bot_running, session_USDT_EARNED, last_msg_discord_balance_date, session_USDT_EARNED_TODAY, parsed_creds, TUP,PUP, TDOWN, PDOWN, TNEUTRAL, PNEUTRAL, renewlist, DISABLE_TIMESTAMPS, signalthreads, VOLATILE_VOLUME_LIST, FLAG_PAUSE, coins_up,coins_down,coins_unchanged, SHOW_TABLE_COINS_BOUGHT, USED_BNB_IN_SESSION, PAUSEBOT_MANUAL
last_price_global = 0
session_profit_incfees_perc = 0
session_profit_incfees_total = 0
session_tpsl_override_msg = ""
session_USDT_EARNED = 0
session_USDT_EARNED_TODAY = 0
last_msg_discord_balance_date = 0
coins_up = 0
coins_down = 0
coins_unchanged = 0
is_bot_running = True
renewlist = 0
FLAG_PAUSE = True
USED_BNB_IN_SESSION = 0
PAUSEBOT_MANUAL = False

global historic_profit_incfees_perc, historic_profit_incfees_total, trade_wins, trade_losses
global sell_all_coins, bot_started_datetime

try:
    historic_profit_incfees_perc
except NameError:
    historic_profit_incfees_perc = 0      # or some other default value.
try:
    historic_profit_incfees_total
except NameError:
    historic_profit_incfees_total = 0      # or some other default value.
try:
    trade_wins
except NameError:
    trade_wins = 0      # or some other default value.
try:
    trade_losses
except NameError:
    trade_losses = 0      # or some other default value.

bot_started_datetime = ""

def is_fiat():
    # check if we are using a fiat as a base currency
    global hsp_head
    PAIR_WITH = parsed_config['trading_options']['PAIR_WITH']
    #list below is in the order that Binance displays them, apologies for not using ASC order
    fiats = ['USDT', 'BUSD', 'AUD', 'BRL', 'EUR', 'GBP', 'RUB', 'TRY', 'TUSD', 'USDC', 'PAX', 'BIDR', 'DAI', 'IDRT', 'UAH', 'NGN', 'VAI', 'BVND', 'USDP']

    if PAIR_WITH in fiats:
        return True
    else:
        return False

def decimals():
    # set number of decimals for reporting fractions
    if is_fiat():
        return 4
    else:
        return 8

def get_price(add_to_historical=True):
    '''Return the current price for all coins on binance'''
    global historical_prices, hsp_head

    initial_price = {}    
    prices = client.get_all_tickers()
    
    renew_list()
    try:
        for coin in prices:
            if CUSTOM_LIST:
                # intickers = False
                # inex_pairs = False
                for item1 in tickers:
                    if item1 + PAIR_WITH == coin['symbol'] and coin['symbol'].replace(PAIR_WITH, "") not in EX_PAIRS:
                        initial_price[coin['symbol']] = { 'price': coin['price'], 'time': datetime.now()} 
                        # intickers = True
                        # break
                # for item2 in EX_PAIRS:
                    # if item2 + PAIR_WITH == coin['symbol']:
                        # inex_pairs = True
                        # break
                # if intickers == True and inex_pairs == False:
                   # initial_price[coin['symbol']] = { 'price': coin['price'], 'time': datetime.now()}                
                    
                # if any(item + PAIR_WITH == coin['symbol'] for item in tickers) and all(item not in coin['symbol'] for item in EX_PAIRS): #and all(item not in coin['symbol'] for item in FIATS)
                    # initial_price[coin['symbol']] = { 'price': coin['price'], 'time': datetime.now()}
                    #print("CUSTOM_LIST", coin['symbol'])

            else:
                if PAIR_WITH in coin['symbol'] and all(item not in coin['symbol'] for item in EX_PAIRS):
                    initial_price[coin['symbol']] = { 'price': coin['price'], 'time': datetime.now()}

        if add_to_historical:
            hsp_head += 1

            if hsp_head == RECHECK_INTERVAL:
                hsp_head = 0

            historical_prices[hsp_head] = initial_price
    except Exception as e:
        print(f'{"get_price"}: Exception in function: {e}')
        print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
        pass
    #except KeyboardInterrupt as ki:
        #pass
    return initial_price

#use function of the OlorinSledge
def wait_for_price():
    try:
        '''calls the initial price and ensures the correct amount of time has passed
        before reading the current price again'''

        global historical_prices, hsp_head, volatility_cooloff, coins_up,coins_down,coins_unchanged
     
        volatile_coins = {}
        externals = {}

        coins_up = 0
        coins_down = 0
        coins_unchanged = 0
    
        pause_bot()
        # get first element from the dictionary
        firstcoin = next(iter(historical_prices[hsp_head]))  

        #BBif historical_prices[hsp_head]['BNB' + PAIR_WITH]['time'] > datetime.now() - timedelta(minutes=float(TIME_DIFFERENCE / RECHECK_INTERVAL)):
        if historical_prices[hsp_head][firstcoin]['time'] > datetime.now() - timedelta(minutes=float(TIME_DIFFERENCE / RECHECK_INTERVAL)):
            # sleep for exactly the amount of time required
            #BBtime.sleep((timedelta(minutes=float(TIME_DIFFERENCE / RECHECK_INTERVAL)) - (datetime.now() - historical_prices[hsp_head]['BNB' + PAIR_WITH]['time'])).total_seconds())    
            time.sleep((timedelta(minutes=float(TIME_DIFFERENCE / RECHECK_INTERVAL)) - (datetime.now() - historical_prices[hsp_head][firstcoin]['time'])).total_seconds())    

        # retrieve latest prices
        renew_list()
        last_price = get_price()

        # Moved to the end of this method
        # balance_report(last_price)

        # calculate the difference in prices
        for coin in historical_prices[hsp_head]:

            # minimum and maximum prices over time period
            min_price = min(historical_prices, key = lambda x: float("inf") if x is None else float(x[coin]['price']))
            max_price = max(historical_prices, key = lambda x: -1 if x is None else float(x[coin]['price']))

            threshold_check = (-1.0 if min_price[coin]['time'] > max_price[coin]['time'] else 1.0) * (float(max_price[coin]['price']) - float(min_price[coin]['price'])) / float(min_price[coin]['price']) * 100

            # each coin with higher gains than our CHANGE_IN_PRICE is added to the volatile_coins dict if less than TRADE_SLOTS is not reached.
            if threshold_check > CHANGE_IN_PRICE:
                coins_up +=1

                if coin not in volatility_cooloff:
                    volatility_cooloff[coin] = datetime.now() - timedelta(minutes=TIME_DIFFERENCE)
                    # volatility_cooloff[coin] = datetime.now() - timedelta(minutes=COOLOFF_PERIOD)
                
                # only include coin as volatile if it hasn't been picked up in the last TIME_DIFFERENCE minutes already
                if datetime.now() >= volatility_cooloff[coin] + timedelta(minutes=TIME_DIFFERENCE):
                #if datetime.now() >= volatility_cooloff[coin] + timedelta(minutes=COOLOFF_PERIOD):
                    volatility_cooloff[coin] = datetime.now()

                    if len(coins_bought) + len(volatile_coins) < TRADE_SLOTS or TRADE_SLOTS == 0:
                        volatile_coins[coin] = round(threshold_check, 3)
                        print(f'{coin} has gained {volatile_coins[coin]}% within the last {TIME_DIFFERENCE} minutes, purchasing ${TRADE_TOTAL} {PAIR_WITH} of {coin}!')

                    else:
                        print(f'{txcolors.WARNING}{coin} has gained {round(threshold_check, 3)}% within the last {TIME_DIFFERENCE} minutes, but you are using all available trade slots!{txcolors.DEFAULT}')
                #else:
                    #if len(coins_bought) == TRADE_SLOTS:
                    #    print(f'{txcolors.WARNING}{coin} has gained {round(threshold_check, 3)}% within the last {TIME_DIFFERENCE} minutes, but you are using all available trade slots!{txcolors.DEFAULT}')
                    #else:
                    #    print(f'{txcolors.WARNING}{coin} has gained {round(threshold_check, 3)}% within the last {TIME_DIFFERENCE} minutes, but failed cool off period of {COOLOFF_PERIOD} minutes! Curr COP is {volatility_cooloff[coin] + timedelta(minutes=COOLOFF_PERIOD)}{txcolors.DEFAULT}')
            elif threshold_check < CHANGE_IN_PRICE:
                coins_down +=1

            else:
                coins_unchanged +=1

        # Disabled until fix
        #print(f'Up: {coins_up} Down: {coins_down} Unchanged: {coins_unchanged}')

        # Here goes new code for external signalling
        externals = buy_external_signals()
        exnumber = 0

        for excoin in externals:
            if excoin not in volatile_coins and excoin not in coins_bought and (len(coins_bought) + len(volatile_coins)) < TRADE_SLOTS:
                #(len(coins_bought) + exnumber + len(volatile_coins)) < TRADE_SLOTS:
                volatile_coins[excoin] = 1
                exnumber +=1
                print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}External signal received on {excoin}, purchasing ${TRADE_TOTAL} {PAIR_WITH} value of {excoin}!')
                with open(EXTERNAL_COINS,'a+') as f:
                    f.write(excoin + '\n')

        balance_report(last_price)
    except Exception as e:
        print(f'{"wait_for_price"}: Exception in function: {e}')
        print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
        pass
    return volatile_coins, len(volatile_coins), historical_prices[hsp_head]


def buy_external_signals():
    external_list = {}
    #signals = {}

    # check directory and load pairs from files into external_list
    files = []
    folder = "signals"
    files = [item for sublist in [glob.glob(folder + ext) for ext in ["/*.buy", "/*.exs"]] for item in sublist]

    #signals = glob.glob(mask)  #"signals/*.buy")
    #print("signals: ", signals)
    for filename in files: #signals:
        for line in open(filename):
            symbol = line.strip()
            if symbol.replace(PAIR_WITH, "") not in EX_PAIRS:
                external_list[symbol] = symbol
        try:
            os.remove(filename)
        except:
            if DEBUG: print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.WARNING}Could not remove external signalling file{txcolors.DEFAULT}')

    return external_list

def sell_external_signals():
    external_list = {}
    signals = {}

    # check directory and load pairs from files into external_list
    signals = glob.glob("signals/*.sell")
    for filename in signals:
        for line in open(filename):
            symbol = line.strip()
            external_list[symbol] = symbol
            if DEBUG: print(f'{symbol} added to sell_external_signals() list')
        try:
            os.remove(filename)
        except:
            if DEBUG: print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.WARNING}Could not remove external SELL signalling file{txcolors.DEFAULT}')

    return external_list

def get_volume_list():
    try:
        global COINS_MAX_VOLUME, COINS_MIN_VOLUME
        VOLATILE_VOLUME = "volatile_volume_" + str(date.today()) + ".txt"
        most_volume_coins = {}
        tickers_all = []
        #    os.remove(VOLATILE_VOLUME)
        #try:
        #if os.path.exists("tickers_all.txt") == True:
            #tickers_all=[line.strip() for line in open("tickers_all.txt")]
        #else:
            #VOLATILE_VOLUME = ""
        
        prices = client.get_all_tickers()
        
        for coin in prices:
            if coin['symbol'] == coin['symbol'].replace(PAIR_WITH, "") + PAIR_WITH:
                tickers_all.append(coin['symbol'].replace(PAIR_WITH, ""))

        c = 0
        if os.path.exists(VOLATILE_VOLUME) == False:
            load_settings()
            print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Creating volatile list, wait a moment...')
            if COINS_MAX_VOLUME.isnumeric() == False and COINS_MIN_VOLUME.isnumeric() == False:
                infocoinMax = client.get_ticker(symbol=COINS_MAX_VOLUME + PAIR_WITH)
                infocoinMin = client.get_ticker(symbol=COINS_MIN_VOLUME + PAIR_WITH)
                COINS_MAX_VOLUME = math.ceil(float(infocoinMax['quoteVolume']))
                COINS_MIN_VOLUME = round(float(infocoinMin['quoteVolume']))
                print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}COINS_MAX_VOLUME {COINS_MAX_VOLUME} and COINS_MIN_VOLUME {COINS_MIN_VOLUME} were set from specific currencies...')
        
            for coin in tickers_all:
                #try:
                infocoin = client.get_ticker(symbol= coin + PAIR_WITH)
                volumecoin = float(infocoin['quoteVolume']) #/ 1000000                
                if volumecoin <= COINS_MAX_VOLUME and volumecoin >= COINS_MIN_VOLUME and coin not in EX_PAIRS and coin not in most_volume_coins:
                    most_volume_coins.update({coin : volumecoin})  					
                    c = c + 1
                # except Exception as e:
                    # print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
                    # continue
                    
            if c <= 0: 
                print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Cannot continue because there are no coins in the selected range, change the settings and start the bot again...')
                sys.exit()
                
            sortedVolumeList = sorted(most_volume_coins.items(), key=lambda x: x[1], reverse=True)
            
            print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Saving {str(c)} coins to {VOLATILE_VOLUME} ...')
            
            for coin in sortedVolumeList:
                with open(VOLATILE_VOLUME,'a+') as f:
                    f.write(coin[0] + '\n')
        else:
            if ALWAYS_OVERWRITE == False:
                print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}There is already a recently created list, if you want to create a new list, stop the bot and delete the previous one.')
                print(f'{txcolors.WARNING}REMEMBER: {txcolors.DEFAULT}if you create a new list when continuing a previous session, it may not coincide with the previous one and give errors...')
    except Exception as e:
        print(f'{"get_volume_list"}: Exception in function: {e}')
        print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
        print("COIN_ERROR: ", coin + PAIR_WITH)
        exit(1)
    return VOLATILE_VOLUME

def print_table_coins_bought():
    try:
        if SHOW_TABLE_COINS_BOUGHT:
            if len(coins_bought) > 0:
                my_table = PrettyTable()
                my_table.format = True
                my_table.border = True
                my_table.align = "c"
                my_table.valign = "m"
                my_table.field_names = ["Symbol", "Volume", "Bought At", "Now At", "TP %", "SL %", "Change %", "Profit $", "Time Held"]
                last_price = get_price(False)
                for coin in list(coins_bought):
                    LastPriceT = round(float(last_price[coin]['price']),3)
                    sellFeeT = (LastPriceT * (TRADING_FEE/100))
                    LastPriceLessFeesT = round((LastPriceT - sellFeeT), 2)
                    BuyPriceT = round(float(coins_bought[coin]['bought_at']),3)
                    buyFeeT = (BuyPriceT * (TRADING_FEE/100))
                    BuyPricePlusFeesT = BuyPriceT + buyFeeT
                    #ProfitAfterFees = round((LastPriceLessFees - BuyPricePlusFees), 2)
                    #PriceChangeIncFees_Perc = round(float(((LastPriceLessFees - BuyPricePlusFees) / BuyPricePlusFees) * 100), 3)
                    PriceChangeIncFees_PercT = round(float(((LastPriceT - BuyPricePlusFeesT) / BuyPricePlusFeesT) * 100), 3) 
                    PriceChange_PercT = round(float(((LastPriceT - BuyPriceT) / BuyPriceT) * 100), 3)
                    #if PriceChangeIncFees_Perc == -100: PriceChangeIncFees_Perc = 0
                    time_held = timedelta(seconds=datetime.now().timestamp()-int(str(coins_bought[coin]['timestamp'])[:10]))
                    #if IGNORE_FEE: 
                        #my_table.add_row([f"{txcolors.SELL_PROFIT if PriceChangeIncFees_Perc >= 0. else txcolors.RED}{coin.replace(PAIR_WITH,'')}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if PriceChangeIncFees_Perc >= 0. else txcolors.RED}{coins_bought[coin]['volume']:.2f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if PriceChangeIncFees_Perc >= 0. else txcolors.RED}{BuyPrice:.6f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if PriceChangeIncFees_Perc >= 0. else txcolors.RED}{LastPrice:.6f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if PriceChangeIncFees_Perc >= 0. else txcolors.RED}{coins_bought[coin]['take_profit']:.2f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if PriceChangeIncFees_Perc >= 0. else txcolors.RED}{coins_bought[coin]['stop_loss']:.2f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if PriceChangeIncFees_Perc >= 0. else txcolors.RED}{PriceChangeIncFees_Perc:.2f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if PriceChangeIncFees_Perc >= 0. else txcolors.RED}{((float(coins_bought[coin]['volume'])*float(coins_bought[coin]['bought_at']))*PriceChangeIncFees_Perc)/100:.2f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if PriceChangeIncFees_Perc >= 0. else txcolors.RED}{str(time_held).split('.')[0]}{txcolors.DEFAULT}"])
                    my_table.add_row([f"{txcolors.SELL_PROFIT if PriceChangeIncFees_PercT >= 0. else txcolors.RED}{coin.replace(PAIR_WITH,'')}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if PriceChangeIncFees_PercT >= 0. else txcolors.RED}{coins_bought[coin]['volume']:.5f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if PriceChangeIncFees_PercT >= 0. else txcolors.RED}{BuyPriceT:.3f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if PriceChangeIncFees_PercT >= 0. else txcolors.RED}{LastPriceT:.3f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if PriceChangeIncFees_PercT >= 0. else txcolors.RED}{coins_bought[coin]['take_profit']:.2f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if PriceChangeIncFees_PercT >= 0. else txcolors.RED}{coins_bought[coin]['stop_loss']:.2f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if PriceChangeIncFees_PercT >= 0. else txcolors.RED}{PriceChangeIncFees_PercT:.2f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if PriceChangeIncFees_PercT >= 0. else txcolors.RED}{((float(coins_bought[coin]['volume'])*float(coins_bought[coin]['bought_at']))*PriceChangeIncFees_PercT)/100:.2f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if PriceChangeIncFees_PercT >= 0. else txcolors.RED}{str(time_held).split('.')[0]}{txcolors.DEFAULT}"])
                my_table.sortby = SORT_TABLE_BY
                my_table.reversesort = REVERSE_SORT
                print(my_table)
                print("\n")
    except Exception as e:
        print(f'{"print_table_coins_bought"}: Exception in function: {e}')
        print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
        pass


def clear():
    # for windows
    if name == 'nt':
        _ = system('cls')  
    # for mac and linux(here, os.name is 'posix')
    else:
        _ = system('clear')

def balance_report(last_price):
    try:
        global trade_wins, trade_losses, session_profit_incfees_perc, session_profit_incfees_total, last_price_global, session_USDT_EARNED_TODAY, session_USDT_EARNED, TUP, TDOWN, TNEUTRAL
        unrealised_session_profit_incfees_perc = 0
        unrealised_session_profit_incfees_total = 0
        msg1 = ""
        msg2 = ""

        BUDGET = TRADE_SLOTS * TRADE_TOTAL
        exposure_calcuated = 0
        for coin in list(coins_bought):
            LastPriceBR = float(last_price[coin]['price'])
            sellFeeBR = (LastPriceBR * (TRADING_FEE/100))
            
            BuyPriceBR = float(coins_bought[coin]['bought_at'])
            buyFeeBR = (BuyPriceBR * (TRADING_FEE/100))

            exposure_calcuated = exposure_calcuated + round(float(coins_bought[coin]['bought_at']) * float(coins_bought[coin]['volume']),0)

            #PriceChangeIncFees_Perc = float(((LastPrice+sellFee) - (BuyPrice+buyFee)) / (BuyPrice+buyFee) * 100)
            #PriceChangeIncFees_Total = float(((LastPrice+sellFee) - (BuyPrice+buyFee)) * coins_bought[coin]['volume'])
            PriceChangeIncFees_TotalBR = float(((LastPriceBR-sellFeeBR) - (BuyPriceBR+buyFeeBR)) * coins_bought[coin]['volume'])

            # unrealised_session_profit_incfees_perc = float(unrealised_session_profit_incfees_perc + PriceChangeIncFees_Perc)
            unrealised_session_profit_incfees_total = float(unrealised_session_profit_incfees_total + PriceChangeIncFees_TotalBR)
                
        unrealised_session_profit_incfees_perc = (unrealised_session_profit_incfees_total / BUDGET) * 100

        DECIMALS = int(decimals())
        # CURRENT_EXPOSURE = round((TRADE_TOTAL * len(coins_bought)), DECIMALS)
        CURRENT_EXPOSURE = round(exposure_calcuated, 0)
        INVESTMENT_TOTAL = round((TRADE_TOTAL * TRADE_SLOTS), DECIMALS)
        
        # truncating some of the above values to the correct decimal places before printing
        WIN_LOSS_PERCENT = 0
        if (trade_wins > 0) and (trade_losses > 0):
            WIN_LOSS_PERCENT = round((trade_wins / (trade_wins+trade_losses)) * 100, 2)
        if (trade_wins > 0) and (trade_losses == 0):
            WIN_LOSS_PERCENT = 100
        strplus = "+"
        if STATIC_MAIN_INFO == True: clear()
        if SCREEN_MODE < 2: print(f'')
        if SCREEN_MODE == 2: print(f'')
        if SCREEN_MODE < 2: print(f'{txcolors.BORDER}+---------------------------------------------------------------------------+{txcolors.DEFAULT}')
        if SCREEN_MODE < 2: print(f'{txcolors.BORDER}+{txcolors.DEFAULT}STARTED         : {txcolors.SELL_LOSS}{str(bot_started_datetime).split(".")[0]}{txcolors.DEFAULT} | Running for: {txcolors.SELL_LOSS}{str(datetime.now() - bot_started_datetime).split(".")[0]} {txcolors.BORDER}{"+".rjust(15)}{txcolors.DEFAULT}')
        if SCREEN_MODE == 2: print(f'{txcolors.DEFAULT}STARTED: {txcolors.SELL_LOSS}{str(bot_started_datetime).split(".")[0]}{txcolors.DEFAULT} | Running for: {txcolors.SELL_LOSS}{str(datetime.now() - bot_started_datetime).split(".")[0]}{txcolors.DEFAULT}')
        if SCREEN_MODE < 2: print(f'{txcolors.BORDER}+{txcolors.DEFAULT}CURRENT HOLDS   : {txcolors.SELL_LOSS}{str(len(coins_bought)).zfill(4)}{txcolors.DEFAULT}/{txcolors.SELL_LOSS}{str(TRADE_SLOTS).zfill(4)} {"{0:>5}".format(int(CURRENT_EXPOSURE))}{txcolors.DEFAULT}/{txcolors.SELL_LOSS}{"{0:<5}".format(int(INVESTMENT_TOTAL))} {txcolors.DEFAULT}{PAIR_WITH}{txcolors.BORDER}{"+".rjust(32)}{txcolors.DEFAULT}')
        if SCREEN_MODE == 2: print(f'{txcolors.DEFAULT}CURRENT HOLDS: {txcolors.SELL_LOSS}{str(len(coins_bought))}{txcolors.DEFAULT}/{txcolors.SELL_LOSS}{str(TRADE_SLOTS)} {int(CURRENT_EXPOSURE)}{txcolors.DEFAULT}/{txcolors.SELL_LOSS}{int(INVESTMENT_TOTAL)} {txcolors.DEFAULT}{PAIR_WITH}{txcolors.DEFAULT}')
        if SCREEN_MODE < 2: print(f'{txcolors.BORDER}+{txcolors.DEFAULT}BUYING PAUSE    : {txcolors.SELL_LOSS}{"{0:<5}".format(str(bot_paused))}{txcolors.BORDER}{"+".rjust(53)}{txcolors.DEFAULT}')
        if SCREEN_MODE == 2: print(f'{txcolors.DEFAULT}BUYING PAUSE: {txcolors.SELL_LOSS}{str(bot_paused)}{txcolors.DEFAULT}')
        if SCREEN_MODE < 2: print(f'{txcolors.BORDER}+{txcolors.DEFAULT}WINS / LOSSSES  : {txcolors.BOT_WINS}{str(trade_wins).zfill(5).ljust(5)}{txcolors.DEFAULT}/{txcolors.BOT_LOSSES}{str(trade_losses).zfill(5).ljust(5)} {txcolors.DEFAULT}Win%: {txcolors.SELL_LOSS}{str(int(float(WIN_LOSS_PERCENT))).zfill(3)}%{txcolors.BORDER}{"+".rjust(36)}{txcolors.DEFAULT}')
        if SCREEN_MODE == 2: print(f'{txcolors.DEFAULT}WINS/LOSSSES: {txcolors.BOT_WINS}{str(trade_wins)}{txcolors.DEFAULT}/{txcolors.BOT_LOSSES}{str(trade_losses)} {txcolors.DEFAULT}Win%: {txcolors.SELL_PROFIT if WIN_LOSS_PERCENT > 0. else txcolors.BOT_LOSSES}{float(WIN_LOSS_PERCENT):g}%{txcolors.DEFAULT}')
        if SCREEN_MODE < 2: print(f'{txcolors.BORDER}+---------------------------------------------------------------------------+{txcolors.DEFAULT}')
        if SCREEN_MODE < 2: print(f'')
        #if SCREEN_MODE < 2: print(f'{txcolors.BORDER}+---------------------------------------------------------------------------+{txcolors.DEFAULT}')
        #if SCREEN_MODE < 2: print(f'{txcolors.BORDER}+{txcolors.DEFAULT}PENDING : {txcolors.SELL_PROFIT if unrealised_session_profit_incfees_perc > 0. else txcolors.SELL_LOSS}{str(round(unrealised_session_profit_incfees_perc,3)).center(8)}% Est:${str(round(unrealised_session_profit_incfees_total,3)).center(8)} {PAIR_WITH.center(6)}{txcolors.DEFAULT}{txcolors.BORDER}{"+".rjust(36)}{txcolors.DEFAULT}')
        #if SCREEN_MODE == 2: print(f'{txcolors.DEFAULT}PENDING: {txcolors.SELL_PROFIT if unrealised_session_profit_incfees_perc > 0. else txcolors.SELL_LOSS}{str(round(unrealised_session_profit_incfees_perc,3))}% Est:${str(round(unrealised_session_profit_incfees_total,3))} {PAIR_WITH}{txcolors.DEFAULT}')
        #if SCREEN_MODE < 2: print(f'{txcolors.BORDER}+---------------------------------------------------------------------------+{txcolors.DEFAULT}')
        #if SCREEN_MODE < 2: print(f'')
        #if SCREEN_MODE < 2: print(f'{txcolors.BORDER}+---------------------------------------------------------------------------+')
        #if SCREEN_MODE < 2: print(f'{txcolors.BORDER}+{txcolors.DEFAULT}COIN STATUS : {txcolors.SELL_PROFIT}Up {coins_up}, {txcolors.SELL_LOSS}Down: {coins_down}{txcolors.DEFAULT}, Unchanged: {coins_unchanged}{txcolors.BORDER}{"+".rjust(35)}')
        #if SCREEN_MODE == 2: print(f'{txcolors.DEFAULT}COIN STATUS: {txcolors.SELL_PROFIT}Up {coins_up}, {txcolors.SELL_LOSS}Down: {coins_down}{txcolors.DEFAULT}, Unchanged: {coins_unchanged}')
        #if SCREEN_MODE < 2: print(f'{txcolors.BORDER}+---------------------------------------------------------------------------+')
        #if SCREEN_MODE < 2: print(f'')
        #if SCREEN_MODE < 2: print(f'{txcolors.BORDER}+---------------------------------------------------------------------------+{txcolors.DEFAULT}')
        #if SCREEN_MODE < 2: print(f'{txcolors.BORDER}+{txcolors.DEFAULT}TOTAL   : {txcolors.SELL_PROFIT if (session_profit_incfees_perc + unrealised_session_profit_incfees_perc) > 0. else txcolors.SELL_LOSS}{str(round(session_profit_incfees_perc + unrealised_session_profit_incfees_perc,3)).center(8)}% Est:${str(round(session_profit_incfees_total+unrealised_session_profit_incfees_total,3)).center(8)} {PAIR_WITH.center(6)}{txcolors.DEFAULT}{txcolors.BORDER}{"+".rjust(36)}{txcolors.DEFAULT}')
        #if SCREEN_MODE == 2: print(f'{txcolors.DEFAULT}TOTAL: {txcolors.SELL_PROFIT if (session_profit_incfees_perc + unrealised_session_profit_incfees_perc) > 0. else txcolors.SELL_LOSS}{str(round(session_profit_incfees_perc + unrealised_session_profit_incfees_perc,3))}% Est:${str(round(session_profit_incfees_total+unrealised_session_profit_incfees_total,3))} {PAIR_WITH}{txcolors.DEFAULT}')
        #if SCREEN_MODE < 2: print(f'{txcolors.BORDER}+---------------------------------------------------------------------------+{txcolors.DEFAULT}')
        #if SCREEN_MODE < 2: print(f'')
        #if SCREEN_MODE < 2: print(f'{txcolors.BORDER}+---------------------------------------------------------------------------+{txcolors.DEFAULT}')
        #if SCREEN_MODE < 2: print(f'{txcolors.BORDER}+{txcolors.DEFAULT}BNB USED  : {txcolors.SELL_PROFIT} {"{0:>5}".format(str(format(float(USED_BNB_IN_SESSION), ".8f")))} {txcolors.DEFAULT}')
        #if SCREEN_MODE == 2: print(f'{txcolors.DEFAULT}BNB USED: {txcolors.SELL_PROFIT}{str(format(float(USED_BNB_IN_SESSION), ".6f"))} {txcolors.DEFAULT}')
        #if SCREEN_MODE < 2: print(f'{txcolors.BORDER}+---------------------------------------------------------------------------+{txcolors.DEFAULT}')
        #if SCREEN_MODE < 2: print(f'')
        if SCREEN_MODE < 2: print(f'{txcolors.BORDER}+{txcolors.DEFAULT}EARNED  : {txcolors.SELL_PROFIT if session_USDT_EARNED > 0. else txcolors.BOT_LOSSES}{"{0:>5}".format(str(format(float(session_USDT_EARNED), ".14f")))} {txcolors.DEFAULT}{PAIR_WITH.center(6)} |  {txcolors.SELL_PROFIT if (session_USDT_EARNED * 100)/INVESTMENT_TOTAL > 0. else txcolors.BOT_LOSSES}{round((session_USDT_EARNED * 100)/INVESTMENT_TOTAL, 3)}%{txcolors.BORDER}{"+".rjust(33)}{txcolors.DEFAULT}')
        if SCREEN_MODE == 2: print(f'{txcolors.DEFAULT}EARNED: {txcolors.SELL_PROFIT if session_USDT_EARNED > 0. else txcolors.BOT_LOSSES}{str(format(float(session_USDT_EARNED), ".14f"))} {txcolors.DEFAULT}{PAIR_WITH} | Profit%: {txcolors.SELL_PROFIT if (session_USDT_EARNED * 100)/INVESTMENT_TOTAL > 0. else txcolors.BOT_LOSSES}{round((session_USDT_EARNED * 100)/INVESTMENT_TOTAL,3)}%{txcolors.DEFAULT}')
        if SCREEN_MODE < 2: print(f'{txcolors.BORDER}+---------------------------------------------------------------------------+{txcolors.DEFAULT}')
        #if SCREEN_MODE < 2: print(f'')
        #if SCREEN_MODE < 2: print(f'{txcolors.BORDER}+---------------------------------------------------------------------------+{txcolors.DEFAULT}')
        #if SCREEN_MODE < 2: print(f'{txcolors.BORDER}+{txcolors.DEFAULT}BOT PROFIT  : {txcolors.SELL_PROFIT if historic_profit_incfees_perc > 0. else txcolors.SELL_LOSS}{historic_profit_incfees_perc:.4f}% Est: ${historic_profit_incfees_total:.4f} {PAIR_WITH.center(6)}{txcolors.BORDER}{"+".rjust(35)}{txcolors.DEFAULT}')
        #if SCREEN_MODE == 2: print(f'{txcolors.DEFAULT}BOT PROFIT: {txcolors.SELL_PROFIT if historic_profit_incfees_perc > 0. else txcolors.SELL_LOSS}{historic_profit_incfees_perc:.4f}% Est: ${historic_profit_incfees_total:.4f} {PAIR_WITH}{txcolors.DEFAULT}')
        #if SCREEN_MODE < 2: print(f'{txcolors.BORDER}+---------------------------------------------------------------------------+{txcolors.DEFAULT}')
        print(f'')
        print_table_coins_bought()
        #improving reporting messages
        msg1 = str(datetime.now()) + "\n"
        msg2 = " STARTED         : " + str(bot_started_datetime) + "\n"
        msg2 = msg2 + " RUNNING FOR     : " + str(datetime.now() - bot_started_datetime) + "\n"
        msg2 = msg2 + " TEST_MODE       : " + str(TEST_MODE) + "\n"
        msg2 = msg2 + " CURRENT HOLDS   : " + str(len(coins_bought)/TRADE_SLOTS) + "(" + str(float(CURRENT_EXPOSURE)/float(INVESTMENT_TOTAL)) + PAIR_WITH + ")" + "\n"
        msg2 = msg2 + " WIN             : " + str(trade_wins) + "\n"
        msg2 = msg2 + " LOST            : " + str(trade_losses) + "\n"
        msg2 = msg2 + " BUYING PAUSED   : " + str(bot_paused) + "\n"
        msg2 = msg2 + PAIR_WITH + " EARNED     : " + str(session_USDT_EARNED) + "\n"
        if (datetime.now() - bot_started_datetime) > timedelta(1):
            session_USDT_EARNED_TODAY = session_USDT_EARNED_TODAY + session_USDT_EARNED
            msg2 = msg2 + PAIR_WITH + " EARNED TODAY: " + str(session_USDT_EARNED_TODAY)
            session_USDT_EARNED_TODAY = 0

        #msg1 = str(datetime.now())
        #msg2 = " | " + str(len(coins_bought)) + "/" + str(TRADE_SLOTS) + " | PBOT: " + str(bot_paused)
        #msg2 = msg2 + ' SPR%: ' + str(round(session_profit_incfees_perc,2)) + ' SPR$: ' + str(round(session_profit_incfees_total,4))
        #msg2 = msg2 + ' SPU%: ' + str(round(unrealised_session_profit_incfees_perc,2)) + ' SPU$: ' + str(round(unrealised_session_profit_incfees_total,4))
        #msg2 = msg2 + ' SPT%: ' + str(round(session_profit_incfees_perc + unrealised_session_profit_incfees_perc,2)) + ' SPT$: ' + str(round(session_profit_incfees_total+unrealised_session_profit_incfees_total,4))
        #msg2 = msg2 + ' ATP%: ' + str(round(historic_profit_incfees_perc,2)) + ' ATP$: ' + str(round(historic_profit_incfees_total,4))
        #msg2 = msg2 + ' CTT: ' + str(trade_wins+trade_losses) + ' CTW: ' + str(trade_wins) + ' CTL: ' + str(trade_losses) + ' CTWR%: ' + str(round(WIN_LOSS_PERCENT,2))

        msg_discord_balance(msg1, msg2)
        history_log(session_profit_incfees_perc, session_profit_incfees_total, unrealised_session_profit_incfees_perc, unrealised_session_profit_incfees_total, session_profit_incfees_perc + unrealised_session_profit_incfees_perc, session_profit_incfees_total+unrealised_session_profit_incfees_total, historic_profit_incfees_perc, historic_profit_incfees_total, trade_wins+trade_losses, trade_wins, trade_losses, WIN_LOSS_PERCENT)
    except Exception as e:
        print(f'{"balance_report"}: Exception in function: {e}')
        print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
        pass
    
    return msg1 + msg2

def history_log(sess_profit_perc, sess_profit, sess_profit_perc_unreal, sess_profit_unreal, sess_profit_perc_total, sess_profit_total, alltime_profit_perc, alltime_profit, total_trades, won_trades, lost_trades, winloss_ratio):
    global last_history_log_date
    
    time_between_insertion = datetime.now() - last_history_log_date
    if TEST_MODE:
        file_prefix = 'test_'
    else:
        file_prefix = 'live_'
    # only log balance to log file once every 60 seconds
    if time_between_insertion.seconds > 60:
        last_history_log_date = datetime.now()
        timestamp = datetime.now().strftime("%y-%m-%d %H:%M:%S")

        if os.path.exists(file_prefix + HISTORY_LOG_FILE):
            HISTORY_LOG_TABLE = PrettyTable([])
            with open(file_prefix + HISTORY_LOG_FILE, "r") as fp: 
                html = fp.read()
            HISTORY_LOG_TABLE = from_html_one(html)
            HISTORY_LOG_TABLE.format = True
            HISTORY_LOG_TABLE.border = True
            HISTORY_LOG_TABLE.align = "c"
            HISTORY_LOG_TABLE.valign = "m"
            HISTORY_LOG_TABLE.hrules = 1
            HISTORY_LOG_TABLE.vrules = 1
            HISTORY_LOG_TABLE.add_row([timestamp, len(coins_bought), TRADE_SLOTS, str(bot_paused), str(round(sess_profit_perc,2)), str(round(sess_profit,4)), str(round(sess_profit_perc_unreal,2)), str(round(sess_profit_unreal,4)), str(round(sess_profit_perc_total,2)), str(round(sess_profit_total,4)), str(round(alltime_profit_perc,2)), str(round(alltime_profit,4)), str(total_trades), str(won_trades), str(lost_trades), str(winloss_ratio)])
            table_txt = HISTORY_LOG_TABLE.get_html_string()
            #table_txt = HISTORY_LOG_TABLE.get_string()
        else:
            HISTORY_LOG_TABLE = PrettyTable([])
            HISTORY_LOG_TABLE = PrettyTable(["Datetime", "Coins Holding", "Trade Slots", "Pausebot Active", "Session Profit %", "Session Profit $", "Session Profit Unrealised %", "Session Profit Unrealised $", "Session Profit Total %", "Session Profit Total $", "All Time Profit %", "All Time Profit $", "Total Trades", "Won Trades", "Lost Trades", "Win Loss Ratio"])
            HISTORY_LOG_TABLE.format = True
            HISTORY_LOG_TABLE.border = True
            HISTORY_LOG_TABLE.align = "c"
            HISTORY_LOG_TABLE.valign = "m"
            HISTORY_LOG_TABLE.hrules = 1
            HISTORY_LOG_TABLE.vrules = 1
        #    with open(HISTORY_LOG_FILE,'a+') as f:
        #        f.write('Datetime\tCoins Holding\tTrade Slots\tPausebot Active\tSession Profit %\tSession Profit $\tSession Profit Unrealised %\tSession Profit Unrealised $\tSession Profit Total %\tSession Profit Total $\tAll Time Profit %\tAll Time Profit $\tTotal Trades\tWon Trades\tLost Trades\tWin Loss Ratio\n')    
            HISTORY_LOG_TABLE.add_row([timestamp, len(coins_bought), TRADE_SLOTS, str(bot_paused), str(round(sess_profit_perc,2)), str(round(sess_profit,4)), str(round(sess_profit_perc_unreal,2)), str(round(sess_profit_unreal,4)), str(round(sess_profit_perc_total,2)), str(round(sess_profit_total,4)), str(round(alltime_profit_perc,2)), str(round(alltime_profit,4)), str(total_trades), str(won_trades), str(lost_trades), str(winloss_ratio)])
            table_txt = HISTORY_LOG_TABLE.get_html_string()
            #table_txt = HISTORY_LOG_TABLE.get_string()
        if not table_txt == "":
            with open(file_prefix + HISTORY_LOG_FILE,'w') as f:
            #f.write(f'{timestamp}\t{len(coins_bought)}\t{TRADE_SLOTS}\t{str(bot_paused)}\t{str(round(sess_profit_perc,2))}\t{str(round(sess_profit,4))}\t{str(round(sess_profit_perc_unreal,2))}\t{str(round(sess_profit_unreal,4))}\t{str(round(sess_profit_perc_total,2))}\t{str(round(sess_profit_total,4))}\t{str(round(alltime_profit_perc,2))}\t{str(round(alltime_profit,4))}\t{str(total_trades)}\t{str(won_trades)}\t{str(lost_trades)}\t{str(winloss_ratio)}\n')
                f.write(table_txt)
				
def write_log(logline):
    #timestamp = datetime.now().strftime("%y-%m-%d %H:%M:%S")
    if TEST_MODE:
        file_prefix = 'test_'
    else:
        file_prefix = 'live_'
        
    if os.path.exists(file_prefix + LOG_FILE):
        LOGTABLE = PrettyTable([])
        with open(file_prefix + LOG_FILE, "r") as fp: 
            html = fp.read()
        LOGTABLE = from_html_one(html)
        LOGTABLE.format = True
        LOGTABLE.border = True
        LOGTABLE.align = "c"
        LOGTABLE.valign = "m"
        LOGTABLE.hrules = 1
        LOGTABLE.vrules = 1
        LOGTABLE.add_row(logline)
        #table_txt = LOGTABLE.get_string()
        LOGTABLE.sortby = "Coin"
        table_txt = LOGTABLE.get_html_string()
    else:
        LOGTABLE = PrettyTable([])
        LOGTABLE = PrettyTable(["Datetime", "Type", "Coin", "Volume", "Buy Price", "Amount of Buy", "Sell Price", "Amount of Sell", "Sell Reason", "Profit $"])
        LOGTABLE.format = True
        LOGTABLE.border = True
        LOGTABLE.align = "c"
        LOGTABLE.valign = "m"
        LOGTABLE.hrules = 1
        LOGTABLE.vrules = 1
        LOGTABLE.add_row(logline)
        LOGTABLE.sortby = "Coin"
        table_txt = LOGTABLE.get_html_string()
        #table_txt = LOGTABLE.get_string()
        #with open(LOG_FILE,'w') as f:
		#improving the presentation of the log file
            #f.write('Datetime\t\tType\t\tCoin\t\t\tVolume\t\t\tBuy Price\t\tCurrency\t\t\tSell Price\tProfit $\t\tProfit %\tSell Reason\t\t\t\tEarned\n')    
    if not table_txt == "":
        with open(file_prefix + LOG_FILE,'w') as f:
        #f.write(timestamp + ' ' + logline + '\n')
            f.write(table_txt)
			
def msg_discord_balance(msg1, msg2):
    global last_msg_discord_balance_date, discord_msg_balance_data, last_msg_discord_balance_date
    time_between_insertion = datetime.now() - last_msg_discord_balance_date

    # only put the balance message to discord once every 60 seconds and if the balance information has changed since last times
    # message sending time was increased to 2 minutes for more convenience
    if time_between_insertion.seconds > 120:
        if msg2 != discord_msg_balance_data:
            msg_discord(msg1 + msg2)
            discord_msg_balance_data = msg2
        else:
            # ping msg to know the bot is still running
            msg_discord(".")
        #the variable is initialized so that sending messages every 2 minutes can work
        last_msg_discord_balance_date = datetime.now()

def msg_discord(msg):
    message = msg + '\n\n'
    if MSG_DISCORD:
        #Webhook of my channel. Click on edit channel --> Webhooks --> Creates webhook
        mUrl = "https://discordapp.com/api/webhooks/"+DISCORD_WEBHOOK
        data = {"content": message}
        response = requests.post(mUrl, json=data)
        #BB
        # print(response.content)

def pause_bot():
    '''Pause the script when external indicators detect a bearish trend in the market'''
    global bot_paused, session_profit_incfees_perc, hsp_head, session_profit_incfees_total, PAUSEBOT_MANUAL

    # start counting for how long the bot has been paused
    start_time = time.perf_counter()
    try:
        while os.path.exists("signals/pausebot.pause") or PAUSEBOT_MANUAL:

            # do NOT accept any external signals to buy while in pausebot mode
            remove_external_signals('buy')

            if bot_paused == False:
                if PAUSEBOT_MANUAL:
                    if not SCREEN_MODE == 0: print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.WARNING}Purchase paused manually, stop loss and take profit will continue to work...{txcolors.DEFAULT}')
                    msg = str(datetime.now()) + ' | PAUSEBOT.Purchase paused manually, stop loss and take profit will continue to work...'
                else:
                    if not SCREEN_MODE == 0: print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.WARNING}Buying paused due to negative market conditions, stop loss and take profit will continue to work...{txcolors.DEFAULT}')
                    msg = str(datetime.now()) + ' | PAUSEBOT. Buying paused due to negative market conditions, stop loss and take profit will continue to work.'
                msg_discord(msg)

                bot_paused = True

            # Sell function needs to work even while paused
            coins_sold = sell_coins()
            remove_from_portfolio(coins_sold)
            last_price = get_price(True)

            # pausing here
            if hsp_head == 1: 
                # if not SCREEN_MODE == 2: print(f'Paused...Session profit: {session_profit_incfees_perc:.2f}% Est: ${session_profit_incfees_total:.{decimals()}f} {PAIR_WITH}')
                balance_report(last_price)
            
            time.sleep((TIME_DIFFERENCE * 60) / RECHECK_INTERVAL)

        else:
            # stop counting the pause time
            stop_time = time.perf_counter()
            time_elapsed = timedelta(seconds=int(stop_time-start_time))

            # resume the bot and ser pause_bot to False
            if  bot_paused == True:
                if not SCREEN_MODE == 2: print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.WARNING}Resuming buying due to positive market conditions, total sleep time: {time_elapsed}{txcolors.DEFAULT}')
                
                msg = str(datetime.now()) + ' | PAUSEBOT. Resuming buying due to positive market conditions, total sleep time: ' + str(time_elapsed)
                msg_discord(msg)

                bot_paused = False
    except Exception as e:
        print(f'{"pause_bot"}: Exception in function: {e}')
        print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
        pass
    return


def convert_volume():
    '''Converts the volume given in TRADE_TOTAL from "USDT"(or coin selected) to the each coin's volume'''
    volatile_coins, number_of_coins, last_price = wait_for_price()
 
    lot_size = {}
    volume = {}
    try:
        for coin in volatile_coins:

            # Find the correct step size for each coin
            # max accuracy for BTC for example is 6 decimal points
            # while XRP is only 1
            #try:
            info = client.get_symbol_info(coin)
            step_size = info['filters'][2]['stepSize']
            lot_size[coin] = step_size.index('1') - 1
            
            if lot_size[coin] < 0: lot_size[coin] = 0

            #except Exception as e:
                #if not SCREEN_MODE == 2: print(f'convert_volume() exception: {e}')
                #pass
            #except KeyboardInterrupt as ki:
                #pass
            #try: 
                #print("COIN: " + str(coin) + " TRADE_TOTAL: " + str(TRADE_TOTAL) + " last_price[coin]['price']: " + str(last_price[coin]['price']))
                # calculate the volume in coin from TRADE_TOTAL in PAIR_WITH (default)
            volume[coin] = float(TRADE_TOTAL / float(last_price[coin]['price']))

                # define the volume with the correct step size
            if coin not in lot_size:
                    # original code: volume[coin] = float('{:.1f}'.format(volume[coin]))
                volume[coin] = int(volume[coin])
            else:
                    # if lot size has 0 decimal points, make the volume an integer
                if lot_size[coin] == 0:
                    volume[coin] = int(volume[coin])
                else:
                        #volume[coin] = float('{:.{}f}'.format(volume[coin], lot_size[coin]))
                    volume[coin] = truncate(volume[coin], lot_size[coin])
            #except Exception as e:
                #if not SCREEN_MODE == 2: print(f'convert_volume()2 exception: {e}')
                #pass
            #except KeyboardInterrupt as ki:
                #pass
    except Exception as e:
        print(f'convert_volume() exception: {e}')
        print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
        pass
    #except KeyboardInterrupt as ki:
        #pass
    return volume, last_price

def set_exparis(pairs):
    file_name = "config.yml"
    parsed_config = load_config(file_name)
    with open(file_name, 'r') as file:
        data = file.readlines()
    c = 0
    for line in data:
        c = c + 1
        if "EX_PAIRS: [" in line:
            break
    #EX_PAIRS = parsed_config['trading_options']['EX_PAIRS']
    e = False
    pairs = pairs.strip().replace('USDT','')
    for coin in EX_PAIRS:
        if coin == pairs: 
            e = True
            break
        else:
            e = False
    if e == False:
        print(f'The exception has been saved in EX_PAIR in the configuration file...')
        EX_PAIRS.append(pairs)
        data[c-1] = "  EX_PAIRS: " + str(EX_PAIRS) + "\n"
        with open(file_name, 'w') as f:
            f.writelines(data)

def buy():
    try:
        '''Place Buy market orders for each volatile coin found'''
        volume, last_price = convert_volume()
        orders = {}
        global USED_BNB_IN_SESSION
        for coin in volume:
            if coin not in coins_bought and coin.replace(PAIR_WITH,'') not in EX_PAIRS:
                #litle modification of Sparky
                volume[coin] = math.floor(volume[coin]*100000)/100000
                if not SCREEN_MODE == 2: print(f"{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.BUY}Preparing to buy {volume[coin]} of {coin} @ ${last_price[coin]['price']}{txcolors.DEFAULT}")

                msg1 = str(datetime.now()) + ' | BUY: ' + coin + '. V:' +  str(volume[coin]) + ' P$:' + str(last_price[coin]['price']) + ' ' + PAIR_WITH + ' invested:' + str(float(volume[coin])*float(last_price[coin]['price']))
                msg_discord(msg1)
                
                if TEST_MODE:
                    orders[coin] = [{
                        'symbol': coin,
                        'orderId': 0,
                        'time': datetime.now().timestamp()
                    }]

                    # Log trade
                    #if LOG_TRADES:
                    BuyUSDT = str(float(volume[coin]) * float(last_price[coin]['price'])).zfill(9)
                    volumeBuy = format(volume[coin], '.6f')
                    last_price_buy = str(format(float(last_price[coin]['price']), '.8f')).zfill(3)
                    BuyUSDT = str(format(float(BuyUSDT), '.14f')).zfill(4)
                    coin = '{0:<9}'.format(coin)
                    #["Datetime",                                           "Type", "Coin", "Volume",               "Buy Price",                                     "Amount of Buy",                       "Sell Price", "Amount of Sell", "Sell Reason", "Profit $"] "USDTdiff"])
                    write_log([datetime.now().strftime("%y-%m-%d %H:%M:%S"), "Buy", coin.replace(PAIR_WITH,""), round(float(volumeBuy),5), str(round(float(last_price_buy),3)), str(round(float(BuyUSDT),3)) + " " + PAIR_WITH, 0, 0, "-", 0])                
                    write_signallsell(coin.removesuffix(PAIR_WITH))

                    continue

            # try to create a real order if the test orders did not raise an exception
                try:
                    order_details = client.create_order(
                        symbol = coin,
                        side = 'BUY',
                        type = 'MARKET',
                        quantity = volume[coin]
                    )

            # error handling here in case position cannot be placed
                except Exception as e:
                    print(f'buy() exception: {e}')
                    print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))

            # run the else block if the position has been placed and return order info
                else:
                    orders[coin] = client.get_all_orders(symbol=coin, limit=1)

                # binance sometimes returns an empty list, the code will wait here until binance returns the order
                    while orders[coin] == []:
                        if DEBUG: print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT} Binance is being slow in returning the order, calling the API again...')

                        orders[coin] = client.get_all_orders(symbol=coin, limit=1)
                        time.sleep(1)

                    else:
                        if DEBUG: print(f'Order returned, saving order to file')

                        if not TEST_MODE:
                            orders[coin] = extract_order_data(order_details)
                            #adding the price in USDT
                            volumeBuy = float(format(float(volume[coin]), '.6f'))
                            last_price_buy = float(format(orders[coin]['avgPrice'], '.3f'))
                            BuyUSDT = str(format(orders[coin]['volume'] * orders[coin]['avgPrice'], '.14f')).zfill(4)
                            #improving the presentation of the log file
                            coin = '{0:<9}'.format(coin)
                            buyFeeTotal1 = (volumeBuy * last_price_buy) * float(TRADING_FEE/100)
                            USED_BNB_IN_SESSION = USED_BNB_IN_SESSION + buyFeeTotal1
                                     #["Datetime",                                 "Type", "Coin", "Volume",              "Buy Price", "Amount of Buy", "Sell Price", "Amount of Sell", "Sell Reason", "Profit $"] "USDTdiff"])
                            write_log([datetime.now().strftime("%y-%m-%d %H:%M:%S"), "Buy", coin.replace(PAIR_WITH,""), round(float(volumeBuy),5), str(round(float(orders[coin]['avgPrice']),3)), str(round(float(BuyUSDT),3)) + " " + PAIR_WITH, 0, 0, "-", 0])
                        else:
                            #adding the price in USDT
                            BuyUSDT = volume[coin] * last_price[coin]['price']
                            volumeBuy = format(float(volume[coin]), '.6f')
                            last_price_buy = format(float(last_price[coin]['price']), '.3f')
                            BuyUSDT = str(format(BuyUSDT, '.14f')).zfill(4)
                            #improving the presentation of the log file
                            coin = '{0:<9}'.format(coin)
                            buyFeeTotal1 = (volumeBuy * last_price_buy) * float(TRADING_FEE/100)
                            USED_BNB_IN_SESSION = USED_BNB_IN_SESSION + buyFeeTotal1
                                    #(["Datetime", "Type", "Coin", "Volume", "Buy Price", "Sell Price", "Sell Reason", "Profit $"]) "USDTdiff"])
                            write_log([datetime.now().strftime("%y-%m-%d %H:%M:%S"), "Buy", coin.replace(PAIR_WITH,""), round(float(volumeBuy),5), str(round(float(last_price[coin]['price']),3)), str(round(float(BuyUSDT),3)) + " " + PAIR_WITH, 0, 0, "-", 0])
                        
                        write_signallsell(coin)

            else:
                print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Signal detected, but there is already an active trade on {coin}')
    except Exception as e:
        print(f'buy() exception: {e}')
        print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
    return orders, last_price, volume


def sell_coins(tpsl_override = False):
    '''sell coins that have reached the STOP LOSS or TAKE PROFIT threshold'''
    global hsp_head, session_profit_incfees_perc, session_profit_incfees_total, coin_order_id, trade_wins, trade_losses, historic_profit_incfees_perc, historic_profit_incfees_total, sell_all_coins, session_USDT_EARNED, TUP, TDOWN, TNEUTRAL, USED_BNB_IN_SESSION  
    externals = sell_external_signals()
 
    last_price = get_price(False) # don't populate rolling window
    #last_price = get_price(add_to_historical=True) # don't populate rolling window
    coins_sold = {}
    BUDGET = TRADE_TOTAL * TRADE_SLOTS
    try:
        for coin in list(coins_bought):
            LastPrice = float(last_price[coin]['price'])
            sellFee = (LastPrice * (TRADING_FEE/100))
            sellFeeTotal = (coins_bought[coin]['volume'] * LastPrice) * (TRADING_FEE/100)
            
            BuyPrice = float(coins_bought[coin]['bought_at'])
            buyFee = (BuyPrice * (TRADING_FEE/100))
            buyFeeTotal = (coins_bought[coin]['volume'] * BuyPrice) * (TRADING_FEE/100)
            
            PriceChange_Perc = float((LastPrice - BuyPrice) / BuyPrice * 100)
            #PriceChangeIncFees_Perc = float(((LastPrice+sellFee) - (BuyPrice+buyFee)) / (BuyPrice+buyFee) * 100)
            #PriceChangeIncFees_Unit = float((LastPrice+sellFee) - (BuyPrice+buyFee))
            PriceChangeIncFees_Perc = float(((LastPrice-sellFee) - (BuyPrice+buyFee)) / (BuyPrice+buyFee) * 100)
            PriceChangeIncFees_Unit = float((LastPrice-sellFee) - (BuyPrice+buyFee))

            # define stop loss and take profit
            TP = float(coins_bought[coin]['bought_at']) + ((float(coins_bought[coin]['bought_at']) * (coins_bought[coin]['take_profit']) / 100))
            SL = float(coins_bought[coin]['bought_at']) + ((float(coins_bought[coin]['bought_at']) * (coins_bought[coin]['stop_loss']) / 100))
            
            # check that the price is above the take profit and readjust SL and TP accordingly if trialing stop loss used
            
            if LastPrice > TP and USE_TRAILING_STOP_LOSS and not sell_all_coins and not tpsl_override:
                # increasing TP by TRAILING_TAKE_PROFIT (essentially next time to readjust SL)
                #add metod from OlorinSledge
                if PriceChange_Perc >= 0.8:
                    # price has changed by 0.8% or greater, a big change. Make the STOP LOSS trail closely to the TAKE PROFIT
                    # so you don't lose this increase in price if it falls back
                    coins_bought[coin]['take_profit'] = PriceChange_Perc + TRAILING_TAKE_PROFIT    
                    coins_bought[coin]['stop_loss'] = coins_bought[coin]['take_profit'] - TRAILING_STOP_LOSS

                else:
                    # price has changed by less than 0.8%, a small change. Make the STOP LOSS trail loosely to the TAKE PROFIT
                    # so you don't get stopped out of the trade prematurely
                    coins_bought[coin]['stop_loss'] = coins_bought[coin]['take_profit'] - TRAILING_STOP_LOSS
                    coins_bought[coin]['take_profit'] = PriceChange_Perc + TRAILING_TAKE_PROFIT

                # we've got a negative stop loss - not good, we don't want this.
                if coins_bought[coin]['stop_loss'] <= 0:
                    coins_bought[coin]['stop_loss'] = coins_bought[coin]['take_profit'] * .25

                # supress old metod
                #coins_bought[coin]['stop_loss'] = coins_bought[coin]['take_profit'] - TRAILING_STOP_LOSS
                #coins_bought[coin]['take_profit'] = PriceChange_Perc + TRAILING_TAKE_PROFIT
                # if DEBUG: print(f"{coin} TP reached, adjusting TP {coins_bought[coin]['take_profit']:.2f}  and SL {coins_bought[coin]['stop_loss']:.2f} accordingly to lock-in profit")
                #if DEBUG: print(f"{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}{coin} TP reached, adjusting TP {coins_bought[coin]['take_profit']:.{decimals()}f} and SL {coins_bought[coin]['stop_loss']:.{decimals()}f} accordingly to lock-in profit")
                if DEBUG: print(f"{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}{coin} TP reached, adjusting TP {str(round(TP,2))} and SL {str(round(SL,2))} accordingly to lock-in profit")
                continue
            # check that the price is below the stop loss or above take profit (if trailing stop loss not used) and sell if this is the case
            sellCoin = False
            sell_reason = ""
            if SELL_ON_SIGNAL_ONLY:
                # only sell if told to by external signal
                if coin in externals:
                    sellCoin = True
                    sell_reason = 'External Sell Signal'
            else:
                if LastPrice < SL: 
                    sellCoin = True
                    if USE_TRAILING_STOP_LOSS:
                        if PriceChange_Perc >= 0:
                            sell_reason = "TTP " #+ str(SL) + " reached"
                        else:
                            sell_reason = "TSL " #+ str(SL) + " reached"
                    else:
                        sell_reason = "SL "  #+ str(SL) + " reached"  
                    sell_reason = sell_reason + str(format(SL, ".18f")) + " reached"
                    #sell_reason = sell_reason + str(round(SL,2)) + " reached"
                if LastPrice > TP:
                    sellCoin = True
                    #sell_reason = "TP " + str(format(SL, ".18f")) + " reached"
                    sell_reason = "TP " + str(round(TP,2)) + " reached"
                if coin in externals:
                    sellCoin = True
                    sell_reason = 'External Sell Signal'
            
            if sell_all_coins:
                sellCoin = True
                sell_reason = 'Sell All Coins'
            if tpsl_override:
                sellCoin = True
                sell_reason = 'Session TPSL Override reached'

            if sellCoin:
                print(f"{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.SELL_PROFIT if PriceChangeIncFees_Perc >= 0. else txcolors.SELL_LOSS}Sell: {coins_bought[coin]['volume']} of {coin} | {sell_reason} | ${float(LastPrice):g} - ${float(BuyPrice):g} | Profit: {PriceChangeIncFees_Perc:.2f}% Est: {((float(coins_bought[coin]['volume'])*float(coins_bought[coin]['bought_at']))*PriceChangeIncFees_Perc)/100:.{decimals()}f} {PAIR_WITH} (Inc Fees) {PAIR_WITH} earned: {(float(coins_bought[coin]['volume'])*float(coins_bought[coin]['bought_at']))}{txcolors.DEFAULT}")
                
                msg1 = str(datetime.now()) + '| SELL: ' + coin + '. R:' +  sell_reason + ' P%:' + str(round(PriceChangeIncFees_Perc,2)) + ' P$:' + str(round(((float(coins_bought[coin]['volume'])*float(coins_bought[coin]['bought_at']))*PriceChangeIncFees_Perc)/100,4)) + ' ' + PAIR_WITH + ' earned:' + str(float(coins_bought[coin]['volume'])*float(coins_bought[coin]['bought_at']))
                msg_discord(msg1)

                # try to create a real order          
                try:
                    if not TEST_MODE:
                        #lot_size = coins_bought[coin]['step_size']
                        #if lot_size == 0:
                        #    lot_size = 1
                        #lot_size = lot_size.index('1') - 1
                        #if lot_size < 0:
                        #    lot_size = 0
                        
                        order_details = client.create_order(
                            symbol = coin,
                            side = 'SELL',
                            type = 'MARKET',
                            quantity = coins_bought[coin]['volume']
                        )

                # error handling here in case position cannot be placed
                except Exception as e:
                    #if repr(e).upper() == "APIERROR(CODE=-1111): PRECISION IS OVER THE MAXIMUM DEFINED FOR THIS ASSET.":
                    if not SCREEN_MODE == 2: print(f"{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}sell_coins() Exception occured on selling the coin! Coin: {coin}\nSell Volume coins_bought: {coins_bought[coin]['volume']}\nPrice:{LastPrice}\nException: {e}")

                # run the else block if coin has been sold and create a dict for each coin sold
                else:
                    if not TEST_MODE:
                        coins_sold[coin] = extract_order_data(order_details)
                        LastPrice = coins_sold[coin]['avgPrice']
                        sellFee = coins_sold[coin]['tradeFeeUnit']
                        coins_sold[coin]['orderid'] = coins_bought[coin]['orderid']
                        priceChange = float((LastPrice - BuyPrice) / BuyPrice * 100)

                        # update this from the actual Binance sale information
                        #PriceChangeIncFees_Unit = float((LastPrice+sellFee) - (BuyPrice+buyFee))
                        PriceChangeIncFees_Unit = float((LastPrice-sellFee) - (BuyPrice+buyFee))
                    else:
                        coins_sold[coin] = coins_bought[coin]

                    # prevent system from buying this coin for the next TIME_DIFFERENCE minutes
                    volatility_cooloff[coin] = datetime.now()
                    
                    time_held = (timedelta(seconds=datetime.now().timestamp()-int(str(coins_bought[coin]['timestamp'])[:10])).total_seconds())/3600
                    
                    if not int(MAX_HOLDING_TIME) == 0: 
                        if time_held >= int(MAX_HOLDING_TIME): set_exparis(coin)
                    
                    if DEBUG:
                        if not SCREEN_MODE == 2: print(f"{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}sell_coins() | Coin: {coin} | Sell Volume: {coins_bought[coin]['volume']} | Price:{LastPrice}")
                    
                    # Log trade
                    #BB profit = ((LastPrice - BuyPrice) * coins_sold[coin]['volume']) * (1-(buyFee + sellFeeTotal))                
                    profit_incfees_total = coins_sold[coin]['volume'] * PriceChangeIncFees_Unit
                    #write_log(f"Sell: {coins_sold[coin]['volume']} {coin} - {BuyPrice} - {LastPrice} Profit: {profit_incfees_total:.{decimals()}f} {PAIR_WITH} ({PriceChange_Perc:.2f}%)")
                    SellUSDT = coins_sold[coin]['volume'] * LastPrice
                    USDTdiff = SellUSDT - (BuyPrice * coins_sold[coin]['volume'])
                    session_USDT_EARNED = session_USDT_EARNED + USDTdiff
                    #improving the presentation of the log file
                    # it was padded with trailing zeros to give order to the table in the log file
                    VolumeSell = format(float(coins_sold[coin]['volume']), '.6f')
                    BuyPriceCoin = format(BuyPrice, '.8f')
                    SellUSDT = str(format(SellUSDT, '.14f')).zfill(4)
                    coin = '{0:<9}'.format(coin)
                    #BuyUSDT = (BuyPrice * coins_sold[coin]['volume']) 
                    #last_price[coin]['price']
                             #["Datetime",                                  "Type", "Coin", "Volume",                  "Buy Price",           "Amount of Buy", "Sell Price",    "Amount of Sell",                            "Sell Reason", "Profit $"] "USDTdiff"])
                    write_log([datetime.now().strftime("%y-%m-%d %H:%M:%S"), "Sell", coin.replace(PAIR_WITH,""), str(round(float(VolumeSell),5)), str(round(float(BuyPrice),2)), 0, str(round(float(LastPrice),2)), str(round(float(SellUSDT),2)) + " " + PAIR_WITH, sell_reason, str(round(float(USDTdiff),2)) + " " + PAIR_WITH])
                    
                    #this is good
                    session_profit_incfees_total = session_profit_incfees_total + profit_incfees_total
                    session_profit_incfees_perc = session_profit_incfees_perc + ((profit_incfees_total/BUDGET) * 100)
                    
                    historic_profit_incfees_total = historic_profit_incfees_total + profit_incfees_total
                    historic_profit_incfees_perc = historic_profit_incfees_perc + ((profit_incfees_total/BUDGET) * 100)
                    
                    #TRADE_TOTAL*PriceChangeIncFees_Perc)/100
                    
                    #if (LastPrice+sellFee) >= (BuyPrice+buyFee):
                    USED_BNB_IN_SESSION = USED_BNB_IN_SESSION + buyFeeTotal
                    #if IGNORE_FEE:
                    #    sellFee = 0
                    #    buyFee = 0
                    
                    #if (LastPrice-sellFee) >= (BuyPrice+buyFee):
                    #if USDTdiff > 0.:
                    if (LastPrice) >= (BuyPrice):
                        trade_wins += 1
                    else:
                        trade_losses += 1

                    update_bot_stats()
                    if not sell_all_coins:
                        # within sell_all_coins, it will print display to screen
                        balance_report(last_price)

                # sometimes get "rate limited" errors from Binance if we try to sell too many coins at once
                # so wait 1 second in between sells
                time.sleep(1)
                
                continue

            # no action; print once every TIME_DIFFERENCE
            if hsp_head == 1:
                if len(coins_bought) > 0:
                    #if not SCREEN_MODE == 2: print(f"Holding: {coins_bought[coin]['volume']} of {coin} | {LastPrice} - {BuyPrice} | Profit: {txcolors.SELL_PROFIT if PriceChangeIncFees_Perc >= 0. else txcolors.SELL_LOSS}{PriceChangeIncFees_Perc:.4f}% Est: ({(TRADE_TOTAL*PriceChangeIncFees_Perc)/100:.{decimals()}f} {PAIR_WITH}){txcolors.DEFAULT}")
                    if not SCREEN_MODE == 2: print(f"{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Holding: {coins_bought[coin]['volume']} of {coin} | {LastPrice} - {BuyPrice} | Profit: {txcolors.SELL_PROFIT if PriceChangeIncFees_Perc >= 0. else txcolors.SELL_LOSS}{PriceChangeIncFees_Perc:.4f}% Est: ({((float(coins_bought[coin]['volume'])*float(coins_bought[coin]['bought_at']))*PriceChangeIncFees_Perc)/100:.{decimals()}f} {PAIR_WITH}){txcolors.DEFAULT}")
                        
        #if hsp_head == 1 and len(coins_bought) == 0: if not SCREEN_MODE == 2: print(f"No trade slots are currently in use")

        # if tpsl_override: is_bot_running = False
    except Exception as e:
        print(f'{"sell_coins"}: Exception in function: {e}')
        print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
        pass
    except KeyboardInterrupt as ki:
        pass

    return coins_sold

def extract_order_data(order_details):
    global TRADING_FEE, STOP_LOSS, TAKE_PROFIT
    transactionInfo = {}
    # This code is from GoranJovic - thank you!
    #
    # adding order fill extractions here
    #
    # just to explain what I am doing here:
    # Market orders are not always filled at one price, we need to find the averages of all 'parts' (fills) of this order.
    #
    # reset other variables to 0 before use
    FILLS_TOTAL = 0
    FILLS_QTY = 0
    FILLS_FEE = 0
    BNB_WARNING = 0
    # loop through each 'fill':
    for fills in order_details['fills']:
        FILL_PRICE = float(fills['price'])
        FILL_QTY = float(fills['qty'])
        FILLS_FEE += float(fills['commission'])
        # check if the fee was in BNB. If not, log a nice warning:
        if (fills['commissionAsset'] != 'BNB') and (TRADING_FEE == 0.075) and (BNB_WARNING == 0):
            if not SCREEN_MODE == 2: print(f"WARNING: BNB not used for trading fee, please ")
            BNB_WARNING += 1
        # quantity of fills * price
        FILLS_TOTAL += (FILL_PRICE * FILL_QTY)
        # add to running total of fills quantity
        FILLS_QTY += FILL_QTY
        # increase fills array index by 1

    # calculate average fill price:
    FILL_AVG = (FILLS_TOTAL / FILLS_QTY)

    #tradeFeeApprox = (float(FILLS_QTY) * float(FILL_AVG)) * (TRADING_FEE/100)
    # Olorin Sledge: I only want fee at the unit level, not the total level
    tradeFeeApprox = float(FILL_AVG) * (TRADING_FEE/100)

    # the volume size is sometimes outside of precision, correct it
    try:
        info = client.get_symbol_info(order_details['symbol'])
        step_size = info['filters'][2]['stepSize']
        lot_size = step_size.index('1') - 1

        if lot_size <= 0:
            FILLS_QTY = int(FILLS_QTY)
        else:
            FILLS_QTY = truncate(FILLS_QTY, lot_size)
    except Exception as e:
        if not SCREEN_MODE == 2: print(f"extract_order_data(): Exception getting coin {order_details['symbol']} step size! Exception: {e}")
    
    # create object with received data from Binance
    transactionInfo = {
        'symbol': order_details['symbol'],
        'orderId': order_details['orderId'],
        'timestamp': order_details['transactTime'],
        'avgPrice': float(FILL_AVG),
        'volume': float(FILLS_QTY),
        'tradeFeeBNB': float(FILLS_FEE),
        'tradeFeeUnit': tradeFeeApprox,
    }
    return transactionInfo

def check_total_session_profit(coins_bought, last_price):
    global is_bot_running, session_tpsl_override_msg
    unrealised_session_profit_incfees_total = 0
    
    BUDGET = TRADE_SLOTS * TRADE_TOTAL
    
    for coin in list(coins_bought):
        LastPrice = float(last_price[coin]['price'])
        sellFee = (LastPrice * (TRADING_FEE/100))
        
        BuyPrice = float(coins_bought[coin]['bought_at'])
        buyFee = (BuyPrice * (TRADING_FEE/100))
        
        #PriceChangeIncFees_Total = float(((LastPrice+sellFee) - (BuyPrice+buyFee)) * coins_bought[coin]['volume'])
        PriceChangeIncFees_Total = float(((LastPrice-sellFee) - (BuyPrice+buyFee)) * coins_bought[coin]['volume'])

        unrealised_session_profit_incfees_total = float(unrealised_session_profit_incfees_total + PriceChangeIncFees_Total)

    allsession_profits_perc = session_profit_incfees_perc +  ((unrealised_session_profit_incfees_total / BUDGET) * 100)

    if DEBUG: print(f'Session Override SL Feature: ASPP={allsession_profits_perc} STP {SESSION_TAKE_PROFIT} SSL {SESSION_STOP_LOSS}')
    
    if allsession_profits_perc >= float(SESSION_TAKE_PROFIT): 
        session_tpsl_override_msg = "Session TP Override target of " + str(SESSION_TAKE_PROFIT) + "% met. Sell all coins now!"
        is_bot_running = False
    if allsession_profits_perc <= float(SESSION_STOP_LOSS):
        session_tpsl_override_msg = "Session SL Override target of " + str(SESSION_STOP_LOSS) + "% met. Sell all coins now!"
        is_bot_running = False   

def update_portfolio(orders, last_price, volume):
    '''add every coin bought to our portfolio for tracking/selling later'''

    #     print(orders)
    for coin in orders:
        try:
            coin_step_size = float(next(
                        filter(lambda f: f['filterType'] == 'LOT_SIZE', client.get_symbol_info(orders[coin][0]['symbol'])['filters'])
                        )['stepSize'])
        except Exception as ExStepSize:
            coin_step_size = .1


        if not TEST_MODE:
            coins_bought[coin] = {
               'symbol': orders[coin]['symbol'],
               'orderid': orders[coin]['orderId'],
               'timestamp': orders[coin]['timestamp'],
               'bought_at': orders[coin]['avgPrice'],
               'volume': orders[coin]['volume'],
               'volume_debug': volume[coin],
               'buyFeeBNB': orders[coin]['tradeFeeBNB'],
               'buyFee': orders[coin]['tradeFeeUnit'] * orders[coin]['volume'],
               'stop_loss': -STOP_LOSS,
               'take_profit': TAKE_PROFIT,
               'step_size': float(coin_step_size),
               }

            if not SCREEN_MODE == 2: print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Order for {orders[coin]["symbol"]} with ID {orders[coin]["orderId"]} placed and saved to file.')
        else:
            coins_bought[coin] = {
                'symbol': orders[coin][0]['symbol'],
                'orderid': orders[coin][0]['orderId'],
                'timestamp': orders[coin][0]['time'],
                'bought_at': last_price[coin]['price'],
                'volume': volume[coin],
                'stop_loss': -STOP_LOSS,
                'take_profit': TAKE_PROFIT,
                'step_size': float(coin_step_size),
                }

            if not SCREEN_MODE == 2: print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Order for {orders[coin][0]["symbol"]} with ID {orders[coin][0]["orderId"]} placed and saved to file.')

        # save the coins in a json file in the same directory
        with open(coins_bought_file_path, 'w') as file:
            json.dump(coins_bought, file, indent=4)

def update_bot_stats():
    global trade_wins, trade_losses, historic_profit_incfees_perc, historic_profit_incfees_total, session_USDT_EARNED, USED_BNB_IN_SESSION

    bot_stats = {
        'total_capital' : str(TRADE_SLOTS * TRADE_TOTAL),
        'botstart_datetime' : str(bot_started_datetime),
        'historicProfitIncFees_Percent': historic_profit_incfees_perc,
        'historicProfitIncFees_Total': format(historic_profit_incfees_total, ".14f"),
        'tradeWins': trade_wins,
        'tradeLosses': trade_losses,
        'session_'+ PAIR_WITH + '_EARNED': format(session_USDT_EARNED, ".14f"),
        'used_bnb_in_session': USED_BNB_IN_SESSION,
    }

    #save session info for through session portability
    with open(bot_stats_file_path, 'w') as file:
        json.dump(bot_stats, file, indent=4)


def remove_from_portfolio(coins_sold):
    '''Remove coins sold due to SL or TP from portfolio'''
    for coin in coins_sold:
        # code below created by getsec <3
        coins_bought.pop(coin)
    with open(coins_bought_file_path, 'w') as file:
        json.dump(coins_bought, file, indent=4)
    if os.path.exists('signalsell_tickers.txt'):
        os.remove('signalsell_tickers.txt')
        for coin in coins_bought:
            write_signallsell(coin.removesuffix(PAIR_WITH))
    
def write_signallsell(symbol):
    with open('signalsell_tickers.txt','a+') as f:
        f.write(f'{symbol}\n')

def remove_external_signals(fileext):
    signals = glob.glob('signals/*.{fileext}')
    for filename in signals:
        for line in open(filename):
            try:
                os.remove(filename)
            except:
                if DEBUG: print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.WARNING}Could not remove external signalling file {filename}{txcolors.DEFAULT}')

def sell_all(msgreason, session_tspl_ovr = False):
    global sell_all_coins

    msg_discord(f'{str(datetime.now())} | SELL ALL COINS: {msgreason}')

    # stop external signals so no buying/selling/pausing etc can occur
    stop_signal_threads()

    # sell all coins NOW!
    sell_all_coins = True

    coins_sold = sell_coins(session_tspl_ovr)
    remove_from_portfolio(coins_sold)
    
    # display final info to screen
    last_price = get_price()
    discordmsg = balance_report(last_price)
    msg_discord(discordmsg)
	
def load_signal_threads():
 # load signalling modules
    global signalthreads
    signalthreads = []
    try:
        if SIGNALLING_MODULES is not None: 
            if len(SIGNALLING_MODULES) > 0:
                for module in SIGNALLING_MODULES:
                    print(f'Starting {module}')
                    mymodule[module] = importlib.import_module(module)
                    # t = threading.Thread(target=mymodule[module].do_work, args=())
                    t = multiprocessing.Process(target=mymodule[module].do_work, args=())
                    t.name = module
                    t.daemon = True
                    t.start()

                    # add process to a list. This is so the thread can be terminated at a later time
                    signalthreads.append(t)

                    time.sleep(2)
            else:
                print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}No modules to load {SIGNALLING_MODULES}')
    except Exception as e:
        print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT} load_signal_threads: Loading external signals exception: {e}')
        print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))

def stop_signal_threads():
    global signalthreads
    try:
        for signalthread in signalthreads:
            print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Terminating thread {str(signalthread.name)}')
            signalthread.terminate()
    except Exception as e:
        print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}{"stop_signal_threads"}: Exception in function: {e}')
        pass
    except KeyboardInterrupt as ki:
        pass

def truncate(number, decimals=0):
    """
    Returns a value truncated to a specific number of decimal places.
    Better than rounding
    """
    if not isinstance(decimals, int):
        raise TypeError("decimal places must be an integer.")
    elif decimals < 0:
        raise ValueError("decimal places has to be 0 or more.")
    elif decimals == 0:
        return math.trunc(number)

    factor = 10.0 ** decimals
    return math.trunc(number * factor) / factor

def load_settings():
    # set to false at Start
    global bot_paused, parsed_config, creds_file, access_key, secret_key, parsed_creds
    bot_paused = False

    DEFAULT_CONFIG_FILE = 'config.yml'
    DEFAULT_CREDS_FILE = 'creds.yml'

    config_file = args.config if args.config else DEFAULT_CONFIG_FILE
    creds_file = args.creds if args.creds else DEFAULT_CREDS_FILE
    parsed_config = load_config(config_file)
    parsed_creds = load_config(creds_file)

    # Default no debugging
    global DEBUG, TEST_MODE, LOG_TRADES, LOG_FILE, DEBUG_SETTING, AMERICAN_USER, PAIR_WITH, QUANTITY, MAX_COINS, FIATS, TIME_DIFFERENCE, RECHECK_INTERVAL, CHANGE_IN_PRICE, STOP_LOSS, TAKE_PROFIT, CUSTOM_LIST, TICKERS_LIST, USE_TRAILING_STOP_LOSS, TRAILING_STOP_LOSS, TRAILING_TAKE_PROFIT, TRADING_FEE, SIGNALLING_MODULES, SCREEN_MODE, MSG_DISCORD, HISTORY_LOG_FILE, TRADE_SLOTS, TRADE_TOTAL, SESSION_TPSL_OVERRIDE, SELL_ON_SIGNAL_ONLY, TRADING_FEE, SIGNALLING_MODULES, SHOW_INITIAL_CONFIG, USE_MOST_VOLUME_COINS, COINS_MAX_VOLUME, COINS_MIN_VOLUME, DISABLE_TIMESTAMPS, STATIC_MAIN_INFO, COINS_BOUGHT, BOT_STATS, MAIN_FILES_PATH, PRINT_TO_FILE, ENABLE_PRINT_TO_FILE, EX_PAIRS, RESTART_MODULES, SHOW_TABLE_COINS_BOUGHT, ALWAYS_OVERWRITE, SORT_TABLE_BY, REVERSE_SORT, MAX_HOLDING_TIME, IGNORE_FEE, EXTERNAL_COINS, PROXY_HTTP, PROXY_HTTPS, SIGNALLING_MODULES

    # Default no debugging
    DEBUG = False

    # Load system vars
    TEST_MODE = parsed_config['script_options']['TEST_MODE']
    #     LOG_TRADES = parsed_config['script_options'].get('LOG_TRADES')
    MAIN_FILES_PATH = parsed_config['script_options'].get('MAIN_FILES_PATH')
    LOG_FILE = parsed_config['script_options'].get('LOG_FILE')
    HISTORY_LOG_FILE = parsed_config['script_options'].get('HISTORY_LOG_FILE')
    #HISTORY_LOG_FILE = "history.html"
    COINS_BOUGHT = parsed_config['script_options'].get('COINS_BOUGHT')
    BOT_STATS = parsed_config['script_options'].get('BOT_STATS')
    DEBUG_SETTING = parsed_config['script_options'].get('DEBUG')
    AMERICAN_USER = parsed_config['script_options'].get('AMERICAN_USER')
    EXTERNAL_COINS = parsed_config['script_options']['EXTERNAL_COINS']

    # Load trading vars
    PAIR_WITH = parsed_config['trading_options']['PAIR_WITH']
    TRADE_TOTAL = parsed_config['trading_options']['TRADE_TOTAL']
    TRADE_SLOTS = parsed_config['trading_options']['TRADE_SLOTS']
    #FIATS = parsed_config['trading_options']['FIATS']
    EX_PAIRS = parsed_config['trading_options']['EX_PAIRS']
    
    TIME_DIFFERENCE = parsed_config['trading_options']['TIME_DIFFERENCE']
    RECHECK_INTERVAL = parsed_config['trading_options']['RECHECK_INTERVAL']
    
    CHANGE_IN_PRICE = parsed_config['trading_options']['CHANGE_IN_PRICE']
    STOP_LOSS = parsed_config['trading_options']['STOP_LOSS']
    TAKE_PROFIT = parsed_config['trading_options']['TAKE_PROFIT']
    
    #COOLOFF_PERIOD = parsed_config['trading_options']['COOLOFF_PERIOD']

    CUSTOM_LIST = parsed_config['trading_options']['CUSTOM_LIST']
    TICKERS_LIST = parsed_config['trading_options']['TICKERS_LIST']
    
    USE_TRAILING_STOP_LOSS = parsed_config['trading_options']['USE_TRAILING_STOP_LOSS']
    TRAILING_STOP_LOSS = parsed_config['trading_options']['TRAILING_STOP_LOSS']
    TRAILING_TAKE_PROFIT = parsed_config['trading_options']['TRAILING_TAKE_PROFIT']
     
    # Code modified from DJCommie fork
    # Load Session OVERRIDE values - used to STOP the bot when current session meets a certain STP or SSL value
    SESSION_TPSL_OVERRIDE = parsed_config['trading_options']['SESSION_TPSL_OVERRIDE']
    SESSION_TAKE_PROFIT = parsed_config['trading_options']['SESSION_TAKE_PROFIT']
    SESSION_STOP_LOSS = parsed_config['trading_options']['SESSION_STOP_LOSS']

    # Borrowed from DJCommie fork
    # If TRUE, coin will only sell based on an external SELL signal
    SELL_ON_SIGNAL_ONLY = parsed_config['trading_options']['SELL_ON_SIGNAL_ONLY']

    # Discord integration
    # Used to push alerts, messages etc to a discord channel
    MSG_DISCORD = parsed_config['trading_options']['MSG_DISCORD']
    
    # Functionality to "reset / restart" external signal modules(code os OlorinSledge)
    RESTART_MODULES = parsed_config['trading_options']['RESTART_MODULES']
    
	#minimal mode
    SCREEN_MODE = parsed_config['trading_options']['SCREEN_MODE']
    STATIC_MAIN_INFO = parsed_config['trading_options']['STATIC_MAIN_INFO']
    DISABLE_TIMESTAMPS = parsed_config['trading_options']['DISABLE_TIMESTAMPS']
    #PRINT_TO_FILE = parsed_config['trading_options']['PRINT_TO_FILE']
    #ENABLE_PRINT_TO_FILE = parsed_config['trading_options']['ENABLE_PRINT_TO_FILE']
    TRADING_FEE = parsed_config['trading_options']['TRADING_FEE']
    SIGNALLING_MODULES = parsed_config['trading_options']['SIGNALLING_MODULES']
	
    SHOW_INITIAL_CONFIG = parsed_config['trading_options']['SHOW_INITIAL_CONFIG']
    SHOW_TABLE_COINS_BOUGHT = parsed_config['trading_options']['SHOW_TABLE_COINS_BOUGHT']

    USE_MOST_VOLUME_COINS = parsed_config['trading_options']['USE_MOST_VOLUME_COINS']
    COINS_MAX_VOLUME = parsed_config['trading_options']['COINS_MAX_VOLUME']
    COINS_MIN_VOLUME = parsed_config['trading_options']['COINS_MIN_VOLUME']
    ALWAYS_OVERWRITE = parsed_config['trading_options']['ALWAYS_OVERWRITE']
    
    SORT_TABLE_BY = parsed_config['trading_options']['SORT_TABLE_BY']
    REVERSE_SORT = parsed_config['trading_options']['REVERSE_SORT']
    
    MAX_HOLDING_TIME = parsed_config['trading_options']['MAX_HOLDING_TIME']
    
    IGNORE_FEE = parsed_config['trading_options']['IGNORE_FEE']
    
    PROXY_HTTP = parsed_config['script_options']['PROXY_HTTP']
    PROXY_HTTPS = parsed_config['script_options']['PROXY_HTTPS']
	
    #BNB_FEE = parsed_config['trading_options']['BNB_FEE']
    #TRADING_OTHER_FEE = parsed_config['trading_options']['TRADING_OTHER_FEE']

    if DEBUG_SETTING or args.debug:
        DEBUG = True
    access_key, secret_key = load_correct_creds(parsed_creds)

def renew_list():
    global tickers, VOLATILE_VOLUME_LIST, FLAG_PAUSE, COINS_MAX_VOLUME, COINS_MIN_VOLUME
    try:
        if USE_MOST_VOLUME_COINS == True:
            if VOLATILE_VOLUME_LIST == "volatile_volume_" + str(date.today()) + ".txt" and os.path.exists(VOLATILE_VOLUME_LIST) == True:
                tickers=[line.strip() for line in open(VOLATILE_VOLUME_LIST)]                
            else:
                print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}A new Volatily Volume list will be created...')
                stop_signal_threads()
                FLAG_PAUSE = True
                if TEST_MODE == True:
                    jsonfile = "test_" + COINS_BOUGHT
                else: 
                    jsonfile = "live_" + COINS_BOUGHT
                    
                with open(jsonfile,'r') as f:
                    coins_bought_list = json.load(f)
                    
                coinstosave = []
                
                for coin in coins_bought_list:
                    coinstosave.append(coin.replace(PAIR_WITH,"") + "\n")
                    
                VOLATILE_VOLUME_LIST = get_volume_list()
                with open(VOLATILE_VOLUME_LIST,'r') as f:
                    lines = f.readlines()
                    
                for c in coinstosave:
                    for l in lines:
                        if c == l:
                            break
                        else:
                            lines.append(c)
                            break
                            
                with open(VOLATILE_VOLUME_LIST,'w') as f:
                    f.writelines(lines)
                    
                print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}A new Volatily Volume list has been created...')
                FLAG_PAUSE = False
                #renew_list()
                load_signal_threads()     
                    
        else:
            tickers=[line.strip() for line in open(TICKERS_LIST)]
    except Exception as e:
        print(f'{"renew_list"}: Exception in function: {e}')
        print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
        pass
    

def new_or_continue():
    if TEST_MODE:
        file_prefix = 'test_'
    else:
        file_prefix = 'live_'      
    
    if os.path.exists(file_prefix + str(COINS_BOUGHT)) or os.path.exists(file_prefix + str(BOT_STATS)):
        LOOP = True
        END = False
        while LOOP:
            if ALWAYS_OVERWRITE == False:
                print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Use previous session exists, do you want to continue it? Otherwise a new session will be created.')
                x = input('y/n: ')
            else:
                x = "n"
            if x == "y" or x == "n":
                if x == "y":
                    print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Continuing with the session started ...')
                    LOOP = False
                    END = True
                else:
                    print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Deleting previous sessions ...')
                    if os.path.exists(file_prefix + COINS_BOUGHT): os.remove(file_prefix + COINS_BOUGHT)
                    if os.path.exists(file_prefix + BOT_STATS): os.remove(file_prefix + BOT_STATS)
                    if os.path.exists(EXTERNAL_COINS): os.remove(EXTERNAL_COINS)
                    if os.path.exists(file_prefix + LOG_FILE): os.remove(file_prefix + LOG_FILE)
                    if os.path.exists(file_prefix + HISTORY_LOG_FILE): os.remove(file_prefix + HISTORY_LOG_FILE)
                    if os.path.exists(EXTERNAL_COINS): os.remove(EXTERNAL_COINS)
                    print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Session deleted, continuing ...')
                    LOOP = False
                    END = True
            else:
                print(f'Press the y key or the or key ...')
                LOOP = True
        return END
		
		
def menu():
    try:
        global COINS_MAX_VOLUME, COINS_MIN_VOLUME
        global SCREEN_MODE, PAUSEBOT_MANUAL
        END = False
        LOOP = True
        stop_signal_threads()
        while LOOP:
            time.sleep(5)
            print(f'')
            print(f'')
            print(f'[1]Reload Configuration{txcolors.DEFAULT}')
            print(f'[2]Reload modules{txcolors.DEFAULT}')
            print(f'[3]Reload Volatily Volume List{txcolors.DEFAULT}')
            if PAUSEBOT_MANUAL == False: 
                print(f'[4]Stop Purchases{txcolors.DEFAULT}')
            else:
                print(f'[4]Start Purchases{txcolors.DEFAULT}')
            print(f'[5]Exit BOT{txcolors.DEFAULT}')
            x = input('Please enter your choice: ')
            x = int(x)
            print(f'')
            print(f'')
            if x == 1:
                load_settings()
                #print(f'TICKERS_LIST(menu): ' + TICKERS_LIST)
                renew_list()
                LOOP = False
                load_signal_threads()
                print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.WARNING}Reaload Completed{txcolors.DEFAULT}')
            elif x == 2:
                stop_signal_threads()
                load_signal_threads()
                print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.WARNING}Modules Realoaded Completed{txcolors.DEFAULT}')
                LOOP = False
            elif x == 3:
                stop_signal_threads()
                #load_signal_threads()
                global VOLATILE_VOLUME_LIST
                if USE_MOST_VOLUME_COINS == True:
                    os.remove(VOLATILE_VOLUME_LIST)
                    VOLATILE_VOLUME_LIST = get_volume_list()
                    renew_list()
                else:
                    print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.WARNING}USE_MOST_VOLUME_COINS must be true in config.yml{txcolors.DEFAULT}')
                    LOOP = False
                print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.WARNING}VOLATILE_VOLUME_LIST Realoaded Completed{txcolors.DEFAULT}')
                LOOP = False
            elif x == 4:
                if PAUSEBOT_MANUAL == False:
                    PAUSEBOT_MANUAL = True
                    LOOP = False
                else:
                    PAUSEBOT_MANUAL = False
                    LOOP = False
            elif x == 5:
                # stop external signal threads
                stop_signal_threads()
                # ask user if they want to sell all coins
                print(f'\n\n\n')
                sellall = input(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.WARNING}Program execution ended by user!\n\nDo you want to sell all coins (y/N)?{txcolors.DEFAULT}')
                if sellall.upper() == "Y":
                    # sell all coins
                    sell_all('Program execution ended by user!')
                    END = True
                    LOOP = False
                else:
                    END = True
                    LOOP = False
            else:
                print(f'wrong choice')
                LOOP = True
    except Exception as e:
        print(f'Exception in menu() 1: {e}')
        print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
        pass
    except KeyboardInterrupt as ki:
        menu()
    return END
	
if __name__ == '__main__':
    req_version = (3,9)
    if sys.version_info[:2] < req_version: 
        print(f'This bot requires Python version 3.9 or higher/newer. You are running version {sys.version_info[:2]} - please upgrade your Python version!!')
        sys.exit()
		# Load arguments then parse settings
    args = parse_args()
    mymodule = {}
    print(f'')
    print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Initializing, wait a moment...')
    discord_msg_balance_data = ""
    last_msg_discord_balance_date = datetime.now()
    last_history_log_date = datetime.now()
	
    load_settings()
	
    if DISABLE_TIMESTAMPS == False:
        # print with timestamps
        old_out = sys.stdout
        class St_ampe_dOut:
            """Stamped stdout."""
            nl = True
            def write(self, x):
                """Write function overloaded."""
                if x == '\n':
                    old_out.write(x)
                    self.nl = True
                elif self.nl:
                    old_out.write(f'{txcolors.DIM}[{str(datetime.now().replace(microsecond=0))}]{txcolors.DEFAULT} {x}')
                    self.nl = False
                else:
                    old_out.write(x)

            def flush(self):
                pass

        sys.stdout = St_ampe_dOut()
			
    # Load creds for correct environment
    if DEBUG:
        if SHOW_INITIAL_CONFIG == True: print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Loaded config below\n{json.dumps(parsed_config, indent=4)}')
        if SHOW_INITIAL_CONFIG == True: print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Your credentials have been loaded from {creds_file}')
		
    if MSG_DISCORD:
        DISCORD_WEBHOOK = load_discord_creds(parsed_creds)
		
    if MSG_DISCORD:
        MSG_DISCORD = True

    sell_all_coins = False

    # Authenticate with the client, Ensure API key is good before continuing
    if AMERICAN_USER:
        if PROXY_HTTP != '' or PROXY_HTTPS != '': 
            print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT} Using proxy ...')
            proxies = {
                    'http': PROXY_HTTP,
                    'https': PROXY_HTTPS
            }
            client = Client(access_key, secret_key, {'proxies': proxies}, tld='us')
        else:
            client = Client(access_key, secret_key, tld='us')
    else:
        if PROXY_HTTP != '' or PROXY_HTTPS != '': 
            print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT} Using proxy ...')
            proxies = {
                    'http': PROXY_HTTP,
                    'https': PROXY_HTTPS
            }
            client = Client(access_key, secret_key, {'proxies': proxies})
        else:
            client = Client(access_key, secret_key)

    # If the users has a bad / incorrect API key.
    # this will stop the script from starting, and display a helpful error.
    api_ready, msg = test_api_key(client, BinanceAPIException)
    if api_ready is not True:
        exit(f'{txcolors.SELL_LOSS}{msg}{txcolors.DEFAULT}')
        
    global VOLATILE_VOLUME_LIST
    if USE_MOST_VOLUME_COINS == True: VOLATILE_VOLUME_LIST = get_volume_list()
    renew_list()

    new_or_continue()

    # try to load all the coins bought by the bot if the file exists and is not empty
    coins_bought = {}

    if TEST_MODE:
        file_prefix = 'test_'
    else:
        file_prefix = 'live_'

    # path to the saved coins_bought file
    coins_bought_file_path = file_prefix + COINS_BOUGHT

    # The below mod was stolen and altered from GoGo's fork, a nice addition for keeping a historical history of profit across multiple bot sessions.
    # path to the saved bot_stats file
    bot_stats_file_path = file_prefix + BOT_STATS

    # use separate files for testing and live trading
    #LOG_FILE = file_prefix + LOG_FILE
    #HISTORY_LOG_FILE = file_prefix + HISTORY_LOG_FILE

    bot_started_datetime = datetime.now()
    total_capital_config = TRADE_SLOTS * TRADE_TOTAL

    if os.path.isfile(bot_stats_file_path) and os.stat(bot_stats_file_path).st_size!= 0:
        with open(bot_stats_file_path) as file:
            bot_stats = json.load(file)
            # load bot stats:
            try:
                bot_started_datetime = datetime.strptime(bot_stats['botstart_datetime'], '%Y-%m-%d %H:%M:%S.%f')
            except Exception as e:
                print (f'Exception on reading botstart_datetime from {bot_stats_file_path}. Exception: {e}')   
                bot_started_datetime = datetime.now()
            
            try:
                total_capital = bot_stats['total_capital']
            except Exception as e:
                print (f'Exception on reading total_capital from {bot_stats_file_path}. Exception: {e}')   
                total_capital = TRADE_SLOTS * TRADE_TOTAL

            historic_profit_incfees_perc = float(bot_stats['historicProfitIncFees_Percent'])
            historic_profit_incfees_total = float(bot_stats['historicProfitIncFees_Total'])
            trade_wins = bot_stats['tradeWins']
            trade_losses = bot_stats['tradeLosses']
            session_USDT_EARNED = float(bot_stats['session_' + PAIR_WITH + '_EARNED'])

            if total_capital != total_capital_config:
                historic_profit_incfees_perc = (historic_profit_incfees_total / total_capital_config) * 100

    # rolling window of prices; cyclical queue
    historical_prices = [None] * (TIME_DIFFERENCE * RECHECK_INTERVAL)
    hsp_head = -1

    # prevent including a coin in volatile_coins if it has already appeared there less than TIME_DIFFERENCE minutes ago
    volatility_cooloff = {}

    # if saved coins_bought json file exists and it's not empty then load it
    if os.path.isfile(coins_bought_file_path) and os.stat(coins_bought_file_path).st_size!= 0:
        with open(coins_bought_file_path) as file:
                coins_bought = json.load(file)

    print('Press Ctrl-C to stop the script')

    if not TEST_MODE:
        if not args.notimeout: # if notimeout skip this (fast for dev tests)
            print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}WARNING: Test mode is disabled in the configuration, you are using _LIVE_ funds.')
            print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}WARNING: Waiting 10 seconds before live trading as a security measure!')
            time.sleep(0)

    remove_external_signals('buy')
    remove_external_signals('sell')
    remove_external_signals('pause')

    #load_signal_threads()
    load_signal_threads()

    # seed initial prices
    get_price()
    TIMEOUT_COUNT=0
    READ_CONNECTERR_COUNT=0
    BINANCE_API_EXCEPTION=0	
    
    #extract of code of OlorinSledge, Thanks
    thehour = datetime.now().hour  
    
    while is_bot_running:
        try:
            orders, last_price, volume = buy()
            update_portfolio(orders, last_price, volume)
            
            if SESSION_TPSL_OVERRIDE:
                check_total_session_profit(coins_bought, last_price)
                
            coins_sold = sell_coins()
            remove_from_portfolio(coins_sold)
            update_bot_stats()
            
            if FLAG_PAUSE == False:
                #extract of code of OlorinSledge, Thanks
                if RESTART_MODULES and thehour != datetime.now().hour :
                    stop_signal_threads()
                    load_signal_threads()
                    thehour = datetime.now().hour
                    print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.WARNING}Modules Realoaded Completed{txcolors.DEFAULT}')
        except ReadTimeout as rt:
            TIMEOUT_COUNT += 1
            print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}We got a timeout error from Binance. Re-loop. Connection Timeouts so far: {TIMEOUT_COUNT}')
        except ConnectionError as ce:
            READ_CONNECTERR_COUNT += 1
            print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}We got a connection error from Binance. Re-loop. Connection Errors so far: {READ_CONNECTERR_COUNT}')
        except BinanceAPIException as bapie:
            BINANCE_API_EXCEPTION += 1
            print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}We got an API error from Binance. Re-loop. API Errors so far: {BINANCE_API_EXCEPTION}.\nException:\n{bapie}')											
        except KeyboardInterrupt as ki:
            if menu() == True: sys.exit(0)

    if not is_bot_running:
        if SESSION_TPSL_OVERRIDE:
            print(f'')
            print(f'')
            print(f'{txcolors.WARNING}{session_tpsl_override_msg}{txcolors.DEFAULT}')            
            sell_all(session_tpsl_override_msg, True)
            sys.exit(0)

        else:
            print(f'')
            print(f'')
            print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Bot terminated for some reason.')