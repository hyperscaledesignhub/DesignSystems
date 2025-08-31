import React, { useState, useEffect } from 'react';
import {
  Typography,
  Grid,
  Card,
  CardContent,
  Box,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip
} from '@mui/material';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

function Analytics() {
  const [timeRange, setTimeRange] = useState('7d');
  const [refreshing, setRefreshing] = useState(false);

  // Sample data - in real app, this would come from APIs
  const transactionVolumeData = [
    { date: '08-24', volume: 145, amount: 32500 },
    { date: '08-25', volume: 167, amount: 41200 },
    { date: '08-26', volume: 134, amount: 28900 },
    { date: '08-27', volume: 189, amount: 45600 },
    { date: '08-28', volume: 156, amount: 38400 },
    { date: '08-29', volume: 198, amount: 52100 },
    { date: '08-30', volume: 123, amount: 31200 }
  ];

  const paymentMethodData = [
    { name: 'Credit Card', value: 45, amount: 125400 },
    { name: 'Debit Card', value: 30, amount: 82300 },
    { name: 'PayPal', value: 15, amount: 41200 },
    { name: 'Bank Transfer', value: 8, amount: 22100 },
    { name: 'Other', value: 2, amount: 5800 }
  ];

  const successRateData = [
    { date: '08-24', successful: 142, failed: 3, successRate: 97.9 },
    { date: '08-25', successful: 164, failed: 3, successRate: 98.2 },
    { date: '08-26', successful: 129, failed: 5, successRate: 96.3 },
    { date: '08-27', successful: 185, failed: 4, successRate: 97.9 },
    { date: '08-28', successful: 153, failed: 3, successRate: 98.1 },
    { date: '08-29', successful: 195, failed: 3, successRate: 98.5 },
    { date: '08-30', successful: 121, failed: 2, successRate: 98.4 }
  ];

  const merchantPerformanceData = [
    { merchant: 'Amazon', transactions: 45, revenue: 12500, avgAmount: 278 },
    { merchant: 'Walmart', transactions: 38, revenue: 8900, avgAmount: 234 },
    { merchant: 'Target', transactions: 29, revenue: 7200, avgAmount: 248 },
    { merchant: 'Best Buy', transactions: 22, revenue: 9800, avgAmount: 445 },
    { merchant: 'Home Depot', transactions: 18, revenue: 6400, avgAmount: 356 }
  ];

  const revenueGrowthData = [
    { month: 'Jan', revenue: 145000, growth: 12.5 },
    { month: 'Feb', revenue: 167000, growth: 15.2 },
    { month: 'Mar', revenue: 134000, growth: -19.8 },
    { month: 'Apr', revenue: 189000, growth: 41.0 },
    { month: 'May', revenue: 201000, growth: 6.3 },
    { month: 'Jun', revenue: 223000, growth: 10.9 },
    { month: 'Jul', revenue: 245000, growth: 9.9 },
    { month: 'Aug', revenue: 267000, growth: 8.9 }
  ];

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          📊 Payment Analytics Dashboard
        </Typography>
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Time Range</InputLabel>
          <Select
            value={timeRange}
            label="Time Range"
            onChange={(e) => setTimeRange(e.target.value)}
          >
            <MenuItem value="1d">Last 24h</MenuItem>
            <MenuItem value="7d">Last 7 days</MenuItem>
            <MenuItem value="30d">Last 30 days</MenuItem>
            <MenuItem value="90d">Last 90 days</MenuItem>
          </Select>
        </FormControl>
      </Box>
      
      <Grid container spacing={3}>
        {/* Key Metrics Cards */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="textSecondary">Total Revenue</Typography>
              <Typography variant="h3" color="success.main">$267K</Typography>
              <Chip label="+8.9%" color="success" size="small" />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="textSecondary">Transactions</Typography>
              <Typography variant="h3" color="primary">1,089</Typography>
              <Chip label="+12.3%" color="success" size="small" />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="textSecondary">Success Rate</Typography>
              <Typography variant="h3" color="success.main">98.4%</Typography>
              <Chip label="+0.3%" color="success" size="small" />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="textSecondary">Avg Amount</Typography>
              <Typography variant="h3" color="primary">$245</Typography>
              <Chip label="-2.1%" color="error" size="small" />
            </CardContent>
          </Card>
        </Grid>

        {/* Transaction Volume & Revenue */}
        <Grid item xs={12} lg={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Transaction Volume & Revenue Trend</Typography>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={transactionVolumeData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis yAxisId="left" orientation="left" />
                  <YAxis yAxisId="right" orientation="right" />
                  <Tooltip formatter={(value, name) => 
                    name === 'amount' ? [`$${value.toLocaleString()}`, 'Revenue'] : [value, 'Volume']
                  } />
                  <Legend />
                  <Bar yAxisId="left" dataKey="volume" fill="#8884d8" name="Transaction Volume" />
                  <Line yAxisId="right" type="monotone" dataKey="amount" stroke="#82ca9d" name="Revenue ($)" strokeWidth={3} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Payment Methods */}
        <Grid item xs={12} lg={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Payment Methods</Typography>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={paymentMethodData}
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    dataKey="value"
                    label={({name, value}) => `${name}\n${value}%`}
                  >
                    {paymentMethodData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value, name) => [`${value}%`, 'Share']} />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Success Rate Trend */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Payment Success Rate</Typography>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={successRateData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis domain={[95, 100]} />
                  <Tooltip formatter={(value) => [`${value}%`, 'Success Rate']} />
                  <Area 
                    type="monotone" 
                    dataKey="successRate" 
                    stroke="#4caf50" 
                    fill="#4caf50" 
                    fillOpacity={0.3}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Revenue Growth */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Monthly Revenue Growth</Typography>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={revenueGrowthData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis yAxisId="left" orientation="left" />
                  <YAxis yAxisId="right" orientation="right" />
                  <Tooltip 
                    formatter={(value, name) => 
                      name === 'revenue' ? [`$${value.toLocaleString()}`, 'Revenue'] : [`${value}%`, 'Growth']
                    } 
                  />
                  <Legend />
                  <Bar yAxisId="left" dataKey="revenue" fill="#2196f3" name="Revenue ($)" />
                  <Line yAxisId="right" type="monotone" dataKey="growth" stroke="#ff5722" name="Growth %" strokeWidth={2} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Top Merchants */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Top Merchant Performance</Typography>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={merchantPerformanceData} layout="horizontal">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis dataKey="merchant" type="category" width={80} />
                  <Tooltip 
                    formatter={(value, name) => {
                      if (name === 'revenue') return [`$${value.toLocaleString()}`, 'Revenue'];
                      if (name === 'transactions') return [value, 'Transactions'];
                      return [value, name];
                    }}
                  />
                  <Legend />
                  <Bar dataKey="transactions" fill="#8884d8" name="Transactions" />
                  <Bar dataKey="revenue" fill="#82ca9d" name="Revenue ($)" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

export default Analytics;