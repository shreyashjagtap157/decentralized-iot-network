import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Box, Paper, Typography, Chip, Switch, FormControlLabel, Slider } from '@mui/material';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';
import 'leaflet/dist/leaflet.css';

// ==================== Types ====================

interface NodeLocation {
  id: string;
  latitude: number;
  longitude: number;
  isActive: boolean;
  isGateway: boolean;
  qualityScore: number;
  connectedUsers: number;
  bandwidthMbps: number;
  lastSeen: Date;
}

interface NetworkStats {
  totalNodes: number;
  activeNodes: number;
  totalUsers: number;
  totalBandwidthTbps: number;
  coverageAreaKm2: number;
}

interface CoverageMapProps {
  nodes: NodeLocation[];
  stats: NetworkStats;
  onNodeClick?: (node: NodeLocation) => void;
  refreshInterval?: number;
}

// ==================== Map Controls ====================

function MapUpdater({ center, zoom }: { center: [number, number]; zoom: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom);
  }, [center, zoom, map]);
  return null;
}

// ==================== Node Marker ====================

function NodeMarker({ node, onClick }: { node: NodeLocation; onClick?: (node: NodeLocation) => void }) {
  const getColor = useCallback((quality: number, isActive: boolean): string => {
    if (!isActive) return '#888888';
    if (quality >= 90) return '#4CAF50';  // Green
    if (quality >= 70) return '#8BC34A';  // Light green
    if (quality >= 50) return '#FFC107';  // Yellow
    if (quality >= 30) return '#FF9800';  // Orange
    return '#F44336';  // Red
  }, []);
  
  const getRadius = useCallback((users: number, isGateway: boolean): number => {
    const base = isGateway ? 12 : 8;
    const bonus = Math.min(users / 10, 6);
    return base + bonus;
  }, []);
  
  return (
    <CircleMarker
      center={[node.latitude, node.longitude]}
      radius={getRadius(node.connectedUsers, node.isGateway)}
      pathOptions={{
        fillColor: getColor(node.qualityScore, node.isActive),
        fillOpacity: 0.8,
        color: node.isGateway ? '#2196F3' : '#333',
        weight: node.isGateway ? 3 : 1,
      }}
      eventHandlers={{
        click: () => onClick?.(node),
      }}
    >
      <Popup>
        <Box sx={{ minWidth: 200 }}>
          <Typography variant="subtitle2" fontWeight="bold">
            {node.isGateway ? '🌐 Gateway Node' : '📡 Relay Node'}
          </Typography>
          <Typography variant="caption" display="block">
            ID: {node.id.slice(0, 12)}...
          </Typography>
          <Box sx={{ mt: 1 }}>
            <Chip
              size="small"
              label={node.isActive ? 'Active' : 'Offline'}
              color={node.isActive ? 'success' : 'default'}
              sx={{ mr: 0.5 }}
            />
            <Chip
              size="small"
              label={`Quality: ${node.qualityScore}%`}
              color={node.qualityScore >= 70 ? 'success' : 'warning'}
            />
          </Box>
          <Typography variant="body2" sx={{ mt: 1 }}>
            👥 {node.connectedUsers} users connected
          </Typography>
          <Typography variant="body2">
            📊 {node.bandwidthMbps.toFixed(1)} Mbps
          </Typography>
          <Typography variant="caption" color="textSecondary">
            Last seen: {new Date(node.lastSeen).toLocaleString()}
          </Typography>
        </Box>
      </Popup>
    </CircleMarker>
  );
}

// ==================== Stats Panel ====================

function StatsPanel({ stats }: { stats: NetworkStats }) {
  return (
    <Paper
      sx={{
        position: 'absolute',
        top: 16,
        right: 16,
        zIndex: 1000,
        p: 2,
        minWidth: 200,
        background: 'rgba(255, 255, 255, 0.95)',
      }}
    >
      <Typography variant="h6" gutterBottom>
        🌍 Network Stats
      </Typography>
      <Box sx={{ display: 'grid', gap: 1 }}>
        <Box>
          <Typography variant="caption" color="textSecondary">
            Total Nodes
          </Typography>
          <Typography variant="h5">{stats.totalNodes.toLocaleString()}</Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="textSecondary">
            Active Nodes
          </Typography>
          <Typography variant="h5" color="success.main">
            {stats.activeNodes.toLocaleString()}
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="textSecondary">
            Connected Users
          </Typography>
          <Typography variant="h5">{stats.totalUsers.toLocaleString()}</Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="textSecondary">
            Network Bandwidth
          </Typography>
          <Typography variant="h5">{stats.totalBandwidthTbps.toFixed(2)} Tbps</Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="textSecondary">
            Coverage Area
          </Typography>
          <Typography variant="h5">{stats.coverageAreaKm2.toLocaleString()} km²</Typography>
        </Box>
      </Box>
    </Paper>
  );
}

// ==================== Filter Controls ====================

