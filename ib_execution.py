# -*- coding: utf-8 -*-
#!/usr/bin/python
#ib_execution.py
from __future__ import print_function
"""
Created on Thu May 23 20:59:02 2019

@author: OBar
"""
import datetime
import time

from ib.ext.Contract import Contract
from ib.ext.Order import Order
from ib.opt import ibConnection, message

from event import FillEvent, OrderEvent
from execution import ExecutionHandler

"""
We now defne the IBExecutionHandler class. The __init__ constructor 
firstly requires
knowledge of the events queue. It also requires speci
cation of order_routing, which I've
defaulted to "SMART". If you have speci
c exchange requirements, you can specify them here.
The default currency has also been set to US Dollars.
Within the method we create a fill_dict dictionary, needed later for usage in generating
FillEvent instances. We also create a tws_conn connection object to store our connection
information to the Interactive Brokers API. We also have to create an initial default order_id,
which keeps track of all subsequent orders to avoid duplicates. Finally we register the message
handlers (which we'll de
ne in more detail below):
"""

class IBExecutionHandler(ExecutionHandler):
    """
    Handles order execution via the IB api, for use against 
    accounts when trading live directly.
    """
    def __init__(
            self, events, order_routing="SMART", currency="USD"):
        """
        initialises the IBExecutionHandler instance.
        """
        self.events = events
        self.order_routing = order_routing
        self.currency = currency
        self.fill_dict = {}
        
        self.tws_conn = self.create_tws_connection()
        self.order_id = self.create_initial_order_id()
        self.register_handlers()
        
    def _error_handler(self, msg):
        """
        Handles the capturing of error messages
        """
        #currently no error handling
        print("Server Error:".format(msg))
        
    def _reply_handler(self, msg):
        """
        Handles of server replies
        """
        #handle open order orderID processing
        if msg.typeName == "openOrder" \
        and msg.orderID == self.order_id \
        and not self.fill_dict.has_key(msg.OrderID):
                self.create_fill_dict_entry(msg)
        #handle fills
        if msg.typeName == "OrderStatus" \
        and msg.status == "Filled" \
        and self.fill_dict[msg.orderID]["filled"] == False:
            self.create_fill(msg)
        print("Server Response: {}, {}".format(msg.typeName, msg))
            
    def create_tws_connection(self):
        """
        Connect to the Trader Workstation (TWS) running on the
        usual port of 7496, with a clientId of 10.
        The clientId is chosen by us and we will need
        separate IDs for both the execution connection and
        market data connection, if the latter is used elsewhere.
        """      
        tws_conn = ibConnection()
        tws_conn.connect()
        return tws_conn
    
    
    def create_initial_order_id(self):
        """
        Creates the initial order ID used for IB
        to keep track of submitted orders
        """
        #there is scopre for more logic but 1 will be default for now
        return 1
    
    def register_handlers(self): #registers the error and reply handler methods with the TWS connection
        """
        Register the error and server reply message handling functions
        """
        # Assign the error handling function defined above
        # to the TWS connection
        self.tws_conn.register(self._error_handler, 'Error')
        # Assign all of the server reply messages to the
        # reply_handler function defined above
        self.tws_conn.registerAll(self._reply_handler)
                
    """
    to transact a trade we need to create an IBPY Contract
    instance and pair it with our order instance. following method
    create_contract generated the first component of the paid.
    """
    def create_contract(self, symbol, sec_type, exch, prim_exch, curr):
        contract = Contract()
        contract.m_symbol = symbol
        contract.m_SecType = sec_type
        contract.m_exchange = exch
        contract.m_primaryExch = prim_exch
        contract.m_currency = curr
        return contract
    
    def create_order(self, order_type, quantity, action):
        """
        Create an order object (market/limit) to go long/short.
        """
        order = Order()
        order.m_orderType = order_type
        order.m_totalQuantity = quantity
        order.m_action = action
        return order
    
    def create_fill_dict_entry(self, msg):
        """
        Creates an entry in the Fill Dictionary that lists
        orderIds and provides security information. This is
        needed for the event-driven behaviour of the IB
        server message behaviour
        """
        self.fill_dict[msg.orderId] = {
            "symbol" : msg.contract.m_symbol,
            "exchange" : msg.contract.m_exchange,
            "direction" : msg.order.m_action,
            "filled" : False
            }
        
    def create_fill(self, msg):
        """
        Handles the creation of the FillEvent that will be placed
        onto the events queue subsequent to an order being filled
        """
        fd = self.fill_dict[msg.orderId]

        #prepare the fill data
        symbol = fd["symbol"]
        exchange = fd["exchange"]
        filled = msg.filled
        direction = fd["direction"]
        fill_cost = msg.avgFillPrice
        
        #Create a fill event object
        fill_event = FillEvent(
                datetime.datetime.utcnow, symbol,
                exchange, filled, direction, fill_cost
            )
        #make sure that multiple messages don't create addtl files
        self.fill_dict[msg.orderId]["filled"] = True
        
        #place the event onto the event queue
        self.events.put(fill_event)
        
    def execute_order(self, event):
        """
        Now that all of the preceeding methods having been implemented it remains to override the
        execute_order method from the ExecutionHandler abstract base class. This method actually
        carries out the order placement with the IB API.
        We first check that the event being received to this method is actually an OrderEvent and
        then prepare the Contract and Order objects with their respective parameters. Once both
        are created the IbPy method placeOrder of the connection object is called with an associated
        order_id.
        It is extremely important to call the time.sleep(1) method to ensure the order actually
        goes through to IB. Removal of this line leads to inconsistent behaviour of the API, at least on
        my system!
        Finally, we increment the order ID to ensure we don't duplicate orders:
        """
        if event.type == 'ORDER':
            #prepare the parameters for the asset order
            asset = event.symbol
            asset_type = "STK"
            order_type = event.order_type
            quantity = event.quantity
            direction = event.direction

            #create te IB contract via the passed order event
            ib_contract = self.create_contract(
                    asset, asset_type, self.order_routing,
                    self.order_routing, self.currency)          
            
            #create the IB order via the passed order event
            ib_order = self.create_order(
                    order_type, quantity, direction
            )
            
            #use the connection to the send order to IB
            self.tws_conn.placeOrder(
                    self.order_id, ib_contract, ib_order)
            
            #note this following line is crucial.
            #it ensures the order goes through
            time.sleep(1)
            
            #increment the order id for this session
            self.order_id += 1
            

        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        