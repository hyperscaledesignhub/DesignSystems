#!/usr/bin/env python3
"""
Matching Engine Algorithms Demonstration
Shows order matching logic, price-time priority, and execution algorithms
"""

import asyncio
import httpx
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict

class MatchingEngineDemo:
    def __init__(self):
        self.matching_engine_url = 'http://localhost:8792'
        self.client_gateway_url = 'http://localhost:8347'
        self.market_data_url = 'http://localhost:8864'
        
    async def authenticate_demo_user(self):
        """Authenticate demo user to get token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.client_gateway_url}/auth/login",
                json={"username": "buyer_demo", "password": "demopass123"}
            )
            return response.json()["access_token"]
            
    async def demonstrate_price_time_priority(self):
        """Demo 1: Price-Time Priority Algorithm"""
        print("⚡ Demo 1: Price-Time Priority Algorithm")
        print("-" * 50)
        
        token = await self.authenticate_demo_user()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create orders with different prices and times
        orders = [
            {"symbol": "AAPL", "side": "BUY", "quantity": "100", "price": "149.00"},   # Lower price, earlier time
            {"symbol": "AAPL", "side": "BUY", "quantity": "50", "price": "150.00"},    # Higher price, later time  
            {"symbol": "AAPL", "side": "BUY", "quantity": "75", "price": "149.50"},    # Mid price, middle time
            {"symbol": "AAPL", "side": "SELL", "quantity": "200", "price": "149.25"}   # Should match with highest bid first
        ]
        
        print("📝 Placing orders to demonstrate price-time priority:")
        order_ids = []
        
        async with httpx.AsyncClient() as client:
            for i, order in enumerate(orders):
                response = await client.post(
                    f"{self.client_gateway_url}/v1/order",
                    json=order,
                    headers=headers
                )
                
                order_data = response.json()
                order_ids.append(order_data['id'])
                
                side_icon = "🟢" if order['side'] == "BUY" else "🔴"
                print(f"   {side_icon} Order {i+1}: {order['side']} {order['quantity']} @ ${order['price']}")
                
                # Small delay to ensure time priority
                await asyncio.sleep(0.2)
                
        print(f"\n🎯 Expected matching order:")
        print(f"   SELL order should match with BUY @ $150.00 first (highest price)")
        print(f"   Then BUY @ $149.50, then BUY @ $149.25")
        
        # Check order book after matching
        await asyncio.sleep(1)
        
        async with httpx.AsyncClient() as client:
            orderbook_response = await client.get(f"{self.market_data_url}/orderBook/L2?symbol=AAPL&depth=5")
            orderbook = orderbook_response.json()
            
            print(f"\n📊 Order Book after matching:")
            print(f"   Best Bid: ${orderbook['bids'][0]['price'] if orderbook['bids'] else 'None'}")
            print(f"   Best Ask: ${orderbook['asks'][0]['price'] if orderbook['asks'] else 'None'}")
            
    async def demonstrate_order_types(self):
        """Demo 2: Different order types (Market vs Limit)"""
        print(f"\n📋 Demo 2: Order Types - Market vs Limit")
        print("-" * 50)
        
        token = await self.authenticate_demo_user()
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient() as client:
            # Place limit orders to create order book depth
            limit_orders = [
                {"symbol": "MSFT", "side": "BUY", "quantity": "100", "price": "299.00"},
                {"symbol": "MSFT", "side": "BUY", "quantity": "150", "price": "298.50"},
                {"symbol": "MSFT", "side": "SELL", "quantity": "100", "price": "300.50"},
                {"symbol": "MSFT", "side": "SELL", "quantity": "200", "price": "301.00"}
            ]
            
            print("📝 Placing limit orders to create order book:")
            for order in limit_orders:
                response = await client.post(
                    f"{self.client_gateway_url}/v1/order",
                    json=order,
                    headers=headers
                )
                side_icon = "🟢" if order['side'] == "BUY" else "🔴"
                print(f"   {side_icon} LIMIT: {order['side']} {order['quantity']} @ ${order['price']}")
                await asyncio.sleep(0.1)
                
            # Now place a market order 
            print(f"\n🚀 Placing MARKET order:")
            market_order = {"symbol": "MSFT", "side": "BUY", "quantity": "75", "price": "305.00"}  # High price acts as market order
            
            start_time = time.time()
            response = await client.post(
                f"{self.client_gateway_url}/v1/order",
                json=market_order,
                headers=headers
            )
            end_time = time.time()
            
            execution_time = (end_time - start_time) * 1000
            market_result = response.json()
            
            print(f"   🚀 MARKET: BUY 75 shares (executed in {execution_time:.2f}ms)")
            print(f"   ✅ Status: {market_result.get('status', 'Unknown')}")
            print(f"   💰 Filled: {market_result.get('filled_quantity', 0)} @ avg price")
            
    async def demonstrate_partial_fills(self):
        """Demo 3: Partial order fills"""
        print(f"\n🔄 Demo 3: Partial Order Fills")
        print("-" * 50)
        
        token = await self.authenticate_demo_user()
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient() as client:
            # Place a large sell order
            large_sell_order = {"symbol": "GOOGL", "side": "SELL", "quantity": "500", "price": "2800.00"}
            
            print("📝 Placing large SELL order:")
            print(f"   🔴 SELL 500 @ $2800.00")
            
            response = await client.post(
                f"{self.client_gateway_url}/v1/order",
                json=large_sell_order,
                headers=headers
            )
            large_order_result = response.json()
            large_order_id = large_order_result['id']
            
            # Place smaller buy orders that will partially fill the sell order
            small_buy_orders = [
                {"symbol": "GOOGL", "side": "BUY", "quantity": "50", "price": "2800.00"},
                {"symbol": "GOOGL", "side": "BUY", "quantity": "75", "price": "2800.00"},
                {"symbol": "GOOGL", "side": "BUY", "quantity": "100", "price": "2800.00"}
            ]
            
            print(f"\n🟢 Placing smaller BUY orders to create partial fills:")
            total_filled = 0
            
            for i, order in enumerate(small_buy_orders):
                response = await client.post(
                    f"{self.client_gateway_url}/v1/order",
                    json=order,
                    headers=headers
                )
                
                buy_result = response.json()
                filled_qty = int(buy_result.get('filled_quantity', 0))
                total_filled += filled_qty
                
                print(f"   🟢 BUY {order['quantity']} @ ${order['price']} - Filled: {filled_qty}")
                await asyncio.sleep(0.3)
                
            print(f"\n📊 Partial Fill Summary:")
            print(f"   Original SELL order: 500 shares")
            print(f"   Total filled so far: {total_filled} shares")
            print(f"   Remaining unfilled: {500 - total_filled} shares")
            
    async def demonstrate_order_book_depth(self):
        """Demo 4: Order book depth and liquidity"""
        print(f"\n📚 Demo 4: Order Book Depth & Liquidity")
        print("-" * 50)
        
        token = await self.authenticate_demo_user()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create orders at different price levels
        depth_orders = [
            # Buy side (bids) - descending prices
            {"symbol": "TSLA", "side": "BUY", "quantity": "100", "price": "800.00"},
            {"symbol": "TSLA", "side": "BUY", "quantity": "150", "price": "799.50"},
            {"symbol": "TSLA", "side": "BUY", "quantity": "200", "price": "799.00"},
            {"symbol": "TSLA", "side": "BUY", "quantity": "250", "price": "798.50"},
            
            # Sell side (asks) - ascending prices
            {"symbol": "TSLA", "side": "SELL", "quantity": "120", "price": "801.00"},
            {"symbol": "TSLA", "side": "SELL", "quantity": "180", "price": "801.50"},
            {"symbol": "TSLA", "side": "SELL", "quantity": "220", "price": "802.00"},
            {"symbol": "TSLA", "side": "SELL", "quantity": "300", "price": "802.50"}
        ]
        
        print("📝 Creating order book depth:")
        
        async with httpx.AsyncClient() as client:
            for order in depth_orders:
                response = await client.post(
                    f"{self.client_gateway_url}/v1/order",
                    json=order,
                    headers=headers
                )
                await asyncio.sleep(0.1)
                
            # Get order book depth
            await asyncio.sleep(0.5)
            orderbook_response = await client.get(f"{self.market_data_url}/orderBook/L2?symbol=TSLA&depth=10")
            orderbook = orderbook_response.json()
            
            print(f"\n📊 TSLA Order Book Depth:")
            print(f"{'':>8} {'BIDS':>15} {'':>5} {'ASKS':>15}")
            print(f"{'Price':>8} {'Quantity':>10} {'Total':>5} {'Quantity':>10} {'Price':>5}")
            print("-" * 50)
            
            # Display bids and asks side by side
            max_levels = max(len(orderbook.get('bids', [])), len(orderbook.get('asks', [])))
            
            for i in range(max_levels):
                bid_price = bid_qty = ask_price = ask_qty = ""
                
                if i < len(orderbook.get('bids', [])):
                    bid = orderbook['bids'][i]
                    bid_price = f"${bid['price']}"
                    bid_qty = bid['quantity']
                    
                if i < len(orderbook.get('asks', [])):
                    ask = orderbook['asks'][i] 
                    ask_price = f"${ask['price']}"
                    ask_qty = ask['quantity']
                    
                print(f"{bid_price:>8} {bid_qty:>10} {'':>5} {ask_qty:>10} {ask_price:>5}")
                
            # Calculate spread
            if orderbook.get('bids') and orderbook.get('asks'):
                best_bid = float(orderbook['bids'][0]['price'])
                best_ask = float(orderbook['asks'][0]['price'])
                spread = best_ask - best_bid
                spread_pct = (spread / best_bid) * 100
                
                print(f"\n💰 Market Statistics:")
                print(f"   Best Bid: ${best_bid:.2f}")
                print(f"   Best Ask: ${best_ask:.2f}")
                print(f"   Spread: ${spread:.2f} ({spread_pct:.3f}%)")
                
    async def demonstrate_matching_performance(self):
        """Demo 5: Matching engine performance testing"""
        print(f"\n🚀 Demo 5: Matching Engine Performance")
        print("-" * 50)
        
        token = await self.authenticate_demo_user()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Performance test with rapid order placement
        test_orders = []
        for i in range(20):
            side = "BUY" if i % 2 == 0 else "SELL"
            base_price = 100.00
            price_variation = (i % 10) * 0.10
            price = base_price + price_variation if side == "BUY" else base_price + 0.50 + price_variation
            
            test_orders.append({
                "symbol": "PERF",
                "side": side,
                "quantity": str(10 + (i % 50)),
                "price": f"{price:.2f}"
            })
            
        print(f"⚡ Performance test: Placing {len(test_orders)} orders rapidly...")
        
        start_time = time.time()
        successful_orders = 0
        
        async with httpx.AsyncClient() as client:
            tasks = []
            for order in test_orders:
                task = client.post(
                    f"{self.client_gateway_url}/v1/order",
                    json=order,
                    headers=headers
                )
                tasks.append(task)
                
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for response in responses:
                if not isinstance(response, Exception) and response.status_code == 201:
                    successful_orders += 1
                    
        end_time = time.time()
        
        total_time = end_time - start_time
        orders_per_second = len(test_orders) / total_time
        
        print(f"📊 Performance Results:")
        print(f"   Orders placed: {len(test_orders)}")
        print(f"   Successful orders: {successful_orders}")
        print(f"   Total time: {total_time:.3f}s")
        print(f"   Orders/second: {orders_per_second:.1f}")
        print(f"   Avg latency: {(total_time/len(test_orders)*1000):.2f}ms per order")
        
    async def get_matching_engine_stats(self):
        """Get matching engine statistics"""
        print(f"\n📊 Matching Engine Statistics")
        print("-" * 50)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.matching_engine_url}/health")
                health_data = response.json()
                
                print(f"🟢 Engine Status: {health_data.get('status', 'Unknown')}")
                print(f"⏱️  Uptime: {health_data.get('uptime', 'Unknown')}")
                
                # Get order book summary for all symbols  
                symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'PERF']
                total_orders = 0
                
                for symbol in symbols:
                    try:
                        ob_response = await client.get(f"{self.market_data_url}/orderBook/L2?symbol={symbol}&depth=1")
                        orderbook = ob_response.json()
                        
                        bid_count = len(orderbook.get('bids', []))
                        ask_count = len(orderbook.get('asks', []))
                        symbol_orders = bid_count + ask_count
                        total_orders += symbol_orders
                        
                        if symbol_orders > 0:
                            print(f"📈 {symbol}: {symbol_orders} orders in book ({bid_count} bids, {ask_count} asks)")
                            
                    except:
                        continue
                        
                print(f"📊 Total active orders across all symbols: {total_orders}")
                
            except Exception as e:
                print(f"❌ Unable to get engine stats: {e}")
                
    async def run_complete_demo(self):
        """Run complete matching engine demonstration"""
        print("⚡ MATCHING ENGINE ALGORITHMS DEMONSTRATION")
        print("=" * 60)
        print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        try:
            # Test matching engine connection
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.matching_engine_url}/health")
                if response.status_code == 200:
                    print("✅ Matching Engine connection successful")
                else:
                    raise Exception("Matching Engine not responding")
                    
            print()
            
            await self.demonstrate_price_time_priority()
            await self.demonstrate_order_types()
            await self.demonstrate_partial_fills()
            await self.demonstrate_order_book_depth()
            await self.demonstrate_matching_performance()
            await self.get_matching_engine_stats()
            
            print(f"\n🎉 MATCHING ENGINE DEMONSTRATION COMPLETE!")
            print("=" * 60)
            print("✅ Price-time priority algorithm demonstrated")
            print("✅ Order types (market vs limit) demonstrated")
            print("✅ Partial fills demonstrated")
            print("✅ Order book depth and liquidity demonstrated") 
            print("✅ Performance testing completed")
            print("✅ Engine statistics displayed")
            
        except Exception as e:
            print(f"❌ Demo failed: {e}")
            print("Make sure all services are running with: ./start_complete_system_fixed.sh")
            
if __name__ == "__main__":
    demo = MatchingEngineDemo()
    asyncio.run(demo.run_complete_demo())