#!/usr/bin/env python3
"""
Redis Pub/Sub Messaging Demonstration
Shows real-time messaging between microservices via Redis
"""

import asyncio
import redis
import json
import time
from datetime import datetime

class RedisPubSubDemo:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.pubsub = self.redis_client.pubsub()
        
    async def demonstrate_order_flow_messaging(self):
        """Demo 1: Order flow messaging between services"""
        print("📡 Demo 1: Order Flow Messaging")
        print("-" * 50)
        
        # Subscribe to order-related channels
        channels = [
            'orders.new',
            'orders.risk_checked', 
            'orders.matched',
            'orders.executed',
            'wallets.updated',
            'notifications.trade'
        ]
        
        self.pubsub.subscribe(*channels)
        print(f"✅ Subscribed to channels: {', '.join(channels)}")
        
        # Simulate order creation message
        order_data = {
            "order_id": "ORDER_001",
            "user_id": 1,
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 100,
            "price": 150.00,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"\n🔄 Publishing order creation...")
        self.redis_client.publish('orders.new', json.dumps(order_data))
        
        # Simulate risk check response
        await asyncio.sleep(0.5)
        risk_response = {
            "order_id": "ORDER_001",
            "risk_status": "APPROVED",
            "risk_score": 0.15,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"🛡️  Publishing risk check result...")
        self.redis_client.publish('orders.risk_checked', json.dumps(risk_response))
        
        # Simulate matching engine response
        await asyncio.sleep(0.5)
        match_data = {
            "order_id": "ORDER_001", 
            "matched_order_id": "ORDER_002",
            "execution_price": 149.95,
            "execution_quantity": 100,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"🎯 Publishing match result...")
        self.redis_client.publish('orders.matched', json.dumps(match_data))
        
        # Read messages
        print(f"\n📨 Reading messages from channels...")
        message_count = 0
        start_time = time.time()
        
        while message_count < 3 and (time.time() - start_time) < 5:
            message = self.pubsub.get_message()
            if message and message['type'] == 'message':
                channel = message['channel']
                data = json.loads(message['data'])
                print(f"   📩 {channel}: Order {data.get('order_id', 'N/A')} - {data.get('risk_status', data.get('execution_price', 'processed'))}")
                message_count += 1
            await asyncio.sleep(0.1)
                
    async def demonstrate_market_data_streaming(self):
        """Demo 2: Market data streaming"""
        print(f"\n📊 Demo 2: Market Data Streaming")
        print("-" * 50)
        
        # Subscribe to market data channels
        market_channels = [
            'market_data.price_updates',
            'market_data.order_book_updates',
            'market_data.trade_ticks'
        ]
        
        # Clear previous subscriptions
        self.pubsub.unsubscribe()
        self.pubsub.subscribe(*market_channels)
        
        print(f"✅ Subscribed to market data channels")
        
        # Simulate market data updates
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        
        for symbol in symbols:
            price_update = {
                "symbol": symbol,
                "price": 150.00 + (hash(symbol) % 50),
                "volume": 1000 + (hash(symbol) % 5000),
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"📈 Publishing price update for {symbol}...")
            self.redis_client.publish('market_data.price_updates', json.dumps(price_update))
            await asyncio.sleep(0.3)
            
        # Read market data messages  
        print(f"\n📨 Reading market data updates...")
        message_count = 0
        start_time = time.time()
        
        while message_count < 3 and (time.time() - start_time) < 5:
            message = self.pubsub.get_message()
            if message and message['type'] == 'message':
                data = json.loads(message['data'])
                symbol = data.get('symbol', 'N/A')
                price = data.get('price', 'N/A')
                volume = data.get('volume', 'N/A')
                print(f"   📊 {symbol}: ${price} (Vol: {volume:,})")
                message_count += 1
            await asyncio.sleep(0.1)
                
    async def demonstrate_notification_system(self):
        """Demo 3: Notification system messaging"""
        print(f"\n🔔 Demo 3: Notification System")
        print("-" * 50)
        
        # Subscribe to notification channels
        notification_channels = [
            'notifications.trade_executed',
            'notifications.balance_updated',
            'notifications.risk_alert',
            'notifications.system_alert'
        ]
        
        self.pubsub.unsubscribe()
        self.pubsub.subscribe(*notification_channels)
        
        print(f"✅ Subscribed to notification channels")
        
        # Simulate various notifications
        notifications = [
            {
                "channel": "notifications.trade_executed",
                "data": {
                    "user_id": 1,
                    "trade_id": "TRADE_001", 
                    "symbol": "AAPL",
                    "quantity": 100,
                    "price": 149.95,
                    "message": "Trade executed successfully"
                }
            },
            {
                "channel": "notifications.balance_updated",
                "data": {
                    "user_id": 1,
                    "previous_balance": 50000.00,
                    "new_balance": 35005.00,
                    "change": -14995.00,
                    "message": "Balance updated after trade"
                }
            },
            {
                "channel": "notifications.risk_alert",
                "data": {
                    "user_id": 2,
                    "alert_type": "DAILY_LOSS_LIMIT",
                    "threshold": 10000.00,
                    "current_loss": 9500.00,
                    "message": "Approaching daily loss limit"
                }
            }
        ]
        
        for notification in notifications:
            print(f"🔔 Publishing {notification['channel'].split('.')[-1]} notification...")
            self.redis_client.publish(notification['channel'], json.dumps(notification['data']))
            await asyncio.sleep(0.5)
            
        # Read notification messages
        print(f"\n📨 Reading notifications...")
        message_count = 0
        start_time = time.time()
        
        while message_count < 3 and (time.time() - start_time) < 5:
            message = self.pubsub.get_message()
            if message and message['type'] == 'message':
                data = json.loads(message['data'])
                notification_type = message['channel'].split('.')[-1]
                user_id = data.get('user_id', 'N/A')
                msg = data.get('message', 'Notification received')
                print(f"   🔔 {notification_type.upper()}: User {user_id} - {msg}")
                message_count += 1
            await asyncio.sleep(0.1)
                
    async def demonstrate_real_time_analytics(self):
        """Demo 4: Real-time analytics messaging"""
        print(f"\n📈 Demo 4: Real-time Analytics")
        print("-" * 50)
        
        # Subscribe to analytics channels
        analytics_channels = [
            'analytics.trade_volume',
            'analytics.price_movement', 
            'analytics.user_activity',
            'analytics.system_metrics'
        ]
        
        self.pubsub.unsubscribe()
        self.pubsub.subscribe(*analytics_channels)
        
        print(f"✅ Subscribed to analytics channels")
        
        # Simulate analytics data
        analytics_data = [
            {
                "channel": "analytics.trade_volume",
                "data": {
                    "symbol": "AAPL",
                    "volume_1m": 15000,
                    "volume_5m": 75000,
                    "volume_1h": 450000,
                    "timestamp": datetime.now().isoformat()
                }
            },
            {
                "channel": "analytics.price_movement",
                "data": {
                    "symbol": "AAPL", 
                    "price_change_1m": 0.15,
                    "price_change_5m": -0.25,
                    "price_change_1h": 1.50,
                    "volatility": 0.023
                }
            },
            {
                "channel": "analytics.user_activity",
                "data": {
                    "active_users_1m": 125,
                    "new_orders_1m": 45,
                    "executed_trades_1m": 23,
                    "avg_order_size": 1250.75
                }
            }
        ]
        
        for analytics in analytics_data:
            print(f"📊 Publishing {analytics['channel'].split('.')[-1]} analytics...")
            self.redis_client.publish(analytics['channel'], json.dumps(analytics['data']))
            await asyncio.sleep(0.5)
            
        # Read analytics messages
        print(f"\n📨 Reading analytics data...")
        message_count = 0
        start_time = time.time()
        
        while message_count < 3 and (time.time() - start_time) < 5:
            message = self.pubsub.get_message()
            if message and message['type'] == 'message':
                data = json.loads(message['data'])
                analytics_type = message['channel'].split('.')[-1]
                
                if analytics_type == 'trade_volume':
                    symbol = data.get('symbol', 'N/A')
                    volume = data.get('volume_1m', 'N/A')
                    print(f"   📊 VOLUME: {symbol} - {volume:,} shares in last minute")
                elif analytics_type == 'price_movement':
                    symbol = data.get('symbol', 'N/A')
                    change = data.get('price_change_1m', 'N/A')
                    print(f"   📈 PRICE: {symbol} - {change:+.2f} (1m change)")
                elif analytics_type == 'user_activity':
                    active_users = data.get('active_users_1m', 'N/A')
                    new_orders = data.get('new_orders_1m', 'N/A')
                    print(f"   👥 ACTIVITY: {active_users} active users, {new_orders} new orders")
                    
                message_count += 1
            await asyncio.sleep(0.1)
                
    async def show_redis_statistics(self):
        """Show Redis connection and message statistics"""
        print(f"\n📊 Redis Statistics")
        print("-" * 50)
        
        info = self.redis_client.info()
        
        print(f"🔗 Connected Clients: {info['connected_clients']}")
        print(f"📨 Commands Processed: {info['total_commands_processed']:,}")
        print(f"💾 Used Memory: {info['used_memory_human']}")
        print(f"⏱️  Uptime: {info['uptime_in_seconds']} seconds")
        print(f"🔄 Pub/Sub Channels: {info['pubsub_channels']}")
        print(f"📡 Pub/Sub Patterns: {info['pubsub_patterns']}")
        
    async def run_complete_demo(self):
        """Run complete Redis pub/sub demonstration"""
        print("📡 REDIS PUB/SUB MESSAGING DEMONSTRATION")
        print("=" * 60)
        print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        try:
            # Test Redis connection
            self.redis_client.ping()
            print("✅ Redis connection successful")
            print()
            
            await self.demonstrate_order_flow_messaging()
            await self.demonstrate_market_data_streaming()
            await self.demonstrate_notification_system()
            await self.demonstrate_real_time_analytics()
            await self.show_redis_statistics()
            
            print(f"\n🎉 REDIS DEMONSTRATION COMPLETE!")
            print("=" * 60)
            print("✅ Order flow messaging demonstrated")
            print("✅ Market data streaming demonstrated") 
            print("✅ Notification system demonstrated")
            print("✅ Real-time analytics demonstrated")
            print("✅ Redis statistics displayed")
            
        except redis.ConnectionError:
            print("❌ Redis connection failed!")
            print("Make sure Redis is running: docker run -p 6379:6379 redis")
            
        except Exception as e:
            print(f"❌ Demo failed: {e}")
            
        finally:
            self.pubsub.close()
            
if __name__ == "__main__":
    demo = RedisPubSubDemo()
    asyncio.run(demo.run_complete_demo())