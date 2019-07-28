#!/usr/bin/python
# -*- coding: utf-8 -*-
#data.py
from __future__ import print_function
"""
Created on Wed May 22 18:27:41 2019

@author: OBar
"""

from abc import ABCMeta, abstractmethod #to define abstract base classes
import datetime
import os, os.path

import numpy as np
import pandas as pd

from event_driven_trading.event import MarketEvent

class DataHandler(object): #abstract parent class
    """
    DataHandler is an Abstract Base Class providing an interface for
    all subsequent (inherited) data handlers (both live and historic).
    
    The goal of a derived datahandler object is to output a generated
    set of bars (OHLCVI) for each symbol requested.
    
    This will replicate how a live strategy would function as current 
    market data would be sent 'down the pipe'. thus a historic and live
    system will be treated identitically by the rest of the backtesting suite.
    """
    
    __metaclass__ = ABCMeta
    
    @abstractmethod
    def get_latest_bar(self, symbol):
        """
        Returns last bar updated
        """
        raise NotImplementedError("Should implement get_latest_bar()")
        
    @abstractmethod
    def get_latest_bars(self, symbol, N=1):
        """
        Returns the last N bars updated.
        """
        raise NotImplementedError("SHould implement get_latest_bars()")
        
    
    @abstractmethod
    def get_latest_bar_datetime(self,symbol):
        """
        returns a python datetime object for the last bar.
        """
        raise NotImplementedError("Should implement get_latest_bar_datetime()")
        
    @abstractmethod
    def get_latest_bar_value(self, symbol, val_type):
        """
        Returns one of the Open, High, Low, Close, Volume or OI
        from the last bar.
        """
        raise NotImplementedError("Should implement get_latest_bar_value()")
        
    @abstractmethod
    def get_latest_bars_values(self, symbol, val_type, N=1):
        """
        Returns the latest N bar values from the latest_symbol list,
        or N-k if less available
        """
        raise NotImplementedError("Should implement get_latest_bar_values()")
        
    @abstractmethod
    def update_bars(self):
        """
        Pushes the latest bars to the bars_queue for each symbol in a typle
        OHLCVI format: (datetime, open, high, low, close, volume, open int).
        """
        raise NotImplementedError("Should implement update_bars()")
        
    
"""
Building out a CSV handler because of simplicity. Ideally this would
be replaced with a database class to query the data for us. but this way
we aren't concerned with the 'boilerplate' code of connecting to a db
and using SQL.
"""
class HistoricCSVDataHandler(DataHandler):
    """
    HistoricCSVDataHandler is designed to read CSV files for
    each requested symbol from disk and provide an interface
    to obtain the "latest" bar in a manner identical to a live
    trading interface.
    """
    def __init__(self, events, csv_dir, symbol_list):
        """
        Initialises the historic data handler by requested the location
        of the CSV files and a list of symbols.
        
        It will be assumed that all files are of the form 'symbol.csv'
        where symbol is a string in the list.
        
        parameters:
            events - the event queue
            csv_dir - absolute directory path to the csv files
            symbol_list - a list of symbol strings.
            
        """
        self.events = events
        self.csv_dir = csv_dir
        self.symbol_list = symbol_list
        self.symbol_data = {}
        self.latest_symbol_data = {}
        self.continue_backtest = True
        
        self._open_convert_csv_files()
        
    def _open_convert_csv_files(self):
        """
        Opens the CSV files from the data directory, converting them into
        pandas dataframes within a symbol dictionary
         
        for this handler it will be assumed that the data is taken from yaoo
        """
        comb_index = None
        for s in self.symbol_list:
            ##print(os.path.join(self.csv_dir, '{}.csv'.format(s) ))
            #load the CSV file with no header inform, indexed on date
            self.symbol_data[s] = pd.read_csv(
                    os.path.join(self.csv_dir, '{}.csv'.format(s) ),
                    header=0, index_col=0, parse_dates=True,
                    names=[
                            'datetime', 'open', 'high', 'low'
                            ,'close', 'adj_close', 'volume'
                            ]).sort_index(axis=0)
            ##print(self.symbol_data[s].head())
            #combine the index to pad forward values
            if comb_index is None:
                comb_index = self.symbol_data[s].index
            else:
                comb_index.union(self.symbol_data[s].index)
                
            #set the latest symbol_data to None
            self.latest_symbol_data[s] = []
            
        #reindex the dataframes
        for s in self.symbol_list:
            self.symbol_data[s] = self.symbol_data[s].reindex(index=comb_index, method='pad').iterrows()
            
            
    def _get_new_bar(self, symbol):
        """
        Returns the latest bar from the data feed
        """
        for b in self.symbol_data[symbol]:
            yield b
    
    def get_latest_bar(self, symbol):
        """
        Returns the last bar from the latest_symbol list.
        """
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("That symbol is not available in the historical data set")
            raise
        else:
            return bars_list[-1]
        
    def get_latest_bars(self, symbol, N=1):
        """
        Returns the last N bars from the latest_Symbol list
        or N-K if less available.
        """
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return bars_list[-N:]
        
    def get_latest_bar_datetime(self, symbol):
        """
        Returns a python datetime object for the last bar.
        """
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return bars_list[-1][0] #first column of last record
        
    #following two methods make use of the getattr function. which
    #queries an object to see if a particular attrb exists on an object.
    #this allows us to be more flexible and to pass strings in.
    def get_latest_bar_value(self, symbol, val_type):
        """
        Returns one of the Open, High, Low, Close, Volume or OI
        values from the pandas Bar series object.
        """
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return getattr(bars_list[-1][1], val_type)
        
    def get_latest_bars_values(self, symbol, val_type, N=1):
        """
        Returns the last N bar values from the
        latest_symbol list, or N-k if less available.
        """
        try:
            bars_list = self.get_latest_bars(symbol, N)
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return np.array([getattr(b[1], val_type) for b in bars_list])
        
        
    def update_bars(self):
        """
        Pushes the latest bar to the latest_symbol_data structure
        for all symbols in the symbol list.
        """
        for s in self.symbol_list:
            try:
                bar = next(self._get_new_bar(s))
            except StopIteration:
                self.continue_backtest = False
            else:
                if bar is not None:
                    self.latest_symbol_data[s].append(bar)
        #.put is used for threading to put the market event into a queue
        self.events.put(MarketEvent())
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        