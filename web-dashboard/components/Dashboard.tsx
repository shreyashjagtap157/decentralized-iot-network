import React, { useState, useEffect } from 'react';
import Link from 'next/link'; // Ensure next/link is imported
import { useAuth } from '../contexts/AuthContext';
import {
  Container,
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip
} from '@mui/material';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import useWebSocket from 'react-use-websocket';
import apiClient from '../lib/api';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface Device {
  device_id: string;
  device_type: string;
  status: string;
  created_at: string;
}

const Dashboard: React.FC = () => {
  const { logout } = useAuth();
  const [devices, setDevices] = useState<Device[]>([]);
  const [earnings, setEarnings] = useState(0);
  const [chartData, setChartData] = useState({
    labels: [],
    datasets: [{
      label: 'Network Throughput (bytes/sec)',
      data: [],
      borderColor: 'rgb(75, 192, 192)',
      tension: 0.1,
    }],
  });

  const { lastJsonMessage } = useWebSocket(
    `${process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'}/ws/dashboard`
  );

  useEffect(() => {
    fetchDevices();
  }, []);

  useEffect(() => {
    if (lastJsonMessage) {
      const message = lastJsonMessage as any;
      if (message.deviceId && message.bytesTransmitted) {
        // Update chart
        setChartData(prev => {
          const newLabels = [...prev.labels, new Date().toLocaleTimeString()];
          const newData = [...prev.datasets[0].data, message.bytesTransmitted];
          
          if (newLabels.length > 20) {
            newLabels.shift();
            newData.shift();
          }
          
          return {
            ...prev,
            labels: newLabels,
            datasets: [{
              ...prev.datasets[0],
              data: newData,
            }],
          };
        });

        // Update earnings (mock calculation)
        setEarnings(prev => prev + (message.bytesTransmitted * 0.000001));
      }
    }
  }, [lastJsonMessage]);

  const fetchDevices = async () => {
    try {
      const response = await apiClient.get('/api/v1/devices/me');
      setDevices(response.data);
    } catch (error) {
      console.error('Failed to fetch devices:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ACTIVE': return 'success';
      case 'PENDING': return 'warning';
      case 'INACTIVE': return 'error';
      default: return 'default';
    }
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4" component="h1">
          IoT Network Dashboard
        </Typography>
        <Button variant="outlined" onClick={logout}>
          Logout
        </Button>
      </Box>

      <Grid container spacing={3}>
        {/* Earnings Card */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Earnings
              </Typography>
              <Typography variant="h4">
                ${earnings.toFixed(6)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Active Devices Card */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Active Devices
              </Typography>
              <Typography variant="h4">
                {devices.filter(d => d.status === 'ACTIVE').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Total Devices Card */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Devices
              </Typography>
              <Typography variant="h4">
                {devices.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Chart */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Real-time Network Throughput
            </Typography>
            <Line data={chartData} />
          </Paper>
        </Grid>

        {/* Devices Table */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              My Devices
            </Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Device ID</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Created</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {devices.map((device) => (
                    <TableRow key={device.device_id}>
                      <TableCell>{device.device_id}</TableCell>
                      <TableCell>{device.device_type}</TableCell>
                      <TableCell>
                        <Chip 
                          label={device.status} 
                          color={getStatusColor(device.status) as any}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        {new Date(device.created_at).toLocaleDateString()}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Grid>
      </Grid>
      <nav style={{ marginTop: 24 }}>
        <ul>
          <li><Link href="/devices">My Devices</Link></li>
          <li><Link href="/analytics">Analytics</Link></li>
          <li><Link href="/admin">Admin Controls</Link></li>
        </ul>
      </nav>
    </Container>
  );
};

export default Dashboard;
