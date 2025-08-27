from collections import defaultdict, deque
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
import heapq
from dataclasses import dataclass
from datetime import datetime
import uuid

from shared.models.base import Order, OrderSide, OrderStatus, Execution

@dataclass
class PriceLevel:
    price: Decimal
    total_quantity: Decimal
    orders: deque

class OrderBook:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.bids: Dict[Decimal, PriceLevel] = {}  # price -> PriceLevel
        self.asks: Dict[Decimal, PriceLevel] = {}  # price -> PriceLevel
        self.orders: Dict[str, Order] = {}  # order_id -> Order
        
        # For efficient best bid/ask lookup
        self.bid_prices = []  # max heap (negative prices)
        self.ask_prices = []  # min heap
        
    def add_order(self, order: Order) -> List[Execution]:
        """Add order to order book and return list of executions"""
        self.orders[order.id] = order
        executions = []
        
        if order.side == OrderSide.BUY:
            executions = self._match_buy_order(order)
        else:
            executions = self._match_sell_order(order)
            
        # Add remaining quantity to order book if not fully filled
        if order.remaining_quantity > 0:
            self._add_to_book(order)
            
        return executions
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order and remove from book"""
        if order_id not in self.orders:
            return False
            
        order = self.orders[order_id]
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
            return False
            
        self._remove_from_book(order)
        order.status = OrderStatus.CANCELLED
        
        return True
    
    def _match_buy_order(self, buy_order: Order) -> List[Execution]:
        """Match buy order against sell orders"""
        executions = []
        
        while (buy_order.remaining_quantity > 0 and 
               self.ask_prices and 
               self.ask_prices[0] <= buy_order.price):
            
            best_ask_price = heapq.heappop(self.ask_prices)
            
            if best_ask_price not in self.asks:
                continue
                
            price_level = self.asks[best_ask_price]
            
            while (buy_order.remaining_quantity > 0 and 
                   price_level.orders):
                
                sell_order = price_level.orders.popleft()
                execution = self._execute_orders(buy_order, sell_order, best_ask_price)
                executions.append(execution)
                
                if sell_order.remaining_quantity == 0:
                    sell_order.status = OrderStatus.FILLED
                else:
                    # Put back partially filled order
                    price_level.orders.appendleft(sell_order)
                    break
            
            # Update price level
            if not price_level.orders:
                del self.asks[best_ask_price]
            else:
                # Put price back in heap if orders remain
                heapq.heappush(self.ask_prices, best_ask_price)
                price_level.total_quantity = sum(order.remaining_quantity for order in price_level.orders)
                
        return executions
    
    def _match_sell_order(self, sell_order: Order) -> List[Execution]:
        """Match sell order against buy orders"""
        executions = []
        
        while (sell_order.remaining_quantity > 0 and 
               self.bid_prices and 
               -self.bid_prices[0] >= sell_order.price):
            
            best_bid_price = -heapq.heappop(self.bid_prices)
            
            if best_bid_price not in self.bids:
                continue
                
            price_level = self.bids[best_bid_price]
            
            while (sell_order.remaining_quantity > 0 and 
                   price_level.orders):
                
                buy_order = price_level.orders.popleft()
                execution = self._execute_orders(buy_order, sell_order, best_bid_price)
                executions.append(execution)
                
                if buy_order.remaining_quantity == 0:
                    buy_order.status = OrderStatus.FILLED
                else:
                    # Put back partially filled order
                    price_level.orders.appendleft(buy_order)
                    break
            
            # Update price level
            if not price_level.orders:
                del self.bids[best_bid_price]
            else:
                # Put price back in heap if orders remain
                heapq.heappush(self.bid_prices, -best_bid_price)
                price_level.total_quantity = sum(order.remaining_quantity for order in price_level.orders)
                
        return executions
    
    def _execute_orders(self, buy_order: Order, sell_order: Order, execution_price: Decimal) -> Execution:
        """Execute matched orders and return execution"""
        quantity = min(buy_order.remaining_quantity, sell_order.remaining_quantity)
        
        # Update order quantities
        buy_order.filled_quantity += quantity
        buy_order.remaining_quantity -= quantity
        sell_order.filled_quantity += quantity
        sell_order.remaining_quantity -= quantity
        
        # Update order status
        if buy_order.remaining_quantity == 0:
            buy_order.status = OrderStatus.FILLED
        else:
            buy_order.status = OrderStatus.PARTIAL
            
        if sell_order.remaining_quantity == 0:
            sell_order.status = OrderStatus.FILLED
        else:
            sell_order.status = OrderStatus.PARTIAL
        
        # Create execution
        execution = Execution(
            id=str(uuid.uuid4()),
            order_id=f"{buy_order.id},{sell_order.id}",
            symbol=self.symbol,
            side=OrderSide.BUY,  # Convention: execution side is from buyer's perspective
            quantity=quantity,
            price=execution_price,
            buyer_id=buy_order.user_id,
            seller_id=sell_order.user_id,
            executed_at=datetime.now()
        )
        
        return execution
    
    def _add_to_book(self, order: Order):
        """Add order to the appropriate side of the book"""
        if order.side == OrderSide.BUY:
            if order.price not in self.bids:
                self.bids[order.price] = PriceLevel(
                    price=order.price,
                    total_quantity=Decimal("0"),
                    orders=deque()
                )
                heapq.heappush(self.bid_prices, -order.price)
            
            self.bids[order.price].orders.append(order)
            self.bids[order.price].total_quantity += order.remaining_quantity
            
        else:  # SELL
            if order.price not in self.asks:
                self.asks[order.price] = PriceLevel(
                    price=order.price,
                    total_quantity=Decimal("0"),
                    orders=deque()
                )
                heapq.heappush(self.ask_prices, order.price)
            
            self.asks[order.price].orders.append(order)
            self.asks[order.price].total_quantity += order.remaining_quantity
    
    def _remove_from_book(self, order: Order):
        """Remove order from the book"""
        if order.side == OrderSide.BUY and order.price in self.bids:
            price_level = self.bids[order.price]
            try:
                price_level.orders.remove(order)
                price_level.total_quantity -= order.remaining_quantity
                if not price_level.orders:
                    del self.bids[order.price]
            except ValueError:
                pass  # Order not in queue
                
        elif order.side == OrderSide.SELL and order.price in self.asks:
            price_level = self.asks[order.price]
            try:
                price_level.orders.remove(order)
                price_level.total_quantity -= order.remaining_quantity
                if not price_level.orders:
                    del self.asks[order.price]
            except ValueError:
                pass  # Order not in queue
    
    def get_best_bid(self) -> Optional[Tuple[Decimal, Decimal]]:
        """Get best bid price and quantity"""
        if not self.bid_prices:
            return None
        best_price = -self.bid_prices[0]
        return (best_price, self.bids[best_price].total_quantity)
    
    def get_best_ask(self) -> Optional[Tuple[Decimal, Decimal]]:
        """Get best ask price and quantity"""
        if not self.ask_prices:
            return None
        best_price = self.ask_prices[0]
        return (best_price, self.asks[best_price].total_quantity)
    
    def get_order_book_snapshot(self, depth: int = 5) -> Dict:
        """Get order book snapshot with specified depth"""
        bids = []
        asks = []
        
        # Get top bids
        sorted_bids = sorted(self.bids.keys(), reverse=True)
        for price in sorted_bids[:depth]:
            bids.append((price, self.bids[price].total_quantity))
        
        # Get top asks
        sorted_asks = sorted(self.asks.keys())
        for price in sorted_asks[:depth]:
            asks.append((price, self.asks[price].total_quantity))
        
        return {
            "symbol": self.symbol,
            "bids": bids,
            "asks": asks,
            "timestamp": datetime.now()
        }