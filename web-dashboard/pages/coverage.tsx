import React from 'react';
import { Container, Typography, Box } from '@mui/material';
import CoverageMap from '../src/components/CoverageMap';

// Sample data for the coverage map
const sampleNodes = [
  { id: 'node_001', latitude: 40.7128, longitude: -74.006, isActive: true, isGateway: true, qualityScore: 95, connectedUsers: 45, bandwidthMbps: 100, lastSeen: new Date() },
  { id: 'node_002', latitude: 34.0522, longitude: -118.2437, isActive: true, isGateway: false, qualityScore: 88, connectedUsers: 23, bandwidthMbps: 50, lastSeen: new Date() },
  { id: 'node_003', latitude: 51.5074, longitude: -0.1278, isActive: true, isGateway: true, qualityScore: 92, connectedUsers: 67, bandwidthMbps: 200, lastSeen: new Date() },
  { id: 'node_004', latitude: 48.8566, longitude: 2.3522, isActive: true, isGateway: false, qualityScore: 75, connectedUsers: 12, bandwidthMbps: 30, lastSeen: new Date() },
  { id: 'node_005', latitude: 35.6762, longitude: 139.6503, isActive: true, isGateway: true, qualityScore: 98, connectedUsers: 89, bandwidthMbps: 500, lastSeen: new Date() },
  { id: 'node_006', latitude: 22.3193, longitude: 114.1694, isActive: true, isGateway: false, qualityScore: 82, connectedUsers: 34, bandwidthMbps: 75, lastSeen: new Date() },
  { id: 'node_007', latitude: 1.3521, longitude: 103.8198, isActive: true, isGateway: true, qualityScore: 91, connectedUsers: 56, bandwidthMbps: 150, lastSeen: new Date() },
  { id: 'node_008', latitude: -33.8688, longitude: 151.2093, isActive: true, isGateway: false, qualityScore: 85, connectedUsers: 28, bandwidthMbps: 60, lastSeen: new Date() },
  { id: 'node_009', latitude: 55.7558, longitude: 37.6173, isActive: false, isGateway: false, qualityScore: 45, connectedUsers: 0, bandwidthMbps: 0, lastSeen: new Date(Date.now() - 600000) },
  { id: 'node_010', latitude: 19.4326, longitude: -99.1332, isActive: true, isGateway: false, qualityScore: 72, connectedUsers: 18, bandwidthMbps: 40, lastSeen: new Date() },
  { id: 'node_011', latitude: -23.5505, longitude: -46.6333, isActive: true, isGateway: true, qualityScore: 89, connectedUsers: 41, bandwidthMbps: 120, lastSeen: new Date() },
  { id: 'node_012', latitude: 28.6139, longitude: 77.209, isActive: true, isGateway: false, qualityScore: 68, connectedUsers: 52, bandwidthMbps: 35, lastSeen: new Date() },
  { id: 'node_013', latitude: 37.5665, longitude: 126.978, isActive: true, isGateway: true, qualityScore: 94, connectedUsers: 73, bandwidthMbps: 300, lastSeen: new Date() },
  { id: 'node_014', latitude: 52.52, longitude: 13.405, isActive: true, isGateway: false, qualityScore: 87, connectedUsers: 31, bandwidthMbps: 80, lastSeen: new Date() },
  { id: 'node_015', latitude: 43.6532, longitude: -79.3832, isActive: true, isGateway: false, qualityScore: 79, connectedUsers: 25, bandwidthMbps: 55, lastSeen: new Date() },
];

const sampleStats = {
  totalNodes: 1250,
  activeNodes: 1180,
  totalUsers: 45000,
  totalBandwidthTbps: 2.5,
  coverageAreaKm2: 850000,
};

export default function CoveragePage() {
  const handleNodeClick = (node: any) => {
    console.log('Node clicked:', node);
  };

  return (
    <Box sx={{ height: 'calc(100vh - 64px)' }}>
      <Box sx={{ p: 2, pb: 0 }}>
        <Typography variant="h4" fontWeight="bold" gutterBottom>
          🌍 Network Coverage Map
        </Typography>
        <Typography variant="body1" color="textSecondary" mb={2}>
          Real-time visualization of IoT network nodes worldwide
        </Typography>
      </Box>
      
      <Box sx={{ height: 'calc(100% - 100px)', px: 2, pb: 2 }}>
        <CoverageMap
          nodes={sampleNodes}
          stats={sampleStats}
          onNodeClick={handleNodeClick}
          refreshInterval={30000}
        />
      </Box>
    </Box>
  );
}
