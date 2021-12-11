# Available indicators here: https://python-tradingview-ta.readthedocs.io/en/latest/usage.html#retrieving-the-analysis

from tradingview_ta import TA_Handler, Interval, Exchange
# use for environment variables
import os
# use if needed to pass args to external modules
import sys
# used for directory handling
import glob
# used for dates
from datetime import date, datetime, timedelta
import time
import threading

# my helper utils
from helpers.os_utils import(rchop)

from helpers.parameters import parse_args, load_config

args = parse_args()
DEFAULT_CONFIG_FILE = 'config.yml'

config_file = args.config if args.config else DEFAULT_CONFIG_FILE
parsed_config = load_config(config_file)

USE_MOST_VOLUME_COINS = parsed_config['trading_options']['USE_MOST_VOLUME_COINS']
PAIR_WITH = parsed_config['trading_options']['PAIR_WITH']

OSC_INDICATORS = ['MACD', 'Stoch.RSI', 'RSI'] # Indicators to use in Oscillator analysis
OSC_THRESHOLD = 3 # Must be less or equal to number of items in OSC_INDICATORS 
MA_INDICATORS = ['EMA20', 'EMA100', 'EMA200'] # Indicators to use in Moving averages analysis
MA_THRESHOLD = 3 # Must be less or equal to number of items in MA_INDICATORS 
INTERVAL = Interval.INTERVAL_1_MINUTE #Timeframe for analysis

EXCHANGE = 'BINANCE'
SCREENER = 'CRYPTO'

if USE_MOST_VOLUME_COINS == True:
        #if ABOVE_COINS_VOLUME == True:
    TICKERS = "volatile_volume_" + str(date.today()) + ".txt"
else:
    TICKERS = 'tickers.txt' #'signalsample.txt'
    
#TICKERS = 'signalsample.txt'
TIME_TO_WAIT = 1 # Minutes to wait between analysis
FULL_LOG = False # List analysis result to console

def analyze(pairs):
    signal_coins = {}
    analysis = {}
    handler = {}
    
    if os.path.exists('signals/custsignalmod.exs'):
        os.remove('signals/custsignalmod.exs')

    for pair in pairs:
        handler[pair] = TA_Handler(
            symbol=pair,
            exchange=EXCHANGE,
            screener=SCREENER,
            interval=INTERVAL,
            timeout= 10)
       
    for pair in pairs:
        try:
            analysis = handler[pair].get_analysis()
        except Exception as e:
            print("Signalsample:")
            print("Exception:")
            print(e)
            print (f'Coin: {pair}')
            print (f'handler: {handler[pair]}')

        oscCheck=0
        maCheck=0
        for indicator in OSC_INDICATORS:
            if analysis.oscillators ['COMPUTE'][indicator] == 'BUY': oscCheck +=1
      	
        for indicator in MA_INDICATORS:
            if analysis.moving_averages ['COMPUTE'][indicator] == 'BUY': maCheck +=1		

        if FULL_LOG:
            print(f'Custsignalmod:{pair} Oscillators:{oscCheck}/{len(OSC_INDICATORS)} Moving averages:{maCheck}/{len(MA_INDICATORS)}')
        
        if oscCheck >= OSC_THRESHOLD and maCheck >= MA_THRESHOLD:
                signal_coins[pair] = pair
                print(f'Custsignalmod: Signal detected on {pair} at {oscCheck}/{len(OSC_INDICATORS)} oscillators and {maCheck}/{len(MA_INDICATORS)} moving averages.')
                with open('signals/custsignalmod.exs','a+') as f:
                    f.write(pair + '\n')
    
    return signal_coins

def do_work():
    try:
        signal_coins = {}
        pairs = {}

        pairs=[line.strip() for line in open(TICKERS)]
        for line in open(TICKERS):
            pairs=[line.strip() + PAIR_WITH for line in open(TICKERS)] 
        
        while True:
            if not threading.main_thread().is_alive(): exit()
            print(f'Custsignalmod: Analyzing {len(pairs)} coins')
            signal_coins = analyze(pairs)
            print(f'Custsignalmod: {len(signal_coins)} coins above {OSC_THRESHOLD}/{len(OSC_INDICATORS)} oscillators and {MA_THRESHOLD}/{len(MA_INDICATORS)} moving averages Waiting {TIME_TO_WAIT} minutes for next analysis.')
            time.sleep((TIME_TO_WAIT*60))
    except Exception as e:
        print(f'{SIGNAL_NAME}: Exception do_work() 1: {e}')
        print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
        pass
    except KeyboardInterrupt as ki:
        pass