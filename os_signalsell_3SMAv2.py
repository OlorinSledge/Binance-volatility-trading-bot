from tradingview_ta import TA_Handler, Interval, Exchange
# used for dates
from datetime import date, datetime, timedelta
import time
# use for environment variables
import os
# use if needed to pass args to external modules
import sys
# used for directory handling
import glob
import time
import threading

# for colourful logging to the console
class txcolors:
    BUY = '\033[92m'
    WARNING = '\033[93m'
    SELL_LOSS = '\033[91m'
    SELL_PROFIT = '\033[32m'
    DIM = '\033[2m\033[35m'
    DEFAULT = '\033[39m'

INTERVAL5MIN = Interval.INTERVAL_5_MINUTES # Main Timeframe for analysis on Oscillators and Moving Averages (15 mins)
INTERVAL15MIN = Interval.INTERVAL_15_MINUTES # Main Timeframe for analysis on Oscillators and Moving Averages (15 mins)

EXCHANGE = 'BINANCE'
SCREENER = 'CRYPTO'
PAIR_WITH = 'USDT'

###
### NOTE: The SELL_TICKERS file is created by the main "Binance Detect Moonings.py" module
###       This is dynamically created based on the coins the bot is currently holding.
###
SELL_TICKERS = 'signalsell_tickers.txt'

TIME_TO_WAIT = 5 # Minutes to wait between analysis
DEBUG = False # List analysis result to console

SIGNAL_NAME = 'os_signalsell_3SMAv2'
SIGNAL_FILE_SELL = 'signals/' + SIGNAL_NAME + '.sell'

TRADINGVIEW_EX_FILE = 'tradingview_ta_unknown'

########################################
# Do NOT edit settings below these lines
########################################

def analyze(pairs):

    signal_coins = {}

    analysis5MIN = {}
    handler5MIN = {}

    analysis15MIN = {}
    handler15MIN = {}
    
    if os.path.exists(SIGNAL_FILE_SELL):
        os.remove(SIGNAL_FILE_SELL)
        
    if os.path.exists(TRADINGVIEW_EX_FILE):
        os.remove(TRADINGVIEW_EX_FILE)

    for pair in pairs:
        handler5MIN[pair] = TA_Handler(
            symbol=pair,
            exchange=EXCHANGE,
            screener=SCREENER,
            interval=INTERVAL5MIN,
            timeout= 10)
        handler15MIN[pair] = TA_Handler(
            symbol=pair,
            exchange=EXCHANGE,
            screener=SCREENER,
            interval=INTERVAL15MIN,
            timeout= 10)
                        
    for pair in pairs:
        try:
            analysis5MIN = handler5MIN[pair].get_analysis()
            analysis15MIN = handler15MIN[pair].get_analysis()
        except Exception as e:
            print(f'{SIGNAL_NAME} Exception:')
            print(e)
            print (f'Coin: {pair}')
            print (f'handler: {handler5MIN[pair]}')
            print (f'handler2: {handler15MIN[pair]}')
            with open(TRADINGVIEW_EX_FILE,'a+') as f:
                    f.write(pair.removesuffix(PAIR_WITH) + '\n')
            continue
        

        SMA20_5MIN = round(analysis5MIN.indicators['SMA20'],2)
        SMA50_5MIN = round(analysis5MIN.indicators['SMA50'],2)
        SMA100_5MIN = round(analysis5MIN.indicators['SMA100'],2)

        SMA20_15MIN = round(analysis15MIN.indicators['SMA20'],2)
        SMA50_15MIN = round(analysis15MIN.indicators['SMA50'],2)
        SMA100_15MIN = round(analysis15MIN.indicators['SMA100'],2)
        
        ACTION = 'NOTHING'
        
        # Sell condition on the 1 minute indicator
        # Buy condition on the 1 minute indicator
        if (SMA20_5MIN < SMA50_5MIN) or (SMA20_5MIN < SMA100_5MIN):            
            # SMA5 = green
            # SMA10 = blue 
            # SMA20 = red
            ACTION = 'SELL'

        if DEBUG:
            print(f'{SIGNAL_NAME} Signals {pair} {ACTION} - SMA100_5MIN: {SMA100_5MIN} SMA50_5MIN: {SMA50_5MIN} SMA20_5MIN: {SMA20_5MIN}')
            print(f'{SIGNAL_NAME} Signals {pair} {ACTION} - SMA100_15MIN: {SMA100_15MIN} SMA50_15MIN: {SMA50_15MIN} SMA20_15MIN: {SMA20_15MIN}')
      
        if ACTION == 'SELL':
            signal_coins[pair] = pair
            
            print(f'{txcolors.WARNING}{SIGNAL_NAME}: {pair} - Sell Signal Detected{txcolors.DEFAULT}')

            with open(SIGNAL_FILE_SELL,'a+') as f:
                f.write(pair + '\n')

            timestamp = datetime.now().strftime("%d/%m %H:%M:%S")
            with open(SIGNAL_NAME + '.log','a+') as f:
                f.write(timestamp + ' ' + pair + '\n')
                f.write(f'    Signals: {ACTION} - SMA100_5MIN: {SMA100_5MIN} SMA50_5MIN: {SMA50_5MIN} SMA20_5MIN: {SMA20_5MIN}\n')
                f.write(f'    Signals: {ACTION} - SMA100_15MIN: {SMA100_15MIN} SMA50_15MIN: {SMA50_15MIN} SMA20_15MIN: {SMA20_15MIN}\n')
        
        if ACTION == 'NOTHING':
            if DEBUG:
                print(f'{SIGNAL_NAME}: {pair} - not enough signal to sell')
            
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