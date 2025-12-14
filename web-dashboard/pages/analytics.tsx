import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useRouter } from 'next/router';
import apiClient from '../lib/api';
import {
  Container,
  Typography,
  Box,
  Card,
  CardContent,
  Grid,
  Paper,
  CircularProgress,
  Alert,
  ToggleButton,
  ToggleButtonGroup,
  Divider
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  AccountBalance as AccountBalanceIcon,
  Speed as SpeedIcon,
  Timeline as TimelineIcon,
  Assessment as AssessmentIcon
} from '@mui/icons-material';
import { Line, Doughnut, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import useWebSocket from 'react-use-websocket';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface AnalyticsData {
  totalEarnings: number;
  todayEarnings: number;
  activeDevices: number;
  totalDevices: number;
  averageQuality: number;
  hourlyThroughput: { hour: string; bytes: number }[];
  dailyEarnings: { date: string; amount: number }[];
  deviceBreakdown: { type: string; count: number }[];
}

const AnalyticsPage: React.FC = () => {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<string>('7d');
  const [realtimeData, setRealtimeData] = useState<number[]>([]);
  const [realtimeLabels, setRealtimeLabels] = useState<string[]>([]);

  // WebSocket for real-time updates
  const { lastJsonMessage } = useWebSocket(
    `${process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'}/ws/analytics`,
    {
      shouldReconnect: () => true,
      reconnectInterval: 3000,
    }
  );

  const fetchAnalytics = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Try to fetch from API, fall back to mock data if endpoint doesn't exist
      try {
        const response = await apiClient.get(`/api/v1/analytics/user-earnings?range=${timeRange}`);
        setAnalytics(response.data);
      } catch {
        // Use mock data for demonstration
        setAnalytics({
          totalEarnings: 12.5478,
          todayEarnings: 0.2341,
          activeDevices: 5,
          totalDevices: 8,
          averageQuality: 94.5,
          hourlyThroughput: generateHourlyData(),
          dailyEarnings: generateDailyEarnings(),
          deviceBreakdown: [
            { type: 'Sensor', count: 4 },
            { type: 'Relay', count: 2 },
            { type: 'Gateway', count: 1 },
            { type: 'Repeater', count: 1 }
          ]
        });
      }
    } catch (err: any) {
      setError('Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  }, [timeRange]);

  // Generate mock hourly data
  const generateHourlyData = () => {
    const hours = [];
    for (let i = 23; i >= 0; i--) {
      const date = new Date();
      date.setHours(date.getHours() - i);
      hours.push({
        hour: date.toISOString(),
        bytes: Math.floor(Math.random() * 500000) + 100000
      });
    }
    return hours;
  };

  // Generate mock daily earnings
  const generateDailyEarnings = () => {
    const days = [];
    for (let i = 6; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      days.push({
        date: date.toISOString().split('T')[0],
        amount: Math.random() * 2 + 0.5
      });
    }
    return days;
  };

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
      return;
    }
    if (user) {
      fetchAnalytics();
    }
  }, [user, authLoading, router, fetchAnalytics]);

  // Handle real-time WebSocket messages
  useEffect(() => {
    if (lastJsonMessage) {
      const msg = lastJsonMessage as any;
      if (msg.bytesTransmitted) {
        setRealtimeData(prev => {
          const newData = [...prev, msg.bytesTransmitted];
          return newData.slice(-20);
        });
        setRealtimeLabels(prev => {
          const newLabels = [...prev, new Date().toLocaleTimeString()];
          return newLabels.slice(-20);
        });
      }
    }
  }, [lastJsonMessage]);

  if (authLoading || loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
        <CircularProgress size={60} />
      </Box>
    );
  }

  if (!user) {
    return null;
  }

  // Chart configurations
  const earningsChartData = {
    labels: analytics?.dailyEarnings.map(d => new Date(d.date).toLocaleDateString('en-US', { weekday: 'short' })) || [],
    datasets: [{
      label: 'Daily Earnings (NWR)',
      data: analytics?.dailyEarnings.map(d => d.amount) || [],
      fill: true,
      backgroundColor: 'rgba(102, 126, 234, 0.1)',
      borderColor: '#667eea',
      tension: 0.4,
      pointBackgroundColor: '#667eea',
      pointBorderWidth: 2,
      pointRadius: 4,
    }]
  };

  const throughputChartData = {
    labels: analytics?.hourlyThroughput.map(t => 
      new Date(t.hour).toLocaleTimeString('en-US', { hour: '2-digit' })
    ) || [],
    datasets: [{
      label: 'Data Throughput (KB)',
      data: analytics?.hourlyThroughput.map(t => t.bytes / 1024) || [],
      fill: true,
      backgroundColor: 'rgba(76, 175, 80, 0.1)',
      borderColor: '#4caf50',
      tension: 0.4,
    }]
  };

  const realtimeChartData = {
    labels: realtimeLabels.length > 0 ? realtimeLabels : ['Now'],
    datasets: [{
      label: 'Live Throughput (bytes)',
      data: realtimeData.length > 0 ? realtimeData : [0],
      borderColor: '#ff9800',
      backgroundColor: 'rgba(255, 152, 0, 0.1)',
      fill: true,
      tension: 0.4,
    }]
  };

  const deviceBreakdownData = {
    labels: analytics?.deviceBreakdown.map(d => d.type) || [],
    datasets: [{
      data: analytics?.deviceBreakdown.map(d => d.count) || [],
      backgroundColor: ['#667eea', '#4caf50', '#ff9800', '#f44336', '#9c27b0'],
      borderWidth: 0,
    }]
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
    },
    scales: {
      x: { grid: { display: false } },
      y: { grid: { color: 'rgba(0,0,0,0.05)' } }
    }
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      {/* Header */}
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        mb: 4,
        p: 3,
        borderRadius: 3,
        background: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
        color: 'white',
        boxShadow: '0 10px 40px rgba(17, 153, 142, 0.3)'
      }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>
            Network Analytics
          </Typography>
          <Typography variant="body1" sx={{ opacity: 0.9, mt: 0.5 }}>
            Track your earnings and network performance
          </Typography>
        </Box>
        <ToggleButtonGroup
          value={timeRange}
          exclusive
          onChange={(_, value) => value && setTimeRange(value)}
          sx={{ bgcolor: 'rgba(255,255,255,0.2)', borderRadius: 2 }}
        >
          <ToggleButton value="24h" sx={{ color: 'white', '&.Mui-selected': { bgcolor: 'rgba(255,255,255,0.3)', color: 'white' }}}>24H</ToggleButton>
          <ToggleButton value="7d" sx={{ color: 'white', '&.Mui-selected': { bgcolor: 'rgba(255,255,255,0.3)', color: 'white' }}}>7D</ToggleButton>
          <ToggleButton value="30d" sx={{ color: 'white', '&.Mui-selected': { bgcolor: 'rgba(255,255,255,0.3)', color: 'white' }}}>30D</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>
      )}

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ 
            borderRadius: 3, 
            boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
            transition: 'all 0.3s',
            '&:hover': { transform: 'translateY(-4px)', boxShadow: '0 8px 30px rgba(0,0,0,0.12)' }
          }}>
            <CardContent sx={{ textAlign: 'center', py: 3 }}>
              <AccountBalanceIcon sx={{ fontSize: 40, color: '#667eea', mb: 1 }} />
              <Typography color="textSecondary" variant="body2">
                Total Earnings
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 700, color: '#667eea' }}>
                {analytics?.totalEarnings.toFixed(4)}
              </Typography>
              <Typography variant="caption" color="textSecondary">NWR</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ 
            borderRadius: 3, 
            boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
            transition: 'all 0.3s',
            '&:hover': { transform: 'translateY(-4px)', boxShadow: '0 8px 30px rgba(0,0,0,0.12)' }
          }}>
            <CardContent sx={{ textAlign: 'center', py: 3 }}>
              <TrendingUpIcon sx={{ fontSize: 40, color: '#4caf50', mb: 1 }} />
              <Typography color="textSecondary" variant="body2">
                Today's Earnings
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 700, color: '#4caf50' }}>
                +{analytics?.todayEarnings.toFixed(4)}
              </Typography>
              <Typography variant="caption" color="textSecondary">NWR</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ 
            borderRadius: 3, 
            boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
            transition: 'all 0.3s',
            '&:hover': { transform: 'translateY(-4px)', boxShadow: '0 8px 30px rgba(0,0,0,0.12)' }
          }}>
            <CardContent sx={{ textAlign: 'center', py: 3 }}>
              <AssessmentIcon sx={{ fontSize: 40, color: '#ff9800', mb: 1 }} />
              <Typography color="textSecondary" variant="body2">
                Active Devices
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 700, color: '#ff9800' }}>
                {analytics?.activeDevices}/{analytics?.totalDevices}
              </Typography>
              <Typography variant="caption" color="textSecondary">online</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ 
            borderRadius: 3, 
            boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
            transition: 'all 0.3s',
            '&:hover': { transform: 'translateY(-4px)', boxShadow: '0 8px 30px rgba(0,0,0,0.12)' }
          }}>
            <CardContent sx={{ textAlign: 'center', py: 3 }}>
              <SpeedIcon sx={{ fontSize: 40, color: '#9c27b0', mb: 1 }} />
              <Typography color="textSecondary" variant="body2">
                Avg Quality Score
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 700, color: '#9c27b0' }}>
                {analytics?.averageQuality.toFixed(1)}%
              </Typography>
              <Typography variant="caption" color="textSecondary">network quality</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Charts Row 1 */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, borderRadius: 3, boxShadow: '0 4px 20px rgba(0,0,0,0.08)' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <TimelineIcon sx={{ color: '#667eea' }} />
              <Typography variant="h6" sx={{ fontWeight: 600 }}>Earnings Over Time</Typography>
            </Box>
            <Box sx={{ height: 300 }}>
              <Line data={earningsChartData} options={chartOptions} />
            </Box>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, borderRadius: 3, boxShadow: '0 4px 20px rgba(0,0,0,0.08)', height: '100%' }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>Device Breakdown</Typography>
            <Box sx={{ height: 260, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              <Doughnut 
                data={deviceBreakdownData} 
                options={{ 
                  responsive: true, 
                  maintainAspectRatio: false,
                  plugins: { legend: { position: 'bottom' } }
                }} 
              />
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* Charts Row 2 */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, borderRadius: 3, boxShadow: '0 4px 20px rgba(0,0,0,0.08)' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <SpeedIcon sx={{ color: '#4caf50' }} />
              <Typography variant="h6" sx={{ fontWeight: 600 }}>Hourly Throughput</Typography>
            </Box>
            <Box sx={{ height: 250 }}>
              <Bar 
                data={{
                  labels: analytics?.hourlyThroughput.slice(-12).map(t => 
                    new Date(t.hour).toLocaleTimeString('en-US', { hour: '2-digit' })
                  ) || [],
                  datasets: [{
                    label: 'KB transferred',
                    data: analytics?.hourlyThroughput.slice(-12).map(t => t.bytes / 1024) || [],
                    backgroundColor: 'rgba(76, 175, 80, 0.6)',
                    borderRadius: 4,
                  }]
                }} 
                options={chartOptions} 
              />
            </Box>
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, borderRadius: 3, boxShadow: '0 4px 20px rgba(0,0,0,0.08)' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <Box sx={{ 
                width: 8, 
                height: 8, 
                borderRadius: '50%', 
                bgcolor: '#ff9800', 
                animation: 'pulse 1.5s infinite'
              }} />
              <Typography variant="h6" sx={{ fontWeight: 600 }}>Live Data Stream</Typography>
            </Box>
            <Box sx={{ height: 250 }}>
              <Line data={realtimeChartData} options={chartOptions} />
            </Box>
          </Paper>
        </Grid>
      </Grid>

      <style jsx global>{`
        @keyframes pulse {
          0% { opacity: 1; }
          50% { opacity: 0.4; }
          100% { opacity: 1; }
        }
      `}</style>
    </Container>
  );
};

export default AnalyticsPage;
