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
import array
import statistics
import numpy as np

from analysis_buffer import AnalysisBuffer

class txcolors:
    BUY = '\033[92m'
    WARNING = '\033[93m'
    SELL_LOSS = '\033[91m'
    SELL_PROFIT = '\033[32m'
    DIM = '\033[2m\033[35m'
    DEFAULT = '\033[39m'

OSC_INDICATORS = ['RSI', 'Stoch.RSI'] # Indicators to use in Oscillator analysis
OSC_THRESHOLD = 2 # Must be less or equal to number of items in OSC_INDICATORS 
MA_INDICATORS = ['EMA10', 'EMA20'] # Indicators to use in Moving averages analysis
MA_THRESHOLD = 2 # Must be less or equal to number of items in MA_INDICATORS 
INTERVAL = Interval.INTERVAL_5_MINUTES #Timeframe for analysis
INTERVAL_IN_MINUTES = 5 # interval in minutes
NUM_CANDLES = 20 # number of candles to be cached in buffer... e.g. the maximum number of candles you want to go back in time for

EXCHANGE = 'BINANCE'
SCREENER = 'CRYPTO'
PAIR_WITH = 'USDT'

###
### NOTE: The SELL_TICKERS file is created by the main "Binance Detect Moonings.py" module
###       This is dynamically created based on the coins the bot is currently holding.
###
SELL_TICKERS = 'signalsell_tickers.txt'

TIME_TO_WAIT = 1 # Minutes to wait between analysis
FULL_LOG = False # List analysis result to console
DEBUG = True

SIGNAL_NAME = 'djcommie_signalsell_rsi_stoch'
SIGNAL_FILE_SELL = 'signals/' + SIGNAL_NAME + '.sell'

TRADINGVIEW_EX_FILE = 'tradingview_ta_unknown'

# TODO: check every 1 minute on 5 minute timeframes by keeping a circular buffer array 
global coin_analysis
coin_analysis = {}

def analyze(pairs):
    global last_RSI

    signal_coins = {}
    analysis = {}
    handler = {}
    
    if os.path.exists(SIGNAL_FILE_SELL):
        os.remove(SIGNAL_FILE_SELL)
        
    if os.path.exists(TRADINGVIEW_EX_FILE):
        os.remove(TRADINGVIEW_EX_FILE)

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
            print(f'{SIGNAL_NAME}Exception:')
            print(e)
            print (f'Coin: {pair}')
            print (f'handler: {handler1MIN[pair]}')
            print (f'handler2: {handler5MIN[pair]}')
            with open(TRADINGVIEW_EX_FILE,'a+') as f:
                    f.write(pair.removesuffix(PAIR_WITH) + '\n')
            continue

        oscCheck=0
        maCheck=0
        for indicator in OSC_INDICATORS:
            oscResult = analysis.oscillators ['COMPUTE'][indicator]
            #print(f'Indicator for {indicator} is {oscResult}')
            if analysis.oscillators ['COMPUTE'][indicator] != 'SELL': oscCheck +=1
      	
        for indicator in MA_INDICATORS:
            if analysis.moving_averages ['COMPUTE'][indicator] == 'BUY': maCheck +=1

        if (pair not in coin_analysis):
            print(f'create new analysis buffer for pair {pair}')
            coin_analysis[pair] = AnalysisBuffer(TIME_TO_WAIT, INTERVAL_IN_MINUTES, NUM_CANDLES * 3)

        coin_analysis[pair].put(analysis)
        prev_candle_analysis = coin_analysis[pair].get_prev_candle()
        prev_RSI = -1
        if (prev_candle_analysis is not None):
            prev_RSI = coin_analysis[pair].get_prev_candle().indicators['RSI']

        # Stoch.RSI (25 - 52) & Stoch.RSI.K > Stoch.RSI.D, RSI (49-67), EMA10 > EMA20 > EMA100, Stoch.RSI = BUY, RSI = BUY, EMA10 = EMA20 = BUY
        RSI = float(analysis.indicators['RSI'])
        STOCH_RSI_K = float(analysis.indicators['Stoch.RSI.K'])
        EMA10 = float(analysis.indicators['EMA10'])
        EMA20 = float(analysis.indicators['EMA20'])
        EMA100 = float(analysis.indicators['EMA100'])
        STOCH_K = float(analysis.indicators['Stoch.K'])
        STOCH_D = float(analysis.indicators['Stoch.D'])

        RSI_list = coin_analysis[pair].get_indicator_list('RSI', int(NUM_CANDLES * 3.5))
        action = 'NADA'
        if (RSI_list is not None):
            action = RSI_BB_dispersion(RSI_list[::-1], NUM_CANDLES, RSI)

        if action == 'SELL':
            signal_coins[pair] = pair
            print(f'{txcolors.SELL}{SIGNAL_NAME}: {pair} - Sell Signal Detected{txcolors.DEFAULT}')

            with open(SIGNAL_FILE_SELL,'a+') as f:
                f.write(pair + '\n')
            
            timestamp = datetime.now().strftime("%d/%m %H:%M:%S")
            with open(SIGNAL_NAME + '.log','a+') as f:
                f.write(timestamp + ' ' + pair + '\n')
                f.write(f'    Signals: {action} - maCheck: {maCheck} MA_THRESHOLD: {MA_THRESHOLD} EMA10: {EMA10} EMA20: {EMA20} STOCH_K: {STOCH_K} STOCH_D: {STOCH_D} RSI: {RSI}\n')
        elif action == 'NADA':
            if FULL_LOG:
                print(f'{SIGNAL_NAME}: {pair} - not enough signal to sell')

        if FULL_LOG:
            print(f'{SIGNAL_NAME}:{pair} Oscillators:{oscCheck}/{len(OSC_INDICATORS)} Moving averages:{maCheck}/{len(MA_INDICATORS)}, trading action:{action}')
    
    return signal_coins

def RSI_BB_dispersion(RSI_buffer, for_ma, current_RSI):
    for_rsi = 14
    for_mult = 2
    for_sigma = 0.1

    if RSI_buffer is None:
        return
    #current_RSI = RSI_buffer[for_ma]
    # get the EMA of the 20 RSIs
    basis = calculate_ema(RSI_buffer, for_ma)[-1]
    # get the deviation
    dev = for_mult * statistics.stdev(RSI_buffer[:for_ma])
    upper = basis + dev
    lower = basis - dev
    disp_up = basis + ((upper - lower) * for_sigma)
    disp_down = basis - ((upper - lower) * for_sigma) 
    
    #print(f'RSI_BB_dispersion: current_RSI: {current_RSI}, disp_up: {disp_up}, disp_down: {disp_down}')

    if current_RSI >= disp_up:
        #print(f'RSI_BB_dispersion: Buy!!')
        return 'BUY'
    elif current_RSI <= disp_down:
        #print(f'RSI_BB_dispersion: Sell!')
        return 'SELL'
    else:
        #print(f'RSI_BB_dispersion: Do nada') 
        return 'NADA'

def calculate_ema(prices, days, smoothing=2):
    ema = [sum(prices[:days]) / days]
    for price in prices[days:]:
        ema.append((price * (smoothing / (1 + days))) + ema[-1] * (1 - (smoothing / (1 + days))))
    return ema

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
            print(f'{SIGNAL_NAME}: Exception do_work() 1: {e}')
            continue
        except KeyboardInterrupt as ki:
            continue
