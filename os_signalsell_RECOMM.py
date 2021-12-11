# Based off Firewatch custsignalmod.py

from tradingview_ta import TA_Handler, Interval, Exchange
# use for environment variables
import os
# use if needed to pass args to external modules
import sys
# used for directory handling
import glob
import threading
import time

MY_EXCHANGE = 'BINANCE'
MY_SCREENER = 'CRYPTO'
MY_FIRST_INTERVAL = Interval.INTERVAL_1_MINUTE
MY_SECOND_INTERVAL = Interval.INTERVAL_5_MINUTES
MY_THIRD_INTERVAL = Interval.INTERVAL_15_MINUTES
PAIR_WITH = 'USDT'
DEBUG = True

TIME_TO_WAIT = 1 # Minutes to wait between analysis
SIGNAL_NAME = 'os_signalsell_RECOMM'
SIGNAL_FILE = 'signals/' + SIGNAL_NAME + '.sell'
TRADINGVIEW_EX_FILE = 'tradingview_ta_unknown'

###
### NOTE: The TICKERS file is created by the main "Binance Detect Moonings.py" module
###       This is dynamically created based on the coins the bot is currently holding.
###
TICKERS = 'signalsell_tickers.txt'
SELL_TICKERS = 'signalsell_tickers.txt'

# if DEBUG: TICKERS = 'test_' + TICKERS

def analyze(pairs):
    taMax = 0
    taMaxCoin = 'none'
    signal_coins = {}
    first_analysis = {}
    second_analysis = {}
    third_analysis = {}
    first_handler = {}
    second_handler = {}
    third_handler = {}
    
    if os.path.exists(SIGNAL_FILE):
        os.remove(SIGNAL_FILE)

    if os.path.exists(TRADINGVIEW_EX_FILE):
        os.remove(TRADINGVIEW_EX_FILE)

    for pair in pairs:
        first_handler[pair] = TA_Handler(
            symbol=pair,
            exchange=MY_EXCHANGE,
            screener=MY_SCREENER,
            interval=MY_FIRST_INTERVAL,
            timeout= 10
        )
        second_handler[pair] = TA_Handler(
            symbol=pair,
            exchange=MY_EXCHANGE,
            screener=MY_SCREENER,
            interval=MY_SECOND_INTERVAL,
            timeout= 10
        )
        third_handler[pair] = TA_Handler(
            symbol=pair,
            exchange=MY_EXCHANGE,
            screener=MY_SCREENER,
            interval=MY_THIRD_INTERVAL,
            timeout= 10
        )

    for pair in pairs:
       
        try:
            first_analysis = first_handler[pair].get_analysis()
            second_analysis = second_handler[pair].get_analysis()
            third_analysis = third_handler[pair].get_analysis()
        except Exception as e:
            print(f'{SIGNAL_NAME}')
            print("Exception:")
            print(e)
            print (f'Coin: {pair}')
            print (f'First handler: {first_handler[pair]}')
            print (f'Second handler: {second_handler[pair]}')
            print (f'Second handler: {third_handler[pair]}')
            with open(TRADINGVIEW_EX_FILE,'a+') as f:
                    f.write(pair.removesuffix(PAIR_WITH) + '\n')
            continue
               
        first_recommendation = first_analysis.summary['RECOMMENDATION']
        second_recommendation = second_analysis.summary['RECOMMENDATION']
        third_recommendation = third_analysis.summary['RECOMMENDATION']
        
        if DEBUG:
            print(f'{SIGNAL_NAME}: {pair} First {first_recommendation} Second {second_recommendation} Third {third_recommendation}')
                
        if  (first_recommendation == "SELL" or first_recommendation == "STRONG_SELL") and \
            (second_recommendation == "SELL" or second_recommendation == "STRONG_SELL") and \
            (third_recommendation == "SELL" or third_recommendation == "STRONG_SELL"):

            print(f'{SIGNAL_NAME}: sell signal detected on {pair}')

            signal_coins[pair] = pair
            
            with open(SIGNAL_FILE,'a+') as f:
                f.write(pair + '\n')

    return signal_coins

def do_work():
    while True:
        try:
            if not os.path.exists(SELL_TICKERS):
                time.sleep((TIME_TO_WAIT*60))
                continue

            signal_coins = {}
            pairs = {}

            pairs=[line.strip() for line in open(SELL_TICKERS)]
            for line in open(SELL_TICKERS):
                pairs=[line.strip() + PAIR_WITH for line in open(SELL_TICKERS)] 
            
            if not threading.main_thread().is_alive(): exit()
            print(f'{SIGNAL_NAME}: Analyzing {len(pairs)} coins')
            signal_coins = analyze(pairs)
            print(f'{SIGNAL_NAME}: {len(signal_coins)} coins with Sell Signals. Waiting {TIME_TO_WAIT} minutes for next analysis.')

            time.sleep((TIME_TO_WAIT*60))
        except Exception as e:
            print(f'{SIGNAL_NAME}: Exception: {e}')
            continue
        except KeyboardInterrupt as ki:
            continue