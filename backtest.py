# -*- coding: utf-8 -*-
#!/usr/bin/python
#backtest.py
from __future__ import print_function

"""
Created on Thu May 23 20:40:04 2019

@author: OBar
"""

import datetime
import pprint
import queue

import time
import matplotlib.pyplot as mp

"""
The Backtest object is designed to carry out a nested while-loop event-driven system in
order to handle the events placed on the Event Queue object. The outer while-loop is known as
the "heartbeat loop" and decides the temporal resolution of the backtesting system. In a live
environment this value will be a positive number, such as 600 seconds (every ten minutes). Thus
the market data and positions will only be updated on this timeframe.

The inner while-loop actually processes the signals and sends them to the correct component
depending upon the event type. Thus the Event Queue is continually being populated and
depopulated with events. This is what it means for a system to be event-driven.

The first task is to import the necessary libraries. We import pprint ("pretty-print"), because
we want to display the stats in an output-friendly manner:
"""


class Backtest(object):
    """
    Encapsulates the settings and compenents for carrying out an event-driven backtest.
    """
    def __init__(
            self, csv_dir, symbol_list, initial_capital,
            heartbeat, start_date, data_handler,
            execution_handler, portfolio, strategy
            ):
        """
        Initilises the backtest
        Parameters:
        csv_dir - The hard root to the CSV data directory.
        symbol_list - The list of symbol strings.
        intial_capital - The starting capital for the portfolio.
        heartbeat - Backtest "heartbeat" in seconds
        start_date - The start datetime of the strategy.
        data_handler - (Class) Handles the market data feed.
        execution_handler - (Class) Handles the orders/fills for trades.
        portfolio - (Class) Keeps track of portfolio current
        and prior positions.
        strategy - (Class) Generates signals based on market data.
        """
        self.csv_dir = csv_dir
        self.symbol_list = symbol_list
        self.initial_capital = initial_capital
        self.heartbeat = heartbeat
        self.start_date = start_date
        
        self.data_handler_cls = data_handler
        self.execution_handler_cls = execution_handler
        self.portfolio_cls = portfolio
        self.strategy_cls = strategy
        
        self.events = queue.Queue()
        
        self.signals = 0
        self.orders = 0
        self.fills = 0
        self.num_strats = 1
        
        self._generate_trading_instances()
        
    def _generate_trading_instances(self):
        """
        Generates the trading instance objects from their class types
        """
        print("Creating DataHandler, Strategy, Portfolio, and ExecutionHandler"
              )
        self.data_handler = self.data_handler_cls(self.events, self.csv_dir, self.symbol_list)
        self.strategy = self.strategy_cls(self.data_handler, self.events)
        self.portfolio = self.portfolio_cls(
                self.data_handler, self.events, self.start_date, self.initial_capital)
        self.execution_handler = self.execution_handler_cls(self.events)
            
            
    def _run_backtest(self):
        """
        Executes the backtest
        """
        i = 0
        while True:
            i +=1
            print(i)
            #update the market bars
            if self.data_handler.continue_backtest == True:
                self.data_handler.update_bars()
            else:
                break
            
            #handle the events
            while True:
                try:
                    event = self.events.get(False)
                except queue.Empty:
                    break
                else:
                    if event is not None:
                        if event.type == 'MARKET':
                            self.strategy.calculate_signals(event)
                            self.portfolio.update_timeindex(event)
                        elif event.type == 'SIGNAL':
                            self.signals +=1
                            self.portfolio.update_signal(event)
                            
                        elif event.type == 'ORDER':
                            self.orders +=1
                            self.execution_handler.execute_order(event)
                            
                        elif event.type == 'FILL':
                            self.fills +=1
                            self.portfolio.update_fill(event)
                            
            time.sleep(self.heartbeat)
        
    def _output_performance(self):
        """
        Outputs the strategy performance from the backtest.
        """
        self.portfolio.create_equity_curve_dataframe()
        
        print("Creating summary stats...")
        stats = self.portfolio.output_summary_stats()
        print("Creating Equity Curve...")
        print(self.portfolio.equity_curve.tail(10))
        pprint.pprint(stats)
        
        print("Signals: {}".format(self.signals))
        print("Orders: {}".format(self.orders))
        print("Fills: {}".format(self.fills))
        """
        Outputs the Portfolio Value, Returns, and Drawdown graphs
        """
        mp.subplot(3, 1, 1)
        mp.plot(self.portfolio.equity_curve.index.values, (self.portfolio.equity_curve['total']/10000.0))
        mp.subplot(3, 1, 2)
        mp.plot(self.portfolio.equity_curve.index.values, self.portfolio.equity_curve['returns'])
        mp.subplot(3, 1, 3)
        mp.plot(self.portfolio.equity_curve.index.values, self.portfolio.equity_curve['drawdown'])
        mp.show()
        
    def simulate_trading(self):
        """
        Simulates the backtest and outputs portfolio performance
        """
        self._run_backtest()
        self._output_performance()
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        