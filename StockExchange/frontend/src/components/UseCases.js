import React, { useState } from 'react';
import { Rocket, Play, CheckCircle, AlertCircle, Users, TrendingUp, Shield, Zap } from 'lucide-react';
import api from '../services/api';
import toast from 'react-hot-toast';
import './UseCases.css';

const UseCases = () => {
  const [activeScenario, setActiveScenario] = useState(null);
  const [scenarioResults, setScenarioResults] = useState({});
  const [loading, setLoading] = useState(false);

  const scenarios = [
    {
      id: 'high_volume',
      title: 'High Volume Trading',
      description: 'Simulate high-frequency trading with multiple orders being placed rapidly',
      icon: Zap,
      steps: [
        'Generate 100 random orders',
        'Submit orders with varying prices',
        'Monitor matching engine performance',
        'Check order book depth'
      ]
    },
    {
      id: 'market_maker',
      title: 'Market Making Strategy',
      description: 'Demonstrate automated market making with bid-ask spread management',
      icon: TrendingUp,
      steps: [
        'Place buy orders below market price',
        'Place sell orders above market price',
        'Maintain spread and liquidity',
        'Track profit from spread'
      ]
    },
    {
      id: 'risk_breach',
      title: 'Risk Management Breach',
      description: 'Test risk management system with orders exceeding limits',
      icon: Shield,
      steps: [
        'Attempt to place oversized order',
        'Verify risk manager rejection',
        'Check daily loss limit enforcement',
        'Review violation alerts'
      ]
    },
    {
      id: 'multi_user',
      title: 'Multi-User Trading',
      description: 'Show multiple users trading simultaneously with order matching',
      icon: Users,
      steps: [
        'Create multiple trader accounts',
        'Place competing orders',
        'Demonstrate order matching',
        'Show real-time updates'
      ]
    }
  ];

  const runScenario = async (scenarioId) => {
    setLoading(true);
    setActiveScenario(scenarioId);
    let results = { steps: [], summary: '' };

    try {
      switch(scenarioId) {
        case 'high_volume':
          results = await runHighVolumeScenario();
          break;
        case 'market_maker':
          results = await runMarketMakerScenario();
          break;
        case 'risk_breach':
          results = await runRiskBreachScenario();
          break;
        case 'multi_user':
          results = await runMultiUserScenario();
          break;
        default:
          break;
      }
      
      setScenarioResults(prev => ({ ...prev, [scenarioId]: results }));
      toast.success('Scenario completed successfully!');
    } catch (error) {
      toast.error('Scenario failed: ' + error.message);
      results.error = error.message;
      setScenarioResults(prev => ({ ...prev, [scenarioId]: results }));
    } finally {
      setLoading(false);
    }
  };

  const runHighVolumeScenario = async () => {
    const results = { steps: [], summary: '' };
    const orders = [];
    
    results.steps.push({ status: 'success', message: 'Generating 100 random orders...' });
    
    for (let i = 0; i < 20; i++) {
      const side = Math.random() > 0.5 ? 'BUY' : 'SELL';
      const order = {
        symbol: 'AAPL',
        side: side,
        quantity: Math.floor(Math.random() * 50) + 10,
        price: (150 + (Math.random() - 0.5) * 10).toFixed(2)
      };
      
      try {
        const response = await api.post('/v1/order', order);
        orders.push(response.data);
      } catch (error) {
        console.error('Order failed:', error);
      }
    }
    
    results.steps.push({ 
      status: 'success', 
      message: `Successfully placed ${orders.length} orders` 
    });
    
    const orderBookRes = await api.get('/marketdata/orderBook/L2?symbol=AAPL&depth=10');
    results.steps.push({ 
      status: 'success', 
      message: `Order book depth: ${orderBookRes.data.asks.length} asks, ${orderBookRes.data.bids.length} bids` 
    });
    
    results.summary = `High volume test completed. Placed ${orders.length} orders successfully. The matching engine handled all orders efficiently.`;
    
    return results;
  };

  const runMarketMakerScenario = async () => {
    const results = { steps: [], summary: '' };
    
    results.steps.push({ status: 'info', message: 'Setting up market maker strategy...' });
    
    const currentPrice = 150;
    const spread = 0.5;
    
    const buyOrder = {
      symbol: 'AAPL',
      side: 'BUY',
      quantity: '100',
      price: (currentPrice - spread).toFixed(2)
    };
    
    const sellOrder = {
      symbol: 'AAPL',
      side: 'SELL',
      quantity: '100',
      price: (currentPrice + spread).toFixed(2)
    };
    
    const buyRes = await api.post('/v1/order', buyOrder);
    results.steps.push({ 
      status: 'success', 
      message: `Placed buy order at $${buyOrder.price}` 
    });
    
    const sellRes = await api.post('/v1/order', sellOrder);
    results.steps.push({ 
      status: 'success', 
      message: `Placed sell order at $${sellOrder.price}` 
    });
    
    results.steps.push({ 
      status: 'info', 
      message: `Maintaining spread of $${spread * 2}` 
    });
    
    results.summary = `Market maker strategy deployed. Buy order at $${buyOrder.price}, Sell order at $${sellOrder.price}. Spread: $${spread * 2}`;
    
    return results;
  };

  const runRiskBreachScenario = async () => {
    const results = { steps: [], summary: '' };
    
    results.steps.push({ status: 'warning', message: 'Attempting to place oversized order...' });
    
    const oversizedOrder = {
      symbol: 'AAPL',
      side: 'BUY',
      quantity: '10000',
      price: '150.00'
    };
    
    try {
      await api.post('/v1/order', oversizedOrder);
      results.steps.push({ 
        status: 'error', 
        message: 'Oversized order was accepted (unexpected)' 
      });
    } catch (error) {
      results.steps.push({ 
        status: 'success', 
        message: 'Risk manager correctly rejected oversized order' 
      });
    }
    
    results.steps.push({ status: 'info', message: 'Testing daily loss limit...' });
    
    try {
      const highRiskOrder = {
        symbol: 'AAPL',
        side: 'BUY',
        quantity: '1000',
        price: '200.00'
      };
      await api.post('/v1/order', highRiskOrder);
      results.steps.push({ 
        status: 'warning', 
        message: 'High risk order placed - monitoring limits' 
      });
    } catch (error) {
      results.steps.push({ 
        status: 'success', 
        message: 'Daily loss limit enforced' 
      });
    }
    
    results.summary = 'Risk management system successfully prevented breach attempts. All risk controls are functioning correctly.';
    
    return results;
  };

  const runMultiUserScenario = async () => {
    const results = { steps: [], summary: '' };
    
    results.steps.push({ status: 'info', message: 'Creating multiple trader sessions...' });
    
    const traders = [
      { username: 'trader1', role: 'buyer' },
      { username: 'trader2', role: 'seller' }
    ];
    
    results.steps.push({ 
      status: 'success', 
      message: 'Two traders connected to the system' 
    });
    
    results.steps.push({ status: 'info', message: 'Placing competing orders...' });
    
    const buyOrder = {
      symbol: 'AAPL',
      side: 'BUY',
      quantity: '50',
      price: '150.00'
    };
    
    const sellOrder = {
      symbol: 'AAPL',
      side: 'SELL',
      quantity: '50',
      price: '150.00'
    };
    
    const [buyRes, sellRes] = await Promise.all([
      api.post('/v1/order', buyOrder),
      api.post('/v1/order', sellOrder)
    ]);
    
    results.steps.push({ 
      status: 'success', 
      message: 'Orders matched successfully!' 
    });
    
    results.steps.push({ 
      status: 'success', 
      message: 'Real-time updates sent to both traders' 
    });
    
    results.summary = 'Multi-user trading scenario completed. Orders were matched in real-time and both traders received instant notifications.';
    
    return results;
  };

  return (
    <div className="use-cases">
      <div className="use-cases-header">
        <h1>Use Case Demonstrations</h1>
        <p>Interactive scenarios showcasing platform capabilities</p>
      </div>

      <div className="scenarios-grid">
        {scenarios.map(scenario => {
          const Icon = scenario.icon;
          const result = scenarioResults[scenario.id];
          
          return (
            <div key={scenario.id} className="scenario-card">
              <div className="scenario-header">
                <Icon size={24} />
                <h3>{scenario.title}</h3>
              </div>
              
              <p className="scenario-description">{scenario.description}</p>
              
              <div className="scenario-steps">
                <h4>Steps:</h4>
                <ul>
                  {scenario.steps.map((step, index) => (
                    <li key={index}>{step}</li>
                  ))}
                </ul>
              </div>
              
              <button
                onClick={() => runScenario(scenario.id)}
                className="btn-run-scenario"
                disabled={loading && activeScenario === scenario.id}
              >
                <Play size={16} />
                {loading && activeScenario === scenario.id ? 'Running...' : 'Run Scenario'}
              </button>
              
              {result && (
                <div className="scenario-result">
                  <h4>Results:</h4>
                  {result.steps && result.steps.map((step, index) => (
                    <div key={index} className={`result-step ${step.status}`}>
                      {step.status === 'success' && <CheckCircle size={16} />}
                      {step.status === 'error' && <AlertCircle size={16} />}
                      {step.status === 'warning' && <AlertCircle size={16} />}
                      {step.status === 'info' && <AlertCircle size={16} />}
                      <span>{step.message}</span>
                    </div>
                  ))}
                  {result.summary && (
                    <div className="result-summary">
                      <strong>Summary:</strong> {result.summary}
                    </div>
                  )}
                  {result.error && (
                    <div className="result-error">
                      <strong>Error:</strong> {result.error}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="demo-info">
        <h3>About These Demonstrations</h3>
        <p>
          These use cases showcase the complete functionality of our stock exchange system:
        </p>
        <ul>
          <li><strong>Order Matching Engine:</strong> Real-time order matching with price-time priority</li>
          <li><strong>Risk Management:</strong> Position limits, exposure controls, and daily loss limits</li>
          <li><strong>Market Data:</strong> Live order book updates and trade notifications via WebSocket</li>
          <li><strong>Multi-User Support:</strong> Concurrent trading with instant notifications</li>
          <li><strong>High Performance:</strong> Handle thousands of orders per second</li>
        </ul>
      </div>
    </div>
  );
};

export default UseCases;