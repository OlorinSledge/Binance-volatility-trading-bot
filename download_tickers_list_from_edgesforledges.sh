#!/bin/bash

fechahora=`date +%Y-%m-%d_%H-%M-%S`

wget -qO- http://edgesforledges.com/watchlists/download/binance/fiat/usdt/innovation-zone | sed 's/BINANCE\://g;s/USDT//g' > "tickers_INNOVATION_$fechahora.txt"
echo 
echo Download Completed...