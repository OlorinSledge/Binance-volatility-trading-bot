"""
Olorin Sledge Fork
Version: 1.29

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

!! IMPORTANT INFORMATION ABOUT EXTERNAL SIGNAL MODULES !!
    Please note this very important difference. If you use any external signals, they need to be modified as follows:
    1) If it is a buy signal, you need to replace .exs with .buy so it creates a signals/whatever.buy (where "whatever" is anything you want)
    2) If it is a sell signal, you need to replace .exs with .sell so it creates a signals/whatever.sell (where "whatever" is anything you want)
    3) If it is a pausebot signal, you need to create a signals/pausebot.pause file
    All these changes are within the external signal itself and is really easy to do via Find/Replace (advice you manually review any replace you do).

FUNCTIONALITY
- Changed way profit % is calculated to be based on ROI
- More details provided on screen on state of bot (i.e.  unrealised session profit, session profit, all time profit, bot paused or not etc)
- Totally reworked external signals. NOTE: you CANNOT use the default signals anymore with my bot unless you modify them to work with it
- Sell all coins on stopping bot functionality
- Stop bot on session profit / session stop loss trigger
- Only sell based on an external signal i.e. Stop Loss and Take Profit are ignored
- Discord support
- Better reporting in trades.txt
- A history.txt that records state of bot every minute (useful for past analysis /charting)
- Better error trapping on certain exceptions
- BNB is no longer used as the reference for TIME_DIFFERENCE, this allows one to not have it in their tickers.txt list.
- Tickers list can now auto reload (if set in the config.yml file)
- Held coins displayed in a Table format
- Market profit vs Bot profit comparison
- Restart an external signal every hour
- Sell a specific coin on stopping bot funciton
- Bot can reinvest any profits from coins sold so as to compound your profits. Please note, this will also compound any losses so use with care.
  Configurable in configy.yml with REINVEST_PROFITS flag.

Added version 1.20:
- Has a "Market Profit". This is a comparison between your bots profits and if you had just bought BTC instead when you started your bot.
     Please note: If your bot has already been running for a period of time, you will need to manually modify your bots_stat.json and update
     the "market_startprice" variable. This needs to be the price of BTC when your bot originally started.

Added version 1.21:
- Ability to "restart" an external signal via the RESTART_EXTSIGNALS setting. Please only use this is you know what you are doing. 99% of the time
      you will want this to be False

Added version 1.25:
- "BUYING MODE" added to summary info so you can easily tell if you are in Test mode or Live mode
- "External Signals" added to summary info so you can tell which external signals you have running

Added version 1.26:
- "Sell A Specific Coin" feature enhancement added. When you end the bot, it gives you the option to sell a specific coin.
  1. The bot will display the coins you can sell in a table
  2. Type in the SYMBOL including the pair and the bot will sell it.
  3. It will loop 1 to 2 until you choose N
  4. Bot ends

Added version 1.27
- Menu system on stopping (CTRL+C) the bot for options to: Exit bot, sell all coins, sell specific coin, resume bot

Added version 1.28
- Reinvest profits, and losses, to compound capital

DONATIONS
If you feel you would like to donate to me, for all the above improvements, I would greatly appreciate it. Please see donation options below.

Bitcoin (BTC network): 1DMRzMWXRXLeTQ9mfN9uvMTeJHmkkG5oS8
Etherium (ERC-20 network): 0x69566c866817c593d8a40a1b672afa3b7cfd69bf
Matic (Polygon network): 0x69566c866817c593d8a40a1b672afa3b7cfd69bf
BNB (BEP20 network): 0x69566c866817c593d8a40a1b672afa3b7cfd69bf
Fantom (FTM network): 0x69566c866817c593d8a40a1b672afa3b7cfd69bf
Algo (Algorand network): ML72MOJ7N3O4G4EGDLKICNOCMIBCH4U5I34WCXZ4B4HREPBA3ME7BOYPB4
Nano (Nano network): nano_1en6m9rx9wgwqu5e1otedzprpgjbnrjs43gi9g94r5nu31ikc1heytt8qd74

ORIGINAL BOT CREATOR
This bot was forked from the original creation by CyberPunkMetalHead.
You can find his repository of projects at https://github.com/CyberPunkMetalHead.
You can find details to donate to him at his website, https://www.cryptomaton.org.

"""

# use for environment variables
import os

# use if needed to pass args to external modules
import sys

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

# used to display holding coins in an ascii table
from prettytable import PrettyTable

# Load helper modules
from helpers.parameters import (
    parse_args, load_config
)

# Load creds modules
from helpers.handle_creds import (
    load_correct_creds, test_api_key,
    load_discord_creds
)

# my helper utils
from helpers.os_utils import(rchop)

# for colourful logging to the console
class txcolors:
    BUY = '\033[92m'
    WARNING = '\033[93m'
    SELL_LOSS = '\033[91m'
    SELL_PROFIT = '\033[32m'
    DIM = '\033[2m\033[35m'
    DEFAULT = '\033[39m'
    YELLOW = '\033[33m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    ENDC = '\033[0m'

# tracks profit/loss each session
global session_profit_incfees_perc, session_profit_incfees_total, session_tpsl_override_msg, is_bot_running
session_profit_incfees_perc = 0
session_profit_incfees_total = 0
session_tpsl_override_msg = ""
is_bot_running = True

global historic_profit_incfees_perc, historic_profit_incfees_total, trade_wins, trade_losses
global sell_all_coins, bot_started_datetime, market_startprice, market_currprice, sell_specific_coin

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
market_startprice = 0

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

def is_fiat():
    # check if we are using a fiat as a base currency
    global hsp_head
    PAIR_WITH = parsed_config['trading_options']['PAIR_WITH']
    #list below is in the order that Binance displays them, apologies for not using ASC order
    fiats = ['USDT', 'BUSD', 'AUD', 'BRL', 'EUR', 'GBP', 'RUB', 'TRY', 'TUSD', 'USDC', 'PAX', 'BIDR', 'DAI', 'IDRT', 'UAH', 'NGN', 'VAI', 'BVND']

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

def print_table(table):
    global old_out

    print('')
    sys.stdout = old_out
    print(table)
    sys.stdout = St_ampe_dOut()

def print_notimestamp(msg):
    global old_out

    sys.stdout = old_out
    print(msg, end = ' ')
    sys.stdout = St_ampe_dOut()

def get_price(add_to_historical=True):
    '''Return the current price for all coins on binance'''

    global historical_prices, hsp_head, market_startprice, market_currprice

    initial_price = {}
    prices = client.get_all_tickers()

    for coin in prices:
        
        if coin['symbol'] == "BTCUSDT":
            if market_startprice == 0:
                market_startprice = float(coin['price'])
            market_currprice = float(coin['price'])

        if CUSTOM_LIST:
            if any(item + PAIR_WITH == coin['symbol'] for item in tickers) and all(item not in coin['symbol'] for item in FIATS):
                initial_price[coin['symbol']] = { 'price': coin['price'], 'time': datetime.now()}
        else:
            if PAIR_WITH in coin['symbol'] and all(item not in coin['symbol'] for item in FIATS):
                initial_price[coin['symbol']] = { 'price': coin['price'], 'time': datetime.now()}

    if add_to_historical:
        hsp_head += 1

        if hsp_head == RECHECK_INTERVAL:
            hsp_head = 0

        historical_prices[hsp_head] = initial_price

    return initial_price


def wait_for_price():
    '''calls the initial price and ensures the correct amount of time has passed
    before reading the current price again'''

    global historical_prices, hsp_head, volatility_cooloff

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
    #last_price = get_price()
    last_price = wrap_get_price()

    # calculate the difference in prices
    for coin in historical_prices[hsp_head]:
           
        # minimum and maximum prices over time period
        try:
            min_price = min(historical_prices, key = lambda x: float("inf") if x is None else float(x[coin]['price']))
            max_price = max(historical_prices, key = lambda x: -1 if x is None else float(x[coin]['price']))

            threshold_check = (-1.0 if min_price[coin]['time'] > max_price[coin]['time'] else 1.0) * (float(max_price[coin]['price']) - float(min_price[coin]['price'])) / float(min_price[coin]['price']) * 100

            #if coin == "BTCUSDT" or coin == "ETHUSDT":
                #print(f"coin: {coin} min_price: {min_price[coin]['price']} max_price: {max_price[coin]['price']}")
        except KeyError:
            if DEBUG:
                print(f"wait_for_price(): Got a KeyError for {coin}. If this coin was just added to your tickers file, no need to worry about this KeyError.")
            continue

        # FOR NEGATIVE PRICE CHECKING
        #if threshold_check>0 and CHANGE_IN_PRICE<0: threshold_check=0

        # each coin with higher gains than our CHANGE_IN_PRICE is added to the volatile_coins dict if less than TRADE_SLOTS is not reached.
        # FOR NEGATIVE PRICE CHECKING
        #if abs(threshold_check) > abs(CHANGE_IN_PRICE):
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
        if excoin not in volatile_coins and excoin not in coins_bought and \
                (len(coins_bought) + len(volatile_coins)) < TRADE_SLOTS:

            #(len(coins_bought) + exnumber + len(volatile_coins)) < TRADE_SLOTS:
            volatile_coins[excoin] = 1
            exnumber +=1
            print(f"External signal received on {excoin}, purchasing ${TRADE_TOTAL} {PAIR_WITH} value of {excoin}!")

    balance_report(last_price)

    return volatile_coins, len(volatile_coins), historical_prices[hsp_head]


def buy_external_signals():
    external_list = {}
    signals = {}

    # check directory and load pairs from files into external_list
    signals = glob.glob("signals/*.buy")
    for filename in signals:
        for line in open(filename):
            symbol = line.strip()
            external_list[symbol] = symbol
        try:
            os.remove(filename)
        except:
            if DEBUG: print(f'{txcolors.WARNING}Could not remove external signalling file{txcolors.DEFAULT}')

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
            if DEBUG: print(f'{txcolors.WARNING}Could not remove external SELL signalling file{txcolors.DEFAULT}')

    return external_list


def balance_report(last_price):

    global trade_wins, trade_losses, session_profit_incfees_perc, session_profit_incfees_total
    unrealised_session_profit_incfees_perc = 0
    unrealised_session_profit_incfees_total = 0

    BUDGET = TRADE_SLOTS * TRADE_TOTAL
    exposure_calcuated = 0

    for coin in list(coins_bought):
        LastPrice = float(last_price[coin]['price'])
        sellFee = (LastPrice * (TRADING_FEE/100))
        
        BuyPrice = float(coins_bought[coin]['bought_at'])
        buyFee = (BuyPrice * (TRADING_FEE/100))

        exposure_calcuated = exposure_calcuated + round(float(coins_bought[coin]['bought_at']) * float(coins_bought[coin]['volume']),0)

        #PriceChangeIncFees_Total = float(((LastPrice+sellFee) - (BuyPrice+buyFee)) * coins_bought[coin]['volume'])
        PriceChangeIncFees_Total = float(((LastPrice-sellFee) - (BuyPrice+buyFee)) * coins_bought[coin]['volume'])

        # unrealised_session_profit_incfees_perc = float(unrealised_session_profit_incfees_perc + PriceChangeIncFees_Perc)
        unrealised_session_profit_incfees_total = float(unrealised_session_profit_incfees_total + PriceChangeIncFees_Total)

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
    
    market_profit = ((market_currprice - market_startprice)/ market_startprice) * 100

    mode = "Live (REAL MONEY)"
    discord_mode = "Live"
    if TEST_MODE:
        mode = "Test (no real money used)"
        discord_mode = "Test"

    font = f'{txcolors.ENDC}{txcolors.YELLOW}{txcolors.BOLD}{txcolors.UNDERLINE}'
    extsigs = ""
    try:
        for module in SIGNALLING_MODULES:
            if extsigs == "":
                extsigs = module
            else:
                extsigs = extsigs + ', ' + module
    except Exception as e:
        pass
    if extsigs == "":
        extsigs = "No external signals running"

    print(f'')
    print(f'--------')
    print(f"STARTED         : {str(bot_started_datetime).split('.')[0]} | Running for: {str(datetime.now() - bot_started_datetime).split('.')[0]}")
    print(f'CURRENT HOLDS   : {len(coins_bought)}/{TRADE_SLOTS} ({float(CURRENT_EXPOSURE):g}/{float(INVESTMENT_TOTAL):g} {PAIR_WITH})')
    if REINVEST_PROFITS:
        print(f'ADJ TRADE TOTAL : {TRADE_TOTAL:.2f} (Current TRADE TOTAL adjusted to reinvest profits)')
    print(f'BUYING MODE     : {font if mode == "Live (REAL MONEY)" else txcolors.DEFAULT}{mode}{txcolors.DEFAULT}{txcolors.ENDC}')
    print(f'Buying Paused   : {bot_paused}')
    print(f'')
    print(f'SESSION PROFIT (Inc Fees)')
    print(f'Realised        : {txcolors.SELL_PROFIT if session_profit_incfees_perc > 0. else txcolors.SELL_LOSS}{session_profit_incfees_perc:.4f}% Est:${session_profit_incfees_total:.4f} {PAIR_WITH}{txcolors.DEFAULT}')
    print(f'Unrealised      : {txcolors.SELL_PROFIT if unrealised_session_profit_incfees_perc > 0. else txcolors.SELL_LOSS}{unrealised_session_profit_incfees_perc:.4f}% Est:${unrealised_session_profit_incfees_total:.4f} {PAIR_WITH}{txcolors.DEFAULT}')
    print(f'        Total   : {txcolors.SELL_PROFIT if (session_profit_incfees_perc + unrealised_session_profit_incfees_perc) > 0. else txcolors.SELL_LOSS}{session_profit_incfees_perc + unrealised_session_profit_incfees_perc:.4f}% Est:${session_profit_incfees_total+unrealised_session_profit_incfees_total:.4f} {PAIR_WITH}{txcolors.DEFAULT}')
    print(f'')
    print(f'ALL TIME DATA   :')
    print(f"Market Profit   : {txcolors.SELL_PROFIT if market_profit > 0. else txcolors.SELL_LOSS}{market_profit:.4f}% (BTCUSDT Since STARTED){txcolors.DEFAULT}")
    print(f'Bot Profit      : {txcolors.SELL_PROFIT if historic_profit_incfees_perc > 0. else txcolors.SELL_LOSS}{historic_profit_incfees_perc:.4f}% Est:${historic_profit_incfees_total:.4f} {PAIR_WITH}{txcolors.DEFAULT}')
    print(f'Completed Trades: {trade_wins+trade_losses} (Wins:{trade_wins} Losses:{trade_losses})')
    print(f'Win Ratio       : {float(WIN_LOSS_PERCENT):g}%')
    print(f'')
    print(f'External Signals: {extsigs}')
    print(f'--------')
    print(f'')
    #msg1 = str(bot_started_datetime) + " | " + str(datetime.now() - bot_started_datetime)
    msg1 = str(datetime.now()).split('.')[0]
    msg2 = " | " + str(len(coins_bought)) + "/" + str(TRADE_SLOTS) + " | PBOT: " + str(bot_paused) + " | MODE: " + str(discord_mode)
    msg2 = msg2 + ' SPR%: ' + str(round(session_profit_incfees_perc,2)) + ' SPR$: ' + str(round(session_profit_incfees_total,4))
    msg2 = msg2 + ' SPU%: ' + str(round(unrealised_session_profit_incfees_perc,2)) + ' SPU$: ' + str(round(unrealised_session_profit_incfees_total,4))
    msg2 = msg2 + ' SPT%: ' + str(round(session_profit_incfees_perc + unrealised_session_profit_incfees_perc,2)) + ' SPT$: ' + str(round(session_profit_incfees_total+unrealised_session_profit_incfees_total,4))
    msg2 = msg2 + ' ATP%: ' + str(round(historic_profit_incfees_perc,2)) + ' ATP$: ' + str(round(historic_profit_incfees_total,4))
    msg2 = msg2 + ' CTT: ' + str(trade_wins+trade_losses) + ' CTW: ' + str(trade_wins) + ' CTL: ' + str(trade_losses) + ' CTWR%: ' + str(round(WIN_LOSS_PERCENT,2))

    msg_discord_balance(msg1, msg2)
    history_log(session_profit_incfees_perc, session_profit_incfees_total, unrealised_session_profit_incfees_perc, unrealised_session_profit_incfees_total, session_profit_incfees_perc + unrealised_session_profit_incfees_perc, session_profit_incfees_total+unrealised_session_profit_incfees_total, historic_profit_incfees_perc, historic_profit_incfees_total, trade_wins+trade_losses, trade_wins, trade_losses, WIN_LOSS_PERCENT)

    return msg1 + msg2

def history_log(sess_profit_perc, sess_profit, sess_profit_perc_unreal, sess_profit_unreal, sess_profit_perc_total, sess_profit_total, alltime_profit_perc, alltime_profit, total_trades, won_trades, lost_trades, winloss_ratio):
    global last_history_log_date
    time_between_insertion = datetime.now() - last_history_log_date

    # only log balance to log file once every 60 seconds
    if time_between_insertion.seconds > 60:
        last_history_log_date = datetime.now()
        timestamp = datetime.now().strftime("%y-%m-%d %H:%M:%S")

        if not os.path.exists(HISTORY_LOG_FILE):
            with open(HISTORY_LOG_FILE,'a+') as f:
                f.write('Datetime\tCoins Holding\tTrade Slots\tPausebot Active\tSession Profit %\tSession Profit $\tSession Profit Unrealised %\tSession Profit Unrealised $\tSession Profit Total %\tSession Profit Total $\tAll Time Profit %\tAll Time Profit $\tTotal Trades\tWon Trades\tLost Trades\tWin Loss Ratio\n')    

        with open(HISTORY_LOG_FILE,'a+') as f:
            f.write(f'{timestamp}\t{len(coins_bought)}\t{TRADE_SLOTS}\t{str(bot_paused)}\t{str(round(sess_profit_perc,2))}\t{str(round(sess_profit,4))}\t{str(round(sess_profit_perc_unreal,2))}\t{str(round(sess_profit_unreal,4))}\t{str(round(sess_profit_perc_total,2))}\t{str(round(sess_profit_total,4))}\t{str(round(alltime_profit_perc,2))}\t{str(round(alltime_profit,4))}\t{str(total_trades)}\t{str(won_trades)}\t{str(lost_trades)}\t{str(winloss_ratio)}\n')

def msg_discord_balance(msg1, msg2):
    global last_msg_discord_balance_date, discord_msg_balance_data
    time_between_insertion = datetime.now() - last_msg_discord_balance_date
    
    # only put the balance message to discord once every 60 seconds and if the balance information has changed since last times
    if time_between_insertion.seconds > 60:
        if msg2 != discord_msg_balance_data:
            msg_discord(msg1 + msg2)
            discord_msg_balance_data = msg2
        else:
            # ping msg to know the bot is still running
            msg_discord(".")

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
    global bot_paused, session_profit_incfees_perc, hsp_head, session_profit_incfees_total

    # start counting for how long the bot has been paused
    start_time = time.perf_counter()

    while os.path.exists("signals/pausebot.pause"):

        # do NOT accept any external signals to buy while in pausebot mode
        remove_external_signals('buy')

        if bot_paused == False:
            print(f'{txcolors.WARNING}Buying paused due to negative market conditions, stop loss and take profit will continue to work...{txcolors.DEFAULT}')
            
            msg = str(datetime.now()) + ' | PAUSEBOT. Buying paused due to negative market conditions, stop loss and take profit will continue to work.'
            msg_discord(msg)

            bot_paused = True

        # Sell function needs to work even while paused
        coins_sold = sell_coins()
        remove_from_portfolio(coins_sold)
        last_price = get_price(True)

        # pausing here
        if hsp_head == 1: 
            # print(f'Paused...Session profit: {session_profit_incfees_perc:.2f}% Est: ${session_profit_incfees_total:.{decimals()}f} {PAIR_WITH}')
            balance_report(last_price)
        
        time.sleep((TIME_DIFFERENCE * 60) / RECHECK_INTERVAL)

    else:
        # stop counting the pause time
        stop_time = time.perf_counter()
        time_elapsed = timedelta(seconds=int(stop_time-start_time))

        # resume the bot and ser pause_bot to False
        if  bot_paused == True:
            print(f'{txcolors.WARNING}Resuming buying due to positive market conditions, total sleep time: {time_elapsed}{txcolors.DEFAULT}')
            
            msg = str(datetime.now()) + ' | PAUSEBOT. Resuming buying due to positive market conditions, total sleep time: ' + str(time_elapsed)
            msg_discord(msg)

            bot_paused = False

    return


def convert_volume():
    '''Converts the volume given in TRADE_TOTAL from USDT to the each coin's volume'''

    volatile_coins, number_of_coins, last_price = wait_for_price()
    lot_size = {}
    volume = {}

    for coin in volatile_coins:

        # Find the correct step size for each coin
        # max accuracy for BTC for example is 6 decimal points
        # while XRP is only 1
        try:
            info = client.get_symbol_info(coin)
            step_size = info['filters'][2]['stepSize']
            lot_size[coin] = step_size.index('1') - 1
            
            if lot_size[coin] < 0:
                lot_size[coin] = 0

        except:
            pass

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

    return volume, last_price


def buy():
    '''Place Buy market orders for each volatile coin found'''
    volume, last_price = convert_volume()
    orders = {}

    for coin in volume:

        if coin not in coins_bought:
            print(f"{txcolors.BUY}Preparing to buy {volume[coin]} of {coin} @ ${last_price[coin]['price']}{txcolors.DEFAULT}")

            msg1 = str(datetime.now()) + ' | BUY: ' + coin + '. V:' +  str(volume[coin]) + ' P$:' + str(last_price[coin]['price'])
            msg_discord(msg1)

            if TEST_MODE:
                orders[coin] = [{
                    'symbol': coin,
                    'orderId': 0,
                    'time': datetime.now().timestamp()
                }]

           		# Log trade
                #if LOG_TRADES:
                write_log(f"\tBuy\t{coin}\t{volume[coin]}\t{last_price[coin]['price']}\t{PAIR_WITH}")
                
                #write_signallsell(coin.removesuffix(PAIR_WITH))
                write_signallsell(rchop(coin, PAIR_WITH))

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

        # run the else block if the position has been placed and return order info
            else:
                orders[coin] = client.get_all_orders(symbol=coin, limit=1)

            # binance sometimes returns an empty list, the code will wait here until binance returns the order
                while orders[coin] == []:
                    print('Binance is being slow in returning the order, calling the API again...')

                    orders[coin] = client.get_all_orders(symbol=coin, limit=1)
                    time.sleep(1)

                else:
                    print('Order returned, saving order to file')

                    if not TEST_MODE:
                        orders[coin] = extract_order_data(order_details)
                        write_log(f"\tBuy\t{coin}\t{orders[coin]['volume']}\t{orders[coin]['avgPrice']}\t{PAIR_WITH}")
                    else:
                        write_log(f"\tBuy\t{coin}\t{volume[coin]}\t{last_price[coin]['price']}\t{PAIR_WITH}")
                    
                    write_signallsell(coin)

        else:
            print(f'Signal detected, but there is already an active trade on {coin}')
    return orders, last_price, volume


def sell_coins(tpsl_override = False, specific_coin_to_sell = ""):
    '''sell coins that have reached the STOP LOSS or TAKE PROFIT threshold'''
    global hsp_head, session_profit_incfees_perc, session_profit_incfees_total, coin_order_id, trade_wins, trade_losses, historic_profit_incfees_perc, historic_profit_incfees_total, sell_all_coins, sell_specific_coin
    
    global TRADE_TOTAL
    externals = sell_external_signals()
    
    last_price = get_price(False) # don't populate rolling window
    #last_price = get_price(add_to_historical=True) # don't populate rolling window
    coins_sold = {}

    BUDGET = TRADE_TOTAL * TRADE_SLOTS
    
    # table stuff
    my_table = PrettyTable()
    my_table.field_names = ["Symbol", "Volume", "Bought At", "Now At", "TP %", "SL %", "Change %", "Profit $", "Time Held"]
    my_table.align["Symbol"] = "l"
    my_table.align["Volume"] = "r"
    my_table.align["Bought At"] = "r"
    my_table.align["Now At"] = "r"
    my_table.align["TP %"] = "r"
    my_table.align["SL %"] = "r"
    my_table.align["Change %"] = "r"
    my_table.align["Profit $"] = "r"
    my_table.align["Time Held"] = "l"

    for coin in list(coins_bought):
        if sell_specific_coin and not specific_coin_to_sell == coin:
            continue
        #time_held = timedelta(seconds=datetime.now().timestamp()-coins_bought[coin]['timestamp'])
        time_held = timedelta(seconds=datetime.now().timestamp()-int(str(coins_bought[coin]['timestamp'])[:10]))

        #if HODLMODE_ENABLED and (time_held >= HODLMODE_TIME_THRESHOLD):
        #    move_coin_to_hodl(coin)
        #    continue

        LastPrice = float(last_price[coin]['price'])
        sellFee = (LastPrice * (TRADING_FEE/100))
        sellFeeTotal = (coins_bought[coin]['volume'] * LastPrice) * (TRADING_FEE/100)
        LastPriceLessFees = LastPrice - sellFee

        BuyPrice = float(coins_bought[coin]['bought_at'])
        buyFee = (BuyPrice * (TRADING_FEE/100))
        buyFeeTotal = (coins_bought[coin]['volume'] * BuyPrice) * (TRADING_FEE/100)
        BuyPricePlusFees = BuyPrice + buyFee

        ProfitAfterFees = LastPriceLessFees - BuyPricePlusFees

        PriceChange_Perc = float((LastPrice - BuyPrice) / BuyPrice * 100)
        #PriceChangeIncFees_Perc = float(((LastPrice+sellFee) - (BuyPrice+buyFee)) / (BuyPrice+buyFee) * 100)
        PriceChangeIncFees_Perc = float(((LastPriceLessFees - BuyPricePlusFees) / BuyPricePlusFees) * 100)
        #PriceChangeIncFees_Unit = float((LastPrice+sellFee) - (BuyPrice+buyFee))
        PriceChangeIncFees_Unit = float(LastPriceLessFees - BuyPricePlusFees)

        # define stop loss and take profit
        TP = float(coins_bought[coin]['bought_at']) + ((float(coins_bought[coin]['bought_at']) * (coins_bought[coin]['take_profit']) / 100))
        SL = float(coins_bought[coin]['bought_at']) + ((float(coins_bought[coin]['bought_at']) * (coins_bought[coin]['stop_loss']) / 100))

        # check that the price is above the take profit and readjust SL and TP accordingly if trialing stop loss used
        #if LastPrice > TP and USE_TRAILING_STOP_LOSS and not sell_all_coins and not tpsl_override:
        if LastPriceLessFees > TP and USE_TRAILING_STOP_LOSS and not sell_all_coins and not tpsl_override and not sell_specific_coin:
            # increasing TP by TRAILING_TAKE_PROFIT (essentially next time to readjust SL)

            #if PriceChange_Perc >= 0.8:
            if PriceChangeIncFees_Perc >= 0.8:
                # price has changed by 0.8% or greater, a big change. Make the STOP LOSS trail closely to the TAKE PROFIT
                # so you don't lose this increase in price if it falls back
                #coins_bought[coin]['take_profit'] = PriceChange_Perc + TRAILING_TAKE_PROFIT    
                coins_bought[coin]['take_profit'] = PriceChangeIncFees_Perc + TRAILING_TAKE_PROFIT    
                coins_bought[coin]['stop_loss'] = coins_bought[coin]['take_profit'] - TRAILING_STOP_LOSS
            else:
                # price has changed by less than 0.8%, a small change. Make the STOP LOSS trail loosely to the TAKE PROFIT
                # so you don't get stopped out of the trade prematurely
                coins_bought[coin]['stop_loss'] = coins_bought[coin]['take_profit'] - TRAILING_STOP_LOSS
                #coins_bought[coin]['take_profit'] = PriceChange_Perc + TRAILING_TAKE_PROFIT
                coins_bought[coin]['take_profit'] = PriceChangeIncFees_Perc + TRAILING_TAKE_PROFIT

            # we've got a negative stop loss - not good, we don't want this.
            if coins_bought[coin]['stop_loss'] <= 0:
                coins_bought[coin]['stop_loss'] = coins_bought[coin]['take_profit'] * .25
                
            #if DEBUG: print(f"{coin} TP reached, adjusting TP {coins_bought[coin]['take_profit']:.{decimals()}f} and SL {coins_bought[coin]['stop_loss']:.{decimals()}f} accordingly to lock-in profit")
            my_table.add_row([f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{coin + ' TP up!'}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{coins_bought[coin]['volume']:.6f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{BuyPrice:.6f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{LastPrice:.6f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{coins_bought[coin]['take_profit']:.4f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{coins_bought[coin]['stop_loss']:.4f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{PriceChangeIncFees_Perc:.4f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{((float(coins_bought[coin]['volume'])*float(coins_bought[coin]['bought_at']))*PriceChangeIncFees_Perc)/100:.6f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{str(time_held).split('.')[0]}{txcolors.DEFAULT}"])
            
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
            #if LastPrice < SL: 
            if LastPriceLessFees < SL: 
                sellCoin = True
                if USE_TRAILING_STOP_LOSS:
                    #if PriceChange_Perc >= 0:PriceChangeIncFees_Perc
                    if PriceChangeIncFees_Perc >= 0:
                        sell_reason = "TTP " + str(SL) + " reached"
                    else:
                        sell_reason = "TSL " + str(SL) + " reached"
                else:
                    sell_reason = "SL " + str(SL) + " reached"
                sell_reason = sell_reason 
            #if LastPrice > TP:
            if LastPriceLessFees > TP:
                sellCoin = True
                sell_reason = "TP " + str(TP) + " reached"
            if coin in externals:
                sellCoin = True
                sell_reason = 'External Sell Signal'

        if sell_all_coins:
            sellCoin = True
            sell_reason = 'Sell All Coins'
        if sell_specific_coin:
            sellCoin = True
            sell_reason = 'Sell Specific Coin'
        if tpsl_override:
            sellCoin = True
            sell_reason = session_tpsl_override_msg

        if sellCoin:
            print(f"{txcolors.SELL_PROFIT if PriceChangeIncFees_Perc >= 0. else txcolors.SELL_LOSS}Sell: {coins_bought[coin]['volume']} of {coin} | {sell_reason} | ${float(LastPrice):g} - ${float(BuyPrice):g} | Profit: {PriceChangeIncFees_Perc:.2f}% Est: {((float(coins_bought[coin]['volume'])*float(coins_bought[coin]['bought_at']))*PriceChangeIncFees_Perc)/100:.{decimals()}f} {PAIR_WITH} (Inc Fees){txcolors.DEFAULT}")
            
            msg1 = str(datetime.now()) + '| SELL: ' + coin + '. R:' +  sell_reason + ' P%:' + str(round(PriceChangeIncFees_Perc,2)) + ' P$:' + str(round(((float(coins_bought[coin]['volume'])*float(coins_bought[coin]['bought_at']))*PriceChangeIncFees_Perc)/100,4))
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
                print(f"sell_coins() Exception occured on selling the coin! Coin: {coin}\nSell Volume coins_bought: {coins_bought[coin]['volume']}\nPrice:{LastPrice}\nException: {e}")

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

                if DEBUG:
                    print(f"sell_coins() | Coin: {coin} | Sell Volume: {coins_bought[coin]['volume']} | Price:{LastPrice}")

                # Log trade
                #BB profit = ((LastPrice - BuyPrice) * coins_sold[coin]['volume']) * (1-(buyFee + sellFeeTotal))                
                profit_incfees_total = coins_sold[coin]['volume'] * PriceChangeIncFees_Unit
                #write_log(f"Sell: {coins_sold[coin]['volume']} {coin} - {BuyPrice} - {LastPrice} Profit: {profit_incfees_total:.{decimals()}f} {PAIR_WITH} ({PriceChange_Perc:.2f}%)")
                #write_log(f"\tSell\t{coin}\t{coins_sold[coin]['volume']}\t{BuyPrice}\t{PAIR_WITH}\t{LastPrice}\t{profit_incfees_total:.{decimals()}f}\t{PriceChange_Perc:.2f}\t{sell_reason}")
                write_log(f"\tSell\t{coin}\t{coins_sold[coin]['volume']}\t{BuyPrice}\t{PAIR_WITH}\t{LastPrice}\t{profit_incfees_total:.{decimals()}f}\t{PriceChangeIncFees_Perc:.2f}\t{sell_reason}")
                
                #reinvest profits
                if REINVEST_PROFITS:
                    TRADE_TOTAL += (profit_incfees_total / TRADE_SLOTS)

                #this is good
                session_profit_incfees_total = session_profit_incfees_total + profit_incfees_total
                session_profit_incfees_perc = session_profit_incfees_perc + ((profit_incfees_total/BUDGET) * 100)
                
                historic_profit_incfees_total = historic_profit_incfees_total + profit_incfees_total
                historic_profit_incfees_perc = historic_profit_incfees_perc + ((profit_incfees_total/BUDGET) * 100)
                
                #TRADE_TOTAL*PriceChangeIncFees_Perc)/100
                
                #if (LastPrice+sellFee) >= (BuyPrice+buyFee):
                if (LastPrice-sellFee) >= (BuyPrice+buyFee):
                    trade_wins += 1
                else:
                    trade_losses += 1

                update_bot_stats()
                if not sell_all_coins and not sell_specific_coin:
                    # within sell_all_coins, it will print display to screen
                    balance_report(last_price)

            # sometimes get "rate limited" errors from Binance if we try to sell too many coins at once
            # so wait 1 second in between sells
            time.sleep(1)
            
            continue

        # no action; print once every TIME_DIFFERENCE
        if hsp_head == 1:
            if len(coins_bought) > 0:
                #print(f"Holding: {coins_bought[coin]['volume']} of {coin} | {LastPrice} - {BuyPrice} | Profit: {txcolors.SELL_PROFIT if PriceChangeIncFees_Perc >= 0. else txcolors.SELL_LOSS}{PriceChangeIncFees_Perc:.4f}% Est: ({((float(coins_bought[coin]['volume'])*float(coins_bought[coin]['bought_at']))*PriceChangeIncFees_Perc)/100:.{decimals()}f} {PAIR_WITH}){txcolors.DEFAULT}")
                my_table.add_row([f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{coin}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{coins_bought[coin]['volume']:.6f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{BuyPrice:.6f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{LastPrice:.6f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{coins_bought[coin]['take_profit']:.4f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{coins_bought[coin]['stop_loss']:.4f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{PriceChangeIncFees_Perc:.4f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{((float(coins_bought[coin]['volume'])*float(coins_bought[coin]['bought_at']))*PriceChangeIncFees_Perc)/100:.6f}{txcolors.DEFAULT}", f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{str(time_held).split('.')[0]}{txcolors.DEFAULT}"])
                
    my_table.sortby = 'Change %'
    #my_table.reversesort = True
        
    if len(coins_bought) == 0:
        if hsp_head == 1:
            print(f"No trade slots are currently in use")
    else:
        if len(my_table._rows) > 0: print_table(my_table)

    # if tpsl_override: is_bot_running = False

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
            print(f"WARNING: BNB not used for trading fee, please enable it in Binance!")
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
        print(f"extract_order_data(): Exception getting coin {order_details['symbol']} step size! Exception: {e}")

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
        session_tpsl_override_msg = "Session TP Override target of " + str(SESSION_TAKE_PROFIT) + f"% met. Sell all coins now! Session profit is {allsession_profits_perc}%"
        is_bot_running = False
    if allsession_profits_perc <= float(SESSION_STOP_LOSS):
        session_tpsl_override_msg = "Session SL Override target of " + str(SESSION_STOP_LOSS) + f"% met. Sell all coins now! Session loss is {allsession_profits_perc}%"
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

            print(f'Order for {orders[coin]["symbol"]} with ID {orders[coin]["orderId"]} placed and saved to file.')
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

            print(f'Order for {orders[coin][0]["symbol"]} with ID {orders[coin][0]["orderId"]} placed and saved to file.')

        # save the coins in a json file in the same directory
        with open(coins_bought_file_path, 'w') as file:
            json.dump(coins_bought, file, indent=4)

def update_bot_stats():
    global trade_wins, trade_losses, historic_profit_incfees_perc, historic_profit_incfees_total

    bot_stats = {
        'total_capital' : TRADE_SLOTS * TRADE_TOTAL,
        'botstart_datetime' : str(bot_started_datetime),
        'historicProfitIncFees_Percent': historic_profit_incfees_perc,
        'historicProfitIncFees_Total': historic_profit_incfees_total,
        'tradeWins': trade_wins,
        'tradeLosses': trade_losses,
        'market_startprice': market_startprice
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
            #write_signallsell(coin.removesuffix(PAIR_WITH))
            write_signallsell(rchop(coin, PAIR_WITH))
    

def write_log(logline):
    timestamp = datetime.now().strftime("%y-%m-%d %H:%M:%S")

    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE,'a+') as f:
            f.write('Datetime\tType\tCoin\tVolume\tBuy Price\tCurrency\tSell Price\tProfit $\tProfit %\tSell Reason\n')    

    with open(LOG_FILE,'a+') as f:
        f.write(timestamp + ' ' + logline + '\n')

def write_signallsell(symbol):
    with open('signalsell_tickers.txt','a+') as f:
        f.write(f'{symbol}\n')

def remove_external_signals(fileext):
    signals = glob.glob(f'signals/*.{fileext}')
    for filename in signals:
        try:
            os.remove(filename)
        except:
            if DEBUG: print(f'{txcolors.WARNING}Could not remove external signalling file {filename}{txcolors.DEFAULT}')

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
    #last_price = get_price()
    last_price = wrap_get_price()

    discordmsg = balance_report(last_price)
    msg_discord(discordmsg)

    sell_all_coins = False

def sell_a_specific_coin(coin):
    global sell_specific_coin

    msg_discord(f'{str(datetime.now())} | SELL SPECIFIC COIN: {coin}')

    # sell all coins NOW!
    sell_specific_coin = True

    coins_sold = sell_coins(False, coin)
    remove_from_portfolio(coins_sold)

    sell_specific_coin = False
    
def restart_signal_threads():
    try:
        for signalthread in signalthreads:
            if any(signalthread.name in word for word in EXTSIGNAL_MODULES):
                
                name = signalthread.name
                
                print(f'Terminating thread {str(name)}')
                signalthread.terminate()
            
                time.sleep(2)

                start_signal_thread(name)
    except:
        pass


def stop_signal_threads():

    try:
        for signalthread in signalthreads:
            print(f'Terminating thread {str(signalthread.name)}')
            signalthread.terminate()
    except:
        pass

def start_signal_threads():
    signal_threads = []

    try:
        if len(SIGNALLING_MODULES) > 0:
            for module in SIGNALLING_MODULES:
                #print(f"Starting external signal: {module}")
                # add process to a list. This is so the thread can be terminated at a later time
                signal_threads.append(start_signal_thread(module))
        else:
            print(f'No modules to load {SIGNALLING_MODULES}')
    except Exception as e:
        if str(e) == "object of type 'NoneType' has no len()":
            print(f'No external signal modules running')
        else:
            print(f'start_signal_threads(): Loading external signals exception: {e}')

    return signal_threads

def start_signal_thread(module):
    try:
        print(f'Starting {module}')
        mymodule[module] = importlib.import_module(module)
        # t = threading.Thread(target=mymodule[module].do_work, args=())
        t = multiprocessing.Process(target=mymodule[module].do_work, args=())
        t.name = module
        t.daemon = True
        t.start()
        
        time.sleep(2)

        return t
    except Exception as e:
        if str(e) == "object of type 'NoneType' has no len()":
            print(f'No external signal modules running')
        else:
            print(f'start_signal_thread(): Loading external signals exception: {e}')


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

def wrap_get_price():
    # Use CUSTOM_LIST symbols if CUSTOM_LIST is set to True
    global tickers

    if CUSTOM_LIST: 
        if CUSTOM_LIST_AUTORELOAD:
            while True:
                if not os.path.exists(TICKERS_LIST):
                    print(f"Autoreload tickers cannot find {TICKERS_LIST} file. Will retry in 1 second.")
                    time.sleep(1)
                else:
                    break
            prevcoincount = len(tickers)
            
            # tickers=[line.strip() for line in open(TICKERS_LIST)]
            # Reload coins, also adding those coins that we currently hold
            #tickers=list(set([line.strip() for line in open(TICKERS_LIST)] + [coin['symbol'].removesuffix(PAIR_WITH) for coin in coins_bought.values()]))
            tickers=list(set([line.strip() for line in open(TICKERS_LIST)] + [rchop(coin['symbol'], PAIR_WITH) for coin in coins_bought.values()]))

            if DEBUG:
                print(f"Reloaded tickers from {TICKERS_LIST} file. Prev coin count: {prevcoincount} | New coin count: {len(tickers)}")

    return get_price()

if __name__ == '__main__':

    #req_version = (3,9)
    #if sys.version_info[:2] < req_version: 
    #    print(f'This bot requires Python version 3.9 or higher/newer. You are running version {sys.version_info[:2]} - please upgrade your Python version!!')
    #    sys.exit()

    # Load arguments then parse settings
    args = parse_args()
    mymodule = {}

    discord_msg_balance_data = ""
    last_msg_discord_balance_date = datetime.now()
    last_history_log_date = datetime.now()

    # set to false at Start
    global bot_paused
    bot_paused = False

    DEFAULT_CONFIG_FILE = 'config.yml'
    DEFAULT_CREDS_FILE = 'creds.yml'

    config_file = args.config if args.config else DEFAULT_CONFIG_FILE
    creds_file = args.creds if args.creds else DEFAULT_CREDS_FILE
    parsed_config = load_config(config_file)
    parsed_creds = load_config(creds_file)

    # Default no debugging
    DEBUG = False

    # Load system vars
    TEST_MODE = parsed_config['script_options']['TEST_MODE']
    #     LOG_TRADES = parsed_config['script_options'].get('LOG_TRADES')
    LOG_FILE = parsed_config['script_options'].get('LOG_FILE')
    HISTORY_LOG_FILE = "history.txt"
    DEBUG_SETTING = parsed_config['script_options'].get('DEBUG')
    AMERICAN_USER = parsed_config['script_options'].get('AMERICAN_USER')

    # Load trading vars
    PAIR_WITH = parsed_config['trading_options']['PAIR_WITH']
    TRADE_TOTAL = parsed_config['trading_options']['TRADE_TOTAL']
    TRADE_SLOTS = parsed_config['trading_options']['TRADE_SLOTS']
    FIATS = parsed_config['trading_options']['FIATS']
    
    TIME_DIFFERENCE = parsed_config['trading_options']['TIME_DIFFERENCE']
    RECHECK_INTERVAL = parsed_config['trading_options']['RECHECK_INTERVAL']
    
    CHANGE_IN_PRICE = parsed_config['trading_options']['CHANGE_IN_PRICE']
    STOP_LOSS = parsed_config['trading_options']['STOP_LOSS']
    TAKE_PROFIT = parsed_config['trading_options']['TAKE_PROFIT']
    
    #COOLOFF_PERIOD = parsed_config['trading_options']['COOLOFF_PERIOD']

    CUSTOM_LIST = parsed_config['trading_options']['CUSTOM_LIST']
    CUSTOM_LIST_AUTORELOAD = parsed_config['trading_options']['CUSTOM_LIST_AUTORELOAD']
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
    
    # Whether the bot should reinvest your profits or not.
    REINVEST_PROFITS = parsed_config['trading_options']['REINVEST_PROFITS']

    # Functionality to "reset / restart" external signal modules
    RESTART_EXTSIGNALS = parsed_config['trading_options']['RESTART_EXTSIGNALS']
    EXTSIGNAL_MODULES = parsed_config['trading_options']['EXTSIGNAL_MODULES']

    # Trashcan settings
    #HODLMODE_ENABLED = parsed_config['trading_options']['HODLMODE_ENABLED']
    #HODLMODE_TIME_THRESHOLD = parsed_config['trading_options']['HODLMODE_TIME_THRESHOLD']

    TRADING_FEE = parsed_config['trading_options']['TRADING_FEE']
    SIGNALLING_MODULES = parsed_config['trading_options']['SIGNALLING_MODULES']

    if DEBUG_SETTING or args.debug:
        DEBUG = True

    # Load creds for correct environment
    access_key, secret_key = load_correct_creds(parsed_creds)

    if DEBUG:
        print(f'Loaded config below\n{json.dumps(parsed_config, indent=4)}')
        print(f'Your credentials have been loaded from {creds_file}')

    if MSG_DISCORD:
        DISCORD_WEBHOOK = load_discord_creds(parsed_creds)

    sell_all_coins = False
    sell_specific_coin = False

    # Authenticate with the client, Ensure API key is good before continuing
    if AMERICAN_USER:
        client = Client(access_key, secret_key, tld='us')
    else:
        client = Client(access_key, secret_key)

    # If the users has a bad / incorrect API key.
    # this will stop the script from starting, and display a helpful error.
    api_ready, msg = test_api_key(client, BinanceAPIException)
    if api_ready is not True:
        exit(f'{txcolors.SELL_LOSS}{msg}{txcolors.DEFAULT}')

    # Use CUSTOM_LIST symbols if CUSTOM_LIST is set to True
    if CUSTOM_LIST: tickers=[line.strip() for line in open(TICKERS_LIST)]

    # try to load all the coins bought by the bot if the file exists and is not empty
    coins_bought = {}

    if TEST_MODE:
        file_prefix = 'test_'
    else:
        file_prefix = 'live_'

    # path to the saved coins_bought file
    coins_bought_file_path = file_prefix + 'coins_bought.json'

    # The below mod was stolen and altered from GoGo's fork, a nice addition for keeping a historical history of profit across multiple bot sessions.
    # path to the saved bot_stats file
    bot_stats_file_path = file_prefix + 'bot_stats.json'

    # use separate files for testing and live trading
    LOG_FILE = file_prefix + LOG_FILE
    HISTORY_LOG_FILE = file_prefix + HISTORY_LOG_FILE

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

            historic_profit_incfees_perc = bot_stats['historicProfitIncFees_Percent']
            historic_profit_incfees_total = bot_stats['historicProfitIncFees_Total']
            trade_wins = bot_stats['tradeWins']
            trade_losses = bot_stats['tradeLosses']
            try:
                market_startprice = bot_stats['market_startprice']
            except:
                pass

            if total_capital != total_capital_config:
                historic_profit_incfees_perc = (historic_profit_incfees_total / total_capital_config) * 100

    if REINVEST_PROFITS:
        TRADE_TOTAL = total_capital / TRADE_SLOTS

    # rolling window of prices; cyclical queue
    historical_prices = [None] * (TIME_DIFFERENCE * RECHECK_INTERVAL)
    hsp_head = -1

    # prevent including a coin in volatile_coins if it has already appeared there less than TIME_DIFFERENCE minutes ago
    volatility_cooloff = {}

    # if saved coins_bought json file exists and it's not empty then load it
    if os.path.isfile(coins_bought_file_path) and os.stat(coins_bought_file_path).st_size!= 0:
        with open(coins_bought_file_path) as file:
                coins_bought = json.load(file)

    print(f'{txcolors.WARNING}Press Ctrl-C for more options / to stop the bot{txcolors.DEFAULT}')

    if not TEST_MODE:
        if not args.notimeout: # if notimeout skip this (fast for dev tests)
            print('WARNING: Test mode is disabled in the configuration, you are using _LIVE_ funds.')
            print('WARNING: Waiting 10 seconds before live trading as a security measure!')
            time.sleep(10)

    remove_external_signals('buy')
    remove_external_signals('sell')
    remove_external_signals('pause')

    # load signalling modules
    signalthreads = start_signal_threads()

    # seed initial prices
    #get_price()
    wrap_get_price() 
    TIMEOUT_COUNT=0
    READ_CONNECTERR_COUNT=0
    BINANCE_API_EXCEPTION=0

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
            
            if RESTART_EXTSIGNALS and thehour != datetime.now().hour :
                restart_signal_threads()
                thehour = datetime.now().hour

        except ReadTimeout as rt:
            TIMEOUT_COUNT += 1
            print(f'We got a timeout error from Binance. Re-loop. Connection Timeouts so far: {TIMEOUT_COUNT}')
        except ConnectionError as ce:
            READ_CONNECTERR_COUNT += 1
            print(f'We got a connection error from Binance. Re-loop. Connection Errors so far: {READ_CONNECTERR_COUNT}')
        except BinanceAPIException as bapie:
            BINANCE_API_EXCEPTION += 1
            print(f'We got an API error from Binance. Re-loop. API Errors so far: {BINANCE_API_EXCEPTION}.\nException:\n{bapie}')
        except KeyboardInterrupt as ki:
            # stop external signal threads
            stop_signal_threads()

            while True:
                #print_notimestamp(f'{txcolors.WARNING}\n--|  Binance Bot Menu  |--{txcolors.DEFAULT}')
                print_notimestamp(f'\n[1] Exit (default option)')
                print_notimestamp(f'\n[2] Sell All Coins')
                print_notimestamp(f'\n[3] Sell A Specific Coin')
                print_notimestamp(f'\n[4] Resume Bot')
                print_notimestamp(f'\n{txcolors.WARNING}Please choose one of the above menu options ([1]. Exit):{txcolors.DEFAULT}')
                menuoption = input()

                if menuoption == "1" or menuoption == "":
                    print_notimestamp('\n')
                    sys.exit(0)
                elif menuoption == "2":
                    print_notimestamp('\n')
                    sell_all('Sell All Coins menu option chosen!')
                    print_notimestamp('\n')
                elif menuoption == "3":
                    while not menuoption.upper() == "N":
                        # setup table
                        my_table = PrettyTable()
                        my_table.field_names = ["Symbol", "Volume", "Bought At", "Now At", "TP %", "SL %", "Change % (ex fees)", "Profit $", "Time Held"]
                        my_table.align["Symbol"] = "l"
                        my_table.align["Volume"] = "r"
                        my_table.align["Bought At"] = "r"
                        my_table.align["Now At"] = "r"
                        my_table.align["TP %"] = "r"
                        my_table.align["SL %"] = "r"
                        my_table.align["Change % (ex fees)"] = "r"
                        my_table.align["Profit $"] = "r"
                        my_table.align["Time Held"] = "l"

                        # get latest prices
                        last_price = wrap_get_price()

                        # display coins to sell
                        #print('\n')
                        for coin in coins_bought:
                            time_held = timedelta(seconds=datetime.now().timestamp()-int(str(coins_bought[coin]['timestamp'])[:10]))
                            change_perc = (float(last_price[coin]['price']) - float(coins_bought[coin]['bought_at']))/float(coins_bought[coin]['bought_at']) * 100
                            ProfitExFees = float(last_price[coin]['price']) - float(coins_bought[coin]['bought_at'])
                            my_table.add_row([f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{coin}{txcolors.DEFAULT}",
                                            f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{float(coins_bought[coin]['volume']):.6f}{txcolors.DEFAULT}",
                                            f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{float(coins_bought[coin]['bought_at']):.6f}{txcolors.DEFAULT}",
                                            f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{float(last_price[coin]['price']):.6f}{txcolors.DEFAULT}",
                                            f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{float(coins_bought[coin]['take_profit']):.4f}{txcolors.DEFAULT}",
                                            f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{float(coins_bought[coin]['stop_loss']):.4f}{txcolors.DEFAULT}",
                                            f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{change_perc:.4f}{txcolors.DEFAULT}",
                                            f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{(float(coins_bought[coin]['volume'])*float(coins_bought[coin]['bought_at'])*change_perc)/100:.6f}{txcolors.DEFAULT}",
                                            f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{str(time_held).split('.')[0]}{txcolors.DEFAULT}"])
                            
                        my_table.sortby = 'Change % (ex fees)'
                        if len(my_table._rows) > 0:
                            print_notimestamp(my_table)
                        else:
                            break

                        # ask for coin to sell
                        print_notimestamp(f'{txcolors.WARNING}\nType in the Symbol you wish to sell, including pair (i.e. BTCUSDT) or type N to return to Menu (N)?{txcolors.DEFAULT}')
                        menuoption = input()
                        if menuoption == "":
                            break

                        sell_a_specific_coin(menuoption.upper())         
                elif menuoption == "4":
                   print_notimestamp(f'{txcolors.WARNING}\nResuming the bot...\n\n{txcolors.DEFAULT}')
                   start_signal_threads()
                   break

            
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
            print(f'Bot terminated for some reason.')