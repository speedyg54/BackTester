#!/usr/bin/python
# -*- coding: utf-8 -*-

#snp_forecast.py
from __future__ import print_function

"""
Created on Tue May 28 18:59:56 2019

@author: OBar
"""

import datetime
import pandas as pd
import sys
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis as QDA

from event_driven_trading.strategy import Strategy
from event_driven_trading.event import SignalEvent
from event_driven_trading.backtest import Backtest
from event_driven_trading.data import HistoricCSVDataHandler
from event_driven_trading.execution import SimulatedExecutionHandler
from event_driven_trading.portfolio import Portfolio
from event_driven_trading.create_lagged_series import create_lagged_series



class SPYDailyForecastStrategy(Strategy):
    """
    SP500 forecast strategy. It uses a quadratic discriminant analyser
    to predict the returns for a subsequent time period and then generated
    long/exit signals based on the prediction
    """
    def __init__(self, bars, events):
        self.bars = bars
        self.symbol_list = self.bars.symbol_list
        self.events = events
        self.datetime_now = datetime.datetime.utcnow()
        
        self.model_start_date = datetime.datetime(2001, 1, 10)
        self.model_end_date = datetime.datetime(2005,12,31)
        self.model_start_test_date = datetime.datetime(2005,1,1)
        
        self.long_market = False
        self.short_market = False
        self.bar_index = 0
        
        self.model = self.create_symbol_forecast_model()
        
        
    def create_symbol_forecast_model(self):
        #Create a lagged series of the SP500 Stock market
        snpret = create_lagged_series(
                self.symbol_list[0], self.model_start_date,
                self.model_end_date, lags=5
                )
        
        ##use the prior two days of returns as predictors
        X = snpret[["Lag1", "Lag2"]]
        y = snpret["Direction"]
        
        #Create training and test sets
        start_test = self.model_start_test_date
        X_train = X[X.index < start_test]
        X_test = X[X.index >= start_test]
        y_train = y[y.index < start_test]
        y_test = y[y.index >= start_test]
        """
        NOTE: we can replace the model with a random fores, SVM, or 
        Logit Regression. just import the library and change the model=QDA()
        line
        """
        model = QDA()
        model.fit(X_train, y_train)
        return model          
    #now to override the calculate_signals method of the Strat base class
    def calculate_signals(self, event):
        """
        Calculate the signalevents based on marketdata.
        
        We wait for five bars to have elapsed (i.e. five days in this strategy!) and then obtain the
        lagged returns values. We then wrap these values in a Pandas Series so that the predict method
        of the model will function correctly. We then calculate a prediction, which manifests itself as a
        +1 or -1. If the prediction is a +1 and we are not already long the market, we create a SignalEvent
        to go long and let the class know we are now in the market. If the prediction is -1 and we are
        long the market, then we simply exit the market:
        """
        sym = self.symbol_list[0]
        dt = self.datetime_now
    
        if event.type == 'MARKET':
            self.bar_index += 1
            if self.bar_index > 5:
                #the 'adj_close' field below needs to be returns. but no returns data exists in the data.py file
                lags = self.bars.get_latest_bars_values(
                        self.symbol_list[0], "adj_close", N=3
                )
                pred_series = ([[lags[1]*100.0, lags[2]*100.0]])
                """
                pd.Series(
                        {
                                'Lag1': lags[1]*100.0,
                                'Lag2': lags[2]*100.0
                        }
                )
                """
                pred = self.model.predict(pred_series)
                if pred > 0 and not self.long_market:
                    self.long_market = True
                    signal = SignalEvent(1, sym, dt, 'LONG', 1.0)
                    self.events.put(signal)
                    
                if pred < 0 and self.long_market:
                    self.long_market = False
                    signal = SignalEvent(1, sym, dt, 'EXIT', 1.0)
                    self.events.put(signal)
                    
#now carry out the backtest
if __name__ == '__main__':
    csv_dir =  "C:\\Users\\OBar\\Documents\\Quant Trading Research\\QuantStart\\Scripts\\event_driven_trading\\"
    symbol_list = ['SPY']
    initial_capital = 100000.0 #100k
    heartbeat = 0.0
    start_date = datetime.datetime(2006, 1, 3)
    
    #include a log file for good measure
    sys.stdout = open(csv_dir + "\log_snpy_forecast.txt", 'w')
    
    
    backtest = Backtest(
            csv_dir, symbol_list, initial_capital, heartbeat,
            start_date, HistoricCSVDataHandler, SimulatedExecutionHandler,
            Portfolio, SPYDailyForecastStrategy)
    backtest.simulate_trading()
                   
                   
                   
                   
                   
                   
                   
                   
                 