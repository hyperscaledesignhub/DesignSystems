import React, { createContext, useContext, useEffect, useState } from 'react';
import { io } from 'socket.io-client';

const WebSocketContext = createContext();

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within WebSocketProvider');
  }
  return context;
};

export const WebSocketProvider = ({ children }) => {
  const [socket, setSocket] = useState(null);
  const [connected, setConnected] = useState(false);
  const [marketData, setMarketData] = useState({});
  const [orderUpdates, setOrderUpdates] = useState([]);
  const [tradeUpdates, setTradeUpdates] = useState([]);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

    const newSocket = io('ws://localhost:8347', {
      auth: { token },
      transports: ['websocket']
    });

    newSocket.on('connect', () => {
      console.log('WebSocket connected');
      setConnected(true);
    });

    newSocket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      setConnected(false);
    });

    newSocket.on('market_data', (data) => {
      setMarketData(prev => ({ ...prev, [data.symbol]: data }));
    });

    newSocket.on('order_update', (data) => {
      setOrderUpdates(prev => [data, ...prev].slice(0, 50));
    });

    newSocket.on('trade_update', (data) => {
      setTradeUpdates(prev => [data, ...prev].slice(0, 50));
    });

    setSocket(newSocket);

    return () => {
      newSocket.close();
    };
  }, []);

  const subscribeToSymbol = (symbol) => {
    if (socket && connected) {
      socket.emit('subscribe', { symbol });
    }
  };

  const unsubscribeFromSymbol = (symbol) => {
    if (socket && connected) {
      socket.emit('unsubscribe', { symbol });
    }
  };

  const value = {
    socket,
    connected,
    marketData,
    orderUpdates,
    tradeUpdates,
    subscribeToSymbol,
    unsubscribeFromSymbol
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};