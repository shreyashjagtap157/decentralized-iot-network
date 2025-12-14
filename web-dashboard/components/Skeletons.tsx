import React from 'react';
import { Box, Skeleton, Card, CardContent, Grid, Paper, Table, TableBody, TableCell, TableHead, TableRow } from '@mui/material';

/**
 * Skeleton components for loading states.
 * These provide a better UX than spinners by showing the expected layout.
 */

export const StatCardSkeleton: React.FC = () => (
  <Card sx={{ borderRadius: 3, boxShadow: '0 4px 20px rgba(0,0,0,0.08)' }}>
    <CardContent sx={{ textAlign: 'center', py: 3 }}>
      <Skeleton variant="text" width="60%" sx={{ mx: 'auto', mb: 1 }} />
      <Skeleton variant="text" width="40%" height={50} sx={{ mx: 'auto' }} />
    </CardContent>
  </Card>
);

export const DeviceTableSkeleton: React.FC<{ rows?: number }> = ({ rows = 5 }) => (
  <Paper sx={{ borderRadius: 3, overflow: 'hidden' }}>
    <Table>
      <TableHead sx={{ bgcolor: '#f8f9fa' }}>
        <TableRow>
          {['Device ID', 'Type', 'Status', 'Data', 'Location', 'Created', 'Actions'].map((header) => (
            <TableCell key={header} sx={{ fontWeight: 600 }}>
              <Skeleton variant="text" width={80} />
            </TableCell>
          ))}
        </TableRow>
      </TableHead>
      <TableBody>
        {Array.from({ length: rows }).map((_, index) => (
          <TableRow key={index}>
            <TableCell><Skeleton variant="text" width={120} /></TableCell>
            <TableCell><Skeleton variant="rounded" width={60} height={24} /></TableCell>
            <TableCell><Skeleton variant="rounded" width={60} height={24} /></TableCell>
            <TableCell><Skeleton variant="text" width={60} /></TableCell>
            <TableCell><Skeleton variant="text" width={100} /></TableCell>
            <TableCell><Skeleton variant="text" width={80} /></TableCell>
            <TableCell>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Skeleton variant="circular" width={32} height={32} />
                <Skeleton variant="circular" width={32} height={32} />
              </Box>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  </Paper>
);

export const ChartSkeleton: React.FC<{ height?: number }> = ({ height = 300 }) => (
  <Paper sx={{ p: 3, borderRadius: 3 }}>
    <Skeleton variant="text" width={150} height={30} sx={{ mb: 2 }} />
    <Skeleton variant="rectangular" height={height} sx={{ borderRadius: 2 }} />
  </Paper>
);

export const DashboardSkeleton: React.FC = () => (
  <Box>
    {/* Stats Row */}
    <Grid container spacing={3} sx={{ mb: 4 }}>
      {[1, 2, 3, 4].map((i) => (
        <Grid item xs={12} sm={6} md={3} key={i}>
          <StatCardSkeleton />
        </Grid>
      ))}
    </Grid>
    {/* Charts Row */}
    <Grid container spacing={3}>
      <Grid item xs={12} md={8}>
        <ChartSkeleton height={350} />
      </Grid>
      <Grid item xs={12} md={4}>
        <ChartSkeleton height={350} />
      </Grid>
    </Grid>
  </Box>
);

export const AnalyticsSkeleton: React.FC = () => (
  <Box>
    <Grid container spacing={3} sx={{ mb: 4 }}>
      {[1, 2, 3, 4].map((i) => (
        <Grid item xs={12} sm={6} md={3} key={i}>
          <StatCardSkeleton />
        </Grid>
      ))}
    </Grid>
    <Grid container spacing={3}>
      <Grid item xs={12} lg={6}>
        <ChartSkeleton height={300} />
      </Grid>
      <Grid item xs={12} lg={6}>
        <ChartSkeleton height={300} />
      </Grid>
    </Grid>
  </Box>
);

export const WalletSkeleton: React.FC = () => (
  <Box>
    <Paper sx={{ p: 4, borderRadius: 3, mb: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Skeleton variant="text" width={100} />
          <Skeleton variant="text" width={200} height={50} />
        </Box>
        <Skeleton variant="rounded" width={150} height={45} />
      </Box>
    </Paper>
    <Grid container spacing={3}>
      <Grid item xs={12} md={4}>
        <StatCardSkeleton />
      </Grid>
      <Grid item xs={12} md={4}>
        <StatCardSkeleton />
      </Grid>
      <Grid item xs={12} md={4}>
        <StatCardSkeleton />
      </Grid>
    </Grid>
  </Box>
);
