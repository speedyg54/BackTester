# -*- coding: utf-8 -*-
#!/usr/bin/python
from __future__ import print_function
"""
Created on Mon May 20 20:37:41 2019

@author: OBar
"""

class Event(object): #parent class
    """
    Event is base class providing an interface for all subsequent
    (inherited) events, that will trigger further events in the trading
    infrasture
    """
    pass


class MarketEvent(Event):
    """
    Handles the event of receiving a new market update with corresponding
    bars.
    """
    def __init__(self):
        """
        initialises the marketevent.
        """
        self.type = 'MARKET'

class SignalEvent(Event):
    """
    Handles the event of sending a signal from a strategy object.
    this is received by a portfolio object and acted upon.
    """
    def __init__(self, strategy_id, symbol, datetime, signal_type, strength):
        """
        Initialises the signalevent
        
        Parameters:
        stategy_id - the unique identifier for the strategy that
            generated the signal.
        symbol - ticker symbol
        datetime - timestamp which signal was generated
        signal_type - 'LONG' or 'SHORT'
        strength - an adjustment factor "suggestion" used to scale
            quantity at the portfolio level. useful for pairs strategies
        """
        self.type = 'SIGNAL'
        self.strategy_id = strategy_id
        self.symbol = symbol
        self.datetime = datetime
        self.signal_type = signal_type
        self.strength = strength
    
class OrderEvent(Event):
    """
    Handles the event of sending an order to an execution system.
    the order contains a symbol, a type, quantity and direction.
    """
    def __init__(self, symbol, order_type, quantity, direction):
        """
        Initialise the order type, setting whether it is a market
        order or limit order, has a quantity, and its direction
        
        Parameters:
            symbol - the instrument
            order type
            quantity
            direction
        """
        self.type = 'ORDER'
        self.symbol = symbol
        self.order_type = order_type
        self.quantity = quantity
        self.direction = direction
    
    def print_order(self):
        """
        Outputs the values within the order
        """
        print(
        "Order: Symbol = {}, Type= {}, Quantity = {}, Direction = {}"
        .format(self.symbol, self.order_type, self.quantity, self.direction)
        )
        
        
class FillEvent(Event):
    """
    Encapsulates the notion of a fill order, as returned from a brokerage
    stores the quantity of an instrument actually filled and at what price.
    in addition, stores the commission of the trade from the brokerage.
    """
    def __init__(self, timeindex, symbol, exchange, quantity, direction,
                 fill_cost, commission=None):
        """
        Initialises the fillevent object. sets the symbol, 
        exchange, quantity, direction, cost of fill and an optional comm.
        If commission is not provided, the Fill object will
        calculate it based on the trade size and Interactive
        Brokers fees.
        Parameters:
        timeindex - The bar-resolution when the order was filled.
        symbol - The instrument which was filled.
        exchange - The exchange where the order was filled.
        quantity - The filled quantity.
        direction - The direction of fill (’BUY’ or ’SELL’)
        fill_cost - The holdings value in dollars.
        commission - An optional commission sent from IB.
        """
        self.type = 'FILL'
        self.timeindex = timeindex
        self.symbol = symbol
        self.exchange = exchange
        self.quantity = quantity
        self.direction = direction
        self.fill_cost = fill_cost
        
        #calculate commission
        if commission is None:
            self.commission = self.calculate_ib_commission()
        else:
            self.commission = commission
    
    def calculate_ib_commission(self):
        """
        Calculates the fees of trading based on an interactive brokers fee structure
        for API, in USD
        This does not include exchange or ECN fees.
        
        Based on "US API Directed Order":
        https://www.interactivebrokers.com/en/index.php?
        f=commission&p=stocks2
        """    
        full_cost = 1.3
        if self.quantity <= 500:
            full_cost = max(1.3, 0.013 * self.quantity)
        else: #Greater than 500
            full_cost = max(1.3, 0.013 * self.quantity)
        return full_cost
        

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    