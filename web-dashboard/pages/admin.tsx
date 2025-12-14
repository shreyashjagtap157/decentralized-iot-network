import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import apiClient from '../lib/api';
import {
  Container,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Box,
  CircularProgress,
  Tabs,
  Tab
} from '@mui/material';

const AdminPage: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState(0);
  const [users, setUsers] = useState<any[]>([]);
  const [devices, setDevices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.role === 'admin') {
      fetchData();
    }
  }, [user]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [usersRes, devicesRes] = await Promise.all([
        apiClient.get('/api/v1/users/'),
        apiClient.get('/api/v1/devices/')
      ]);
      setUsers(usersRes.data);
      setDevices(devicesRes.data);
    } catch (error) {
      console.error('Failed to fetch admin data', error);
    } finally {
      setLoading(false);
    }
  };

  if (!user || user.role !== 'admin') {
    return (
      <Container sx={{ mt: 4 }}>
        <Typography variant="h5" color="error">Access Denied: Admin privileges required.</Typography>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" sx={{ mb: 4, fontWeight: 700 }}>
        Admin Dashboard
      </Typography>

      <Paper sx={{ width: '100%', mb: 2 }}>
        <Tabs value={activeTab} onChange={(_, val) => setActiveTab(val)} sx={{ px: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Tab label="Users" />
          <Tab label="All Devices" />
        </Tabs>
        
        {loading ? (
          <Box sx={{ p: 4, display: 'flex', justifyContent: 'center' }}>
            <CircularProgress />
          </Box>
        ) : (
          <Box sx={{ p: 0 }}>
            {activeTab === 0 && (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Username</TableCell>
                      <TableCell>Email</TableCell>
                      <TableCell>Role</TableCell>
                      <TableCell>Status</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {users.map((u) => (
                      <TableRow key={u.id}>
                        <TableCell>{u.username}</TableCell>
                        <TableCell>{u.email}</TableCell>
                        <TableCell>
                          <Chip label={u.role} color={u.role === 'admin' ? 'secondary' : 'default'} size="small" />
                        </TableCell>
                        <TableCell>
                          <Chip label={u.is_active ? 'Active' : 'Inactive'} color={u.is_active ? 'success' : 'error'} size="small" />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}

            {activeTab === 1 && (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Device ID</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell>Owner</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Created At</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {devices.map((d) => (
                      <TableRow key={d.device_id}>
                        <TableCell sx={{ fontFamily: 'monospace' }}>{d.device_id}</TableCell>
                        <TableCell>{d.device_type}</TableCell>
                        <TableCell sx={{ fontFamily: 'monospace' }}>{d.owner_address}</TableCell>
                        <TableCell>
                          <Chip 
                            label={d.status} 
                            color={d.status === 'ACTIVE' ? 'success' : 'warning'} 
                            variant="outlined"
                            size="small" 
                          />
                        </TableCell>
                        <TableCell>{new Date(d.created_at).toLocaleDateString()}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Box>
        )}
      </Paper>
    </Container>
  );
};

export default AdminPage;
