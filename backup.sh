#!/bin/bash

fechahora=`date +%Y-%m-%d_%H-%M-%S`

echo Archivando live_bot_stats.json...
cp live_bot_stats.json "backup/live_bot_stats_$fechahora.json" 2>/dev/null
echo 
echo Archivando live_coins_bought
cp live_coins_bought.json "backup/live_coins_bought_$fechahora.json" 2>/dev/null
echo 
echo Archivando live_history
cp live_history.txt "backup/live_history_$fechahora.txt" 2>/dev/null
echo 
echo Archivando live_trades
cp live_trades.txt "backup/live_trades_$fechahora.txt" 2>/dev/null
echo 
echo Archivando signalsell_tickers
cp signalsell_tickers.txt "backup/signalsell_tickers_$fechahora.txt" 2>/dev/null
echo 
echo Archivando test_bot_stats
cp test_bot_stats.json "backup/test_bot_stats_$fechahora.json" 2>/dev/null
echo 
echo Archivando test_coins_bought
cp test_coins_bought.json "backup/test_coins_bought_$fechahora.json" 2>/dev/null
echo 
echo Archivando est_history
cp test_history.txt "backup/test_history_$fechahora.txt" 2>/dev/null
echo 
echo Archivando test_trades
cp test_trades.txt "backup/test_trades_$fechahora.txt" 2>/dev/null
echo 
echo BackUp Completo..