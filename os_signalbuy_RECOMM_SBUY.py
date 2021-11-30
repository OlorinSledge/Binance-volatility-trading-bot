# Based off os_signalbuy_RECOMM
# Based off Firewatch custsignalmod.py

# Check TraidingView Technical analysis based on moving averages, oscillators, and the Summary Technical analysis that is based on both oscillators and moving averages.
# Check for BUY, STRONG_BUY, NEUTRAL signals in multiple intervals
# Keep only coins that pass the checks in all intervals.
# Use variables MY_INTERVALS MY_SINGNAL_STRENGTH to customize  your strategy. 
# For example, you can select only coins with STRONG_BUY and BUY signals on intervals from 1 minute to 4 hours. Mon18Oct2021Ci

from tradingview_ta import TA_Handler, Interval, Exchange
# use for environment variables
import os
# use if needed to pass args to external modules
import sys
# used for directory handling
import glob

import threading
import time

from helpers.parameters import parse_args, load_config

# Load creds modules
from helpers.handle_creds import (
    load_correct_creds
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
TICKERS = parsed_config['trading_options']['TICKERS_LIST']

MY_EXCHANGE = 'BINANCE'
MY_SCREENER = 'CRYPTO'
 
MY_INTERVALS=[
    Interval.INTERVAL_1_MINUTE,
    Interval.INTERVAL_5_MINUTES,
    Interval.INTERVAL_15_MINUTES,
    Interval.INTERVAL_30_MINUTES,
    Interval.INTERVAL_1_HOUR,
    Interval.INTERVAL_2_HOURS,
    Interval.INTERVAL_4_HOURS,
    Interval.INTERVAL_1_DAY
#    ,
#    Interval.INTERVAL_1_WEEK,
#    Interval.INTERVAL_1_MONTH
    ]

MY_SINGNAL_STRENGTH = [
    'STRONG_BUY',
    'BUY',
    'NEUTRAL'
    ]

TIME_TO_WAIT = 7 # Minutes to wait between analysis
FULL_LOG = True # List anylysis result to console

SIGNAL_NAME = 'os_signalbuy_RECOMM_SBUY'
SIGNAL_FILE = 'signals/' + SIGNAL_NAME + '.buy'

TRADINGVIEW_EX_FILE = 'tradingview_ta_unknown'

def analyze(pairs):
    signal_coins = {}
    the_handler = {}
    
    if os.path.exists(SIGNAL_FILE):
        os.remove(SIGNAL_FILE)

    if os.path.exists(TRADINGVIEW_EX_FILE):
        os.remove(TRADINGVIEW_EX_FILE)

    for pair in pairs:
        for interval in MY_INTERVALS:
            the_handler = TA_Handler(
                symbol=pair,
                exchange=MY_EXCHANGE,
                screener=MY_SCREENER,
                interval=interval,
                timeout= 10
            )             
            try:               
                the_analysis = the_handler.get_analysis()
            except Exception as e:
                print(f'{SIGNAL_NAME}')
                print("Exception:")
                print(e)
                print (f'Coin: {pair}')
                print (f'The handler interval: {interval}')
                print (f'The handler pair: {the_handler}')
                with open(TRADINGVIEW_EX_FILE,'a+') as f:
                        f.write(pair.removesuffix(PAIR_WITH) + '\n')
                continue

            try:               
                the_recommendation = the_analysis.summary['RECOMMENDATION']
                the_recommendation_osc = the_analysis.oscillators['RECOMMENDATION']
                the_recommendation_ma = the_analysis.moving_averages['RECOMMENDATION'] 
            except Exception as e:
                print(f'{SIGNAL_NAME}')
                print("Exception:")
                print(e)
                print (f'Coin: {pair}')
                print (f'The handler interval: {interval}')
                print (f'The handler pair: {the_handler}')
                with open(TRADINGVIEW_EX_FILE,'a+') as f:
                        f.write(pair.removesuffix(PAIR_WITH) + '\n')
                continue
             
            if FULL_LOG:
                
                print(f'{SIGNAL_NAME}: {pair} \n'
                    f'Interval {interval} recommendation {the_recommendation}\n'
                    f'Interval {interval} recommendation osc {the_recommendation_osc}\n'
                    f'Interval {interval} recommendation ma {the_recommendation_ma}\n'
                    )
                if interval == MY_INTERVALS[-1]: print("This is last interval to check, going to next coin")
 
            if (the_recommendation in MY_SINGNAL_STRENGTH and \
                the_recommendation_osc in MY_SINGNAL_STRENGTH and \
                the_recommendation_ma in MY_SINGNAL_STRENGTH):            
                    print(f'#########{SIGNAL_NAME}: buy signal detected on {pair} in {interval}')
                    if interval == MY_INTERVALS[-1]: 
                        print(" ++++++++++++++++++++++++Ccoin this coin wins+++++++++++++++++++++++++++++++++++++++++++++++ ")
                        signal_coins[pair] = pair          
                        with open(SIGNAL_FILE,'a+') as f: f.write(pair + '\n')
            else: break

    return signal_coins

def do_work():
    while True:
        try:
            if not os.path.exists(TICKERS):
                time.sleep((TIME_TO_WAIT*60))
                continue

            signal_coins = {}
            pairs = {}

            pairs=[line.strip() for line in open(TICKERS)]
            for line in open(TICKERS):
                pairs=[line.strip() + PAIR_WITH for line in open(TICKERS)] 
            
            if not threading.main_thread().is_alive(): exit()
            print(f'{SIGNAL_NAME}: Analyzing {len(pairs)} coins')
            signal_coins = analyze(pairs)
            print(f'{SIGNAL_NAME}: {len(signal_coins)} coins with Buy Signals. Waiting {TIME_TO_WAIT} minutes for next analysis.')

            time.sleep((TIME_TO_WAIT*60))
        #except Exception as e:
        #    print(f'{SIGNAL_NAME}: Exception do_work() 1: {e}')
        #    continue
        except KeyboardInterrupt as ki:
            continue
