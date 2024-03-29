#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function
"""
Created on Sat Jun  1 16:14:13 2019

@author: OBar
"""

import datetime
import numpy as np
import pandas as pd
import statsmodels.api as sm
from event_driven_trading.strategy import Strategy
from event_driven_trading.event import SignalEvent
from event_driven_trading.backtest import Backtest
from event_driven_trading.hft_data import HistoricCSVDataHandlerHFT
from event_driven_trading.hft_portfolio import PortfolioHFT
from event_driven_trading.execution import SimulatedExecutionHandler


class IntradayOLSMRStrategy(Strategy):
    """
    Uses ordinary least squares (OLS) to perform a rolling linear
    regression to determine the hedge ratio between a pair of equities.
    The z-score of the residuals time series is then calculated in a
    rolling fashion and if it exceeds an interval of thresholds
    (defaulting to [0.5, 3.0]) then a long/short signal pair are generated
    (for the high threshold) or an exit signal pair are generated (for the
    low threshold).
    """
    
    def __init__(
            self, bars, events, ols_window=100,
            zscore_low = 0.5, zscore_high=3.0):
        """
        Initialises the stat arb strategy.
        """
        self.bars = bars
        self.symbol_list = self.bars.symbol_list
        self.events = events
        self.ols_window = ols_window
        self.zscore_low = zscore_low
        self.zscore_high = zscore_high
        
        self.pair = ('AREX', 'WLL')
        self.datetime = datetime.datetime.utcnow()
        
        self.long_market = False
        self.short_market = False
        
    def calculate_xy_signals(self, zscore_last):
        """
        Calculates the actual x,y signal pairings to be sent to the
        signal generator.
        """
        y_signal = None
        x_signal = None
        p0 = self.pair[0]
        p1 = self.pair[1]
        dt = self.datetime
        hr = abs(self.hedge_ratio)
        
        #if we're long the market and below the
        #negative of the high zscore threshold
        if zscore_last <= -self.zscore_high and not self.long_market:
            self.long_market = True
            y_signal = SignalEvent(1, p0, dt, 'LONG', 1.0)
            x_signal = SignalEvent(1, p1, dt, 'SHORT', hr)
            
        #if we're long the market and between the absolute value
        #value of the low zscore threshold
        if abs(zscore_last) <= self.zscore_low and self.long_market:
            self.long_market = False
            y_signal = SignalEvent(1, p0, dt, 'EXIT', 1.0)
            x_signal = SignalEvent(1, p1, dt, 'EXIT', hr)
            
        #If we're short the market and above the high zscore threshold
        if zscore_last >= self.zscore_high and not self.short_market:
            self.short_market = True
            y_signal = SignalEvent(1, p0, dt, 'SHORT', 1.0)
            x_signal = SignalEvent(1, p1, dt, 'LONG', hr)
            
        #if we're short the market and between the abs value of the low zscore
        #threshold
        if abs(zscore_last) <= self.zscore_low and self.short_market:
            self.short_market = False
            y_signal = SignalEvent(1, p0, dt, 'EXIT', 1.0)
            x_signal = SignalEvent(1, p1, dt, 'EXIT', 1.0)
            
        return y_signal, x_signal
        
    def calculate_signals_for_pairs(self):
        """
        Generates a new set of signals based on the MR strategy
        calculates the hedge ratio between the paid of tickers.
        we use ols for this, ideally we'd use CADF
        """
        #obtain the latest window of values for each
        #component of the pair of tickers
        y = self.bars.get_latest_bars_values(
                self.paid[0], "close", N=self.ols_window
        )
        x = self.bars.get_latest_bars_values(
                self.pair[1], "close", N=self.ols_window
        )
        
        if y is not None and x is not None:
            #check that all window periods are available
            if len(y) >= self.ols_window and len(x) >= self.ols_window:
                #calculate the current hedge ratio using OLS
                self.hedge_ratio = sm.OLS(y, x).fit().params[0]
                
                #calculate the current z-score of the residuals
                spread = y - self.hedge_ratio * x
                zscore_last = ((spread - spread.mean())/spread.std())[-1]
                
                #calculate signals and add to events queue
                y_signal, x_signal = self.calculate_xy_signals(zscore_last)
                if y_signal is not None and x_signal is not None:
                    self.events.put(y_signal)
                    self.events.put(x_signal)
                        
    def calculate_signals(self, event):
        """
        Calculate the SignalEvents based on market data
        """
        if event.type == 'MARKET':
            self.calculate_signals_for_pairs()
            
if __name__ == "__main__":
    csv_dir = ''
    symbol_list = ["AREX","WLL"]
    initial_capital = 100000.0
    heartbeat = 0.0
    start_date = datetime.datetime(2001,11,8,10,41,0)
    
    backtest = Backtest(
            csv_dir, symbol_list, initial_capital, heartbeat,
            start_date, HistoricCSVDataHandlerHFT, SimulatedExecutionHandler,
            PortfolioHFT, IntradayOLSMRStrategy)
    backtest.simulate_trading()
    
        
        
        
        