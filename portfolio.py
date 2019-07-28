# -*- coding: utf-8 -*-
#!/usr/bin/python
#portfolio.py
from __future__ import print_function
"""
Created on Thu May 23 17:41:35 2019

@author: OBar
"""
from math import floor #used to generate interger-valued order sizes.
import datetime
import queue
    
import numpy as np
import pandas as pd

from event_driven_trading.event import FillEvent, OrderEvent
from event_driven_trading.performance import create_sharpe_ratio, create_drawdowns


"""
The initialisation of the Portfolio object requires access to the bars DataHandler, the events
Event Queue, a start datetime stamp and an initial capital value (defaulting to 100,000 USD).
The Portfolio is designed to handle position sizing and current holdings, but will carry out
trading orders in a "dumb" manner by simply sending them directly to the brokerage with a
predetermined 
xed quantity size, irrespective of cash held. These are all unrealistic assumptions,
but they help to outline how a portfolio order management system (OMS) functions in an eventdriven fashion.
"""

class Portfolio(object):
    """
    The Portfolio class handles the positions and market
    value of all instruments at a resolution of a "bar",
    i.e. secondly, minutely, 5-min, 30-min, 60 min or EOD.
    The positions DataFrame stores a time-index of the
    quantity of positions held.
    The holdings DataFrame stores the cash and total market
    holdings value of each symbol for a particular
    time-index, as well as the percentage change in
    portfolio total across bars.
    """
    def __init__(self, bars, events, start_date, initial_capital=10000.0):
        """
        Initialises the portfolio with bars and an event queue.
        Also includes a starting datetime index and initial capital
        (USD unless otherwise stated).
        Parameters:
        bars - The DataHandler object with current market data.
        events - The Event Queue object.
        start_date - The start date (bar) of the portfolio.
        initial_capital - The starting capital in USD.
        """
        self.bars = bars
        self.events = events
        self.symbol_list = self.bars.symbol_list
        self.start_date = start_date
        self.initial_capital = initial_capital
        
        self.all_positions = self.construct_all_positions()
        self.current_positions = dict( (k,v) for k, v in [(s, 0) for s in self.symbol_list] )
        
        self.all_holdings = self.construct_all_holdings()
        self.current_holdings = self.construct_current_holdings()
        
    def construct_all_positions(self):
        """
        The following method, construct_all_positions, simply creates a dictionary for each
        symbol, sets the value to zero for each and then adds a datetime key, 
nally adding it to a list.
        It uses a dictionary comprehension, which is similar in spirit to a list comprehension:
        """
        d = dict( (k,v) for k, v in [(s,0) for s in self.symbol_list] )
        d['datetime'] = self.start_date
        return [d] #wraps the dictionary in a list
    
    def construct_all_holdings(self):
        """
        this method is similar to the above but adds extra keys for cash,
        commission and total, which respectively represent the spare cash in the account after any
        purchases, the cumulative commission accrued and the total account equity including cash and
        any open positions. Short positions are treated as negative. The starting cash and total account
        equity are both set to the initial capital.
        In this manner there are separate "accounts" for each symbol, the "cash on hand", the
        "commission" paid (Interactive Broker fees) and a "total" portfolio value. Clearly this does not
        take into account margin requirements or shorting constraints, but is su
cient to give you a
        
avour of how such an OMS is created:
        """
        d = dict( (k,v) for k, v in [(s,0.0) for s in self.symbol_list])
        d['datetime'] = self.start_date
        d['cash'] = self.initial_capital
        d['commission'] = 0.0
        d['total'] = self.initial_capital
        return [d]
            
    
    def construct_current_holdings(self):
        """
        constructs the dictionary which will hold the instateneous value of the
        portfolio across all symbols. similar to above but doesn't wrap the dictionary in a list
        b/c it is creating a single entry
        """
        d = dict( (k, v) for k,v in [(s, 0.0) for s in self.symbol_list] )
        d['cash'] = self.initial_capital
        d['commission'] = 0.0
        d['total'] = self.initial_capital        
        
        return d

    """
    
    On every heartbeat, that is every time new market data is requested from the DataHandler
    object, the portfolio must update the current market value of all the positions held. In a live
    trading scenario this information can be downloaded and parsed directly from the brokerage, but
    for a backtesting implementation it is necessary to calculate these values manually from the bars
    DataHandler.
    estimating price by using the closing price of the last bar received. works ok in intraday but
    for a daily strategy the variance between open and close may be too large too often.
    """
    def update_timeindex(self, event):
        """
        Adds a new record to the poisitons matrix for the current market data bar.
        this reflects the previous bar
        
        Makes use of a marketvent from the events queue.
        """
        latest_datetime = self.bars.get_latest_bar_datetime(
                self.symbol_list[0]
                )
        
        #update positions
        #==================
        
        dp = dict( (k,v) for k, v in [(s,0) for s in self.symbol_list] )
        dp['datetime'] = latest_datetime
        
        for s in self.symbol_list:
            dp[s] = self.current_positions[s]
            
        #append the current positions
        self.all_positions.append(dp)
        
        #update holdings
        #==================
        dh = dict( (k,v) for k, v in [(s,0) for s in self.symbol_list] )
        dh['datetime'] = latest_datetime
        dh['cash'] = self.current_holdings['cash']
        dh['commission'] = self.current_holdings['commission']
        dh['total'] = self.current_holdings['cash']
        
        for s in self.symbol_list:
            #approximation to the real value
            market_value = self.current_positions[s] * self.bars.get_latest_bar_value(s, "adj_close")
            dh[s] = market_value
            dh['total'] += market_value
            
        #append the current holdings
        self.all_holdings.append(dh)
        
        
    
    """
    The method update_positions_from_fill determines whether a FillEvent is a Buy or
    a Sell and then updates the current_positions dictionary accordingly by adding/subtracting
    the correct quantity of shares:
    """
    def update_positions_from_fill(self, fill):
        """
        Takes a fill object and updates the position matrix to reflect
        the new positions
        """
        fill_dir = 0
        if fill.direction == 'BUY':
            fill_dir = 1
        if fill.direction == 'SELL':
            fill_dir = -1
        
        #update positions list with new quantities
        self.current_positions[fill.symbol] += fill_dir*fill.quantity
        
    #now to update the holdings values
    #similar approach to above
    
    def update_holdings_from_fill(self, fill):
        """
        Takes a fill object and updates the holdings matrix
        to reflect the holdings value.
        """
        #check for buy or sell
        fill_dir = 0
        if fill.direction == 'BUY':
            fill_dir = 1
        if fill.direction == 'SELL':
            fill_dir = -1   
    
        #update holdings list with new quantities
        fill_cost = self.bars.get_latest_bar_value(fill.symbol, "adj_close")
        cost = fill_dir * fill_cost * fill.quantity
        self.current_holdings[fill.symbol] += cost
        self.current_holdings['commission'] += fill.commission
        self.current_holdings['cash'] -= (cost + fill.commission)
        self.current_holdings['total'] -= (cost + fill.commission)
        
    def update_fill(self, event):
        """
        Updates the portfolio current positions and holdings from a FillEvent
        """
        if event.type == 'FILL':
            self.update_positions_from_fill(event)
            self.update_holdings_from_fill(event)
            
    def generate_naive_order(self, signal):
        """
        Simply files an Order object as a constant quantity
        sizing of the signal object, without risk management or sizing
        considerations
        """
        order = None
        
        symbol = signal.symbol
        direction = signal.signal_type
        strength = signal.strength
        
        mkt_quantity = 100
        cur_quantity = self.current_positions[symbol]
        order_type = 'MKT'
        
        if direction == 'LONG' and cur_quantity == 0:
            order = OrderEvent(symbol, order_type, mkt_quantity, 'BUY')
            OrderEvent(symbol, order_type, mkt_quantity, 'BUY').print_order()
        if direction == 'SHORT' and cur_quantity == 0:
            order = OrderEvent(symbol, order_type, mkt_quantity, 'SELL')
            OrderEvent(symbol, order_type, mkt_quantity, 'SELL').print_order()
        if direction == 'EXIT' and cur_quantity > 0:
            order = OrderEvent(symbol, order_type, abs(cur_quantity), 'SELL')
            OrderEvent(symbol, order_type, mkt_quantity, 'SELL').print_order()
        if direction == 'EXIT' and cur_quantity < 0:
            order = OrderEvent(symbol, order_type, abs(cur_quantity), 'BUY')
            OrderEvent(symbol, order_type, mkt_quantity, 'BUY').print_order()
        
        return order
    
    
    def update_signal(self, event):
        """
        Acts on a signal event to generate new orders based on 
        portfolio logic from above code.
        """
        if event.type == 'SIGNAL':
            order_event = self.generate_naive_order(event)
            self.events.put(order_event)
    """
    The penultimate method in the Portfolio is the generation of an equity curve. This simply
    creates a returns stream, useful for performance calculations, and then normalises the equity
    curve to be percentage based. Thus the account initial size is equal to 1.0, as opposed to the
    absolute dollar amount:
    """        
    def create_equity_curve_dataframe(self):
        """
        Creates a pandas DF from the all_holdings list of dictionaries
        """
        curve = pd.DataFrame(self.all_holdings)
        curve.set_index('datetime', inplace=True)
        curve['returns'] = curve['total'].pct_change()
        curve['equity_curve'] = (1.0+curve['returns']).cumprod()
        self.equity_curve = curve
        
    #now we output the equity curve and other performance stats
    def output_summary_stats(self):
        """
        Creates a list of summary statistics for the portfolio
        """
        total_return = self.equity_curve['equity_curve'][-1]
        returns = self.equity_curve['returns']
        pnl = self.equity_curve['equity_curve']
        
        sharpe_ratio = create_sharpe_ratio(returns, periods=252*60*6.5)
        drawdown, max_dd, dd_duration = create_drawdowns(pnl)
        self.equity_curve['drawdown'] = drawdown
        
        stats = [("Total Return", "{:.4f}".format(((total_return-1.0) *100.0))),
                 ("Sharpe Ratio", "{:.4f}".format(sharpe_ratio)), 
                 ("Max Drawdown", "{:.4f}".format((max_dd * 100.0))),
                 ("Drawdown Duration", "{:.4f}".format(dd_duration)) ]
        self.equity_curve.to_csv(r'C:\Users\OBar\Documents\Quant Trading Research\QuantStart\Scripts\event_driven_trading\equity.csv')
        return stats
            
"""
The Portfolio object is the most complex aspect of the entire event-driven backtest system.
The implementation here, while intricate, is relatively elementary in its handling of positions.  
"""         
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    