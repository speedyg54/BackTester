# -*- coding: utf-8 -*-
#mac.py
"""
Created on Fri May 24 17:38:39 2019

@author: OBar
"""

from __future__ import print_function

import datetime

import numpy as np
import pandas as pd
import statsmodels.api as sm
import sys
from event_driven_trading.strategy import Strategy
from event_driven_trading.event import SignalEvent
from event_driven_trading.backtest import Backtest
from event_driven_trading.data import HistoricCSVDataHandler
from event_driven_trading.execution import SimulatedExecutionHandler
from event_driven_trading.portfolio import Portfolio

class MovingAverageCrossStrategy(Strategy):
    """
    Carries out a basic movin average crossover strategy with a short/long
    simple weighted moving average. Default short/long windows are 100/400
    periods
    """
    def __init__(
            self, bars, events, short_window=100, long_window=400 ):
        """
        Initialises the moving average cross strategy
        """
        self.bars = bars
        self.symbol_list = self.bars.symbol_list
        self.events = events
        self.short_window = short_window
        self.long_window = long_window
        
        #set to True if a symbol is in the market
        self.bought = self._calculate_initial_bought()
    def _calculate_initial_bought(self):
        """
        Adds keys to the bought dictionary for all symbols and sets them to out
        """
        bought = {}
        for s in self.symbol_list:
            bought[s] = 'OUT'
        return bought
    """
    The core of the strategy is the calculate_signals method. It reacts to a MarketEvent
    object and for each symbol traded obtains the latest N bar closing prices, where N is equal to
    the largest lookback period.
    It then calculates both the short and long period simple moving averages. The rule of the
    strategy is to enter the market (go long a stock) when the short moving average value exceeds
    the long moving average value.
    
    The logic is handled by placing a signalevent on the events queue in each of
    the respective situations and then updating the bought attribute (per symbol)
    to be long or short.
    """
    def calculate_signals(self, event):
        if event.type == 'MARKET':
            for s in self.symbol_list:
                bars = self.bars.get_latest_bars_values(
                        s, "adj_close", N=self.long_window)
                bar_date = self.bars.get_latest_bar_datetime(s)
                if bars is not None and bars != []:
                    short_sma = np.mean(bars[-self.short_window:])
                    long_sma = np.mean(bars[-self.long_window:])
                    
                    symbol = s
                    dt = datetime.datetime.utcnow()
                    sig_dir = ""
                    if short_sma > long_sma and self.bought[s] == 'OUT':
                        print("Long: {}".format(bar_date))
                        sig_dir = 'LONG'
                        signal = SignalEvent(1, symbol, dt, sig_dir, 1.0)
                        self.events.put(signal)
                        self.bought[s] = 'LONG'
                    elif short_sma < long_sma and self.bought[s] == 'LONG':
                        print("SHORT: {}".format(bar_date))
                        sig_dir = 'EXIT'
                        signal = SignalEvent(1, symbol, dt, sig_dir, 1.0)
                        self.events.put(signal)
                        self.bought[s] = 'OUT'
                        
"""
last thing to do is make the main function
and implement the strategy
"""
if __name__ == '__main__':
    csv_dir = "C:\\Users\\OBar\\Documents\\Quant Trading Research\\QuantStart\\Scripts\\event_driven_trading\\"
    symbol_list = ['AAPL']
    initial_capital = 10000.0
    heartbeat = 0.0
    start_date = datetime.datetime(1990, 1, 1, 0,0,0)
    
    #include a log file for good measure
    sys.stdout = open(csv_dir + "\log.txt", 'w')
    
#test nonsense    MovingAverageCrossStrategy.short_window=100
    backtest = Backtest(
            csv_dir, symbol_list, initial_capital, heartbeat,
            start_date, HistoricCSVDataHandler, SimulatedExecutionHandler,
            Portfolio, MovingAverageCrossStrategy
    )
    backtest.simulate_trading()
   
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    