interface FilterState {
  showActive: boolean;
  showInactive: boolean;
  showGateways: boolean;
  minQuality: number;
}

function FilterPanel({
  filters,
  onChange,
}: {
  filters: FilterState;
  onChange: (filters: FilterState) => void;
}) {
  return (
    <Paper
      sx={{
        position: 'absolute',
        bottom: 16,
        left: 16,
        zIndex: 1000,
        p: 2,
        minWidth: 250,
        background: 'rgba(255, 255, 255, 0.95)',
      }}
    >
      <Typography variant="subtitle2" gutterBottom>
        🔍 Filters
      </Typography>
      <FormControlLabel
        control={
          <Switch
            checked={filters.showActive}
            onChange={(e) => onChange({ ...filters, showActive: e.target.checked })}
            size="small"
          />
        }
        label="Active Nodes"
      />
      <FormControlLabel
        control={
          <Switch
            checked={filters.showInactive}
            onChange={(e) => onChange({ ...filters, showInactive: e.target.checked })}
            size="small"
          />
        }
        label="Inactive Nodes"
      />
      <FormControlLabel
        control={
          <Switch
            checked={filters.showGateways}
            onChange={(e) => onChange({ ...filters, showGateways: e.target.checked })}
            size="small"
          />
        }
        label="Gateways Only"
      />
      <Box sx={{ mt: 2 }}>
        <Typography variant="caption">Min Quality: {filters.minQuality}%</Typography>
        <Slider
          value={filters.minQuality}
          onChange={(_, value) => onChange({ ...filters, minQuality: value as number })}
          min={0}
          max={100}
          size="small"
        />
      </Box>
    </Paper>
  );
}

// ==================== Legend ====================

function Legend() {
  const items = [
    { color: '#4CAF50', label: 'Excellent (90%+)' },
    { color: '#8BC34A', label: 'Good (70-90%)' },
    { color: '#FFC107', label: 'Fair (50-70%)' },
    { color: '#FF9800', label: 'Poor (30-50%)' },
    { color: '#F44336', label: 'Critical (<30%)' },
    { color: '#888888', label: 'Offline' },
  ];

  return (
    <Paper
      sx={{
        position: 'absolute',
        bottom: 16,
        right: 16,
        zIndex: 1000,
        p: 1.5,
        background: 'rgba(255, 255, 255, 0.95)',
      }}
    >
      <Typography variant="caption" fontWeight="bold" gutterBottom display="block">
        Quality Score
      </Typography>
      {items.map((item) => (
        <Box key={item.label} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
          <Box
            sx={{
              width: 12,
              height: 12,
              borderRadius: '50%',
              backgroundColor: item.color,
            }}
          />
          <Typography variant="caption">{item.label}</Typography>
        </Box>
      ))}
    </Paper>
  );
}

// ==================== Main Component ====================

export default function CoverageMap({
  nodes: initialNodes,
  stats,
  onNodeClick,
  refreshInterval = 30000,
}: CoverageMapProps) {
  const [nodes, setNodes] = useState<NodeLocation[]>(initialNodes);
  const [filters, setFilters] = useState<FilterState>({
    showActive: true,
    showInactive: true,
    showGateways: false,
    minQuality: 0,
  });

  // Refresh nodes periodically
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch('/api/v1/network/nodes');
        const data = await response.json();
        setNodes(data.nodes);
      } catch (error) {
        console.error('Failed to refresh nodes:', error);
      }
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [refreshInterval]);

  // Filter nodes
  const filteredNodes = useMemo(() => {
    return nodes.filter((node) => {
      if (filters.showGateways && !node.isGateway) return false;
      if (!filters.showActive && node.isActive) return false;
      if (!filters.showInactive && !node.isActive) return false;
      if (node.qualityScore < filters.minQuality) return false;
      return true;
    });
  }, [nodes, filters]);

  // Calculate center from nodes
  const center = useMemo((): [number, number] => {
    if (filteredNodes.length === 0) return [40.7128, -74.006]; // NYC default
    const avgLat = filteredNodes.reduce((sum, n) => sum + n.latitude, 0) / filteredNodes.length;
    const avgLng = filteredNodes.reduce((sum, n) => sum + n.longitude, 0) / filteredNodes.length;
    return [avgLat, avgLng];
  }, [filteredNodes]);

  return (
    <Box sx={{ position: 'relative', height: '100%', minHeight: 600 }}>
      <MapContainer
        center={center}
        zoom={4}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapUpdater center={center} zoom={4} />
        
        <MarkerClusterGroup
          chunkedLoading
          showCoverageOnHover={false}
          spiderfyOnMaxZoom={true}
        >
          {filteredNodes.map((node) => (
            <NodeMarker key={node.id} node={node} onClick={onNodeClick} />
          ))}
        </MarkerClusterGroup>
      </MapContainer>

      <StatsPanel stats={stats} />
      <FilterPanel filters={filters} onChange={setFilters} />
      <Legend />
    </Box>
  );
}
