'use client';

import React, { useState, useEffect, useCallback } from 'react';

// Types for all project metrics
interface AISystemMetrics {
  status: 'online' | 'offline' | 'degraded';
  activeConversations: number;
  tokensProcessed: number;
  toolExecutions: number;
  averageLatency: number;
  modelProvider: string;
  uptime: number;
}

interface StockPredictorMetrics {
  status: 'online' | 'offline' | 'training';
  activePredictions: number;
  accuracy7Day: number;
  accuracy30Day: number;
  portfolioValue: number;
  portfolioChange: number;
  sentiment: 'bullish' | 'bearish' | 'neutral';
  ensembleModels: number;
}

interface MinerMetrics {
  status: 'mining' | 'paused' | 'offline';
  hashRate: number;
  hashRateUnit: string;
  validShares: number;
  invalidShares: number;
  currentDifficulty: number;
  estimatedEarnings: number;
  thermalState: 'normal' | 'warm' | 'throttled';
  batteryLevel: number;
  miningIntensity: number;
}

interface IoTNetworkMetrics {
  status: 'online' | 'offline' | 'partial';
  connectedDevices: number;
  activeNodes: number;
  dataPointsToday: number;
  anomaliesDetected: number;
  meshPeers: number;
  pendingRewards: number;
  networkLatency: number;
}

interface UnifiedDashboardProps {
  refreshInterval?: number; // ms
}

const StatusIndicator: React.FC<{ status: string }> = ({ status }) => {
  const getStatusColor = () => {
    switch (status) {
      case 'online':
      case 'mining':
        return 'bg-green-500';
      case 'offline':
        return 'bg-red-500';
      case 'degraded':
      case 'partial':
      case 'paused':
      case 'training':
      case 'warm':
        return 'bg-yellow-500';
      case 'throttled':
        return 'bg-orange-500';
      default:
        return 'bg-gray-500';
    }
  };

  return (
    <span className="flex items-center gap-2">
      <span className={`w-3 h-3 rounded-full ${getStatusColor()} animate-pulse`} />
      <span className="capitalize text-sm font-medium">{status}</span>
    </span>
  );
};

const MetricCard: React.FC<{
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
  icon?: React.ReactNode;
}> = ({ title, value, subtitle, trend, icon }) => {
  const getTrendIcon = () => {
    switch (trend) {
      case 'up':
        return <span className="text-green-500">↑</span>;
      case 'down':
        return <span className="text-red-500">↓</span>;
      default:
        return null;
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      <div className="flex items-center justify-between mb-2">
        <span className="text-gray-400 text-sm">{title}</span>
        {icon}
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-bold text-white">{value}</span>
        {getTrendIcon()}
      </div>
      {subtitle && (
        <span className="text-gray-500 text-xs mt-1 block">{subtitle}</span>
      )}
    </div>
  );
};

const ProjectCard: React.FC<{
  title: string;
  status: string;
  children: React.ReactNode;
  color: string;
}> = ({ title, status, children, color }) => {
  return (
    <div className={`bg-gray-900 rounded-xl border-l-4 ${color} overflow-hidden`}>
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">{title}</h3>
          <StatusIndicator status={status} />
        </div>
      </div>
      <div className="p-4 grid grid-cols-2 md:grid-cols-3 gap-4">
        {children}
      </div>
    </div>
  );
};

const AISystemPanel: React.FC<{ metrics: AISystemMetrics }> = ({ metrics }) => {
  return (
    <ProjectCard title="AI-OS System" status={metrics.status} color="border-purple-500">
      <MetricCard
        title="Active Conversations"
        value={metrics.activeConversations}
        subtitle="Current sessions"
      />
      <MetricCard
        title="Tokens Processed"
        value={`${(metrics.tokensProcessed / 1000000).toFixed(2)}M`}
        subtitle="Total processed"
      />
      <MetricCard
        title="Tool Executions"
        value={metrics.toolExecutions}
        subtitle="Commands run"
      />
      <MetricCard
        title="Avg Latency"
        value={`${metrics.averageLatency.toFixed(0)}ms`}
        trend={metrics.averageLatency < 500 ? 'up' : 'down'}
      />
      <MetricCard
        title="Provider"
        value={metrics.modelProvider}
        subtitle="Active model"
      />
      <MetricCard
        title="Uptime"
        value={`${(metrics.uptime / 3600).toFixed(1)}h`}
        subtitle="Session duration"
      />
    </ProjectCard>
  );
};

const StockPredictorPanel: React.FC<{ metrics: StockPredictorMetrics }> = ({ metrics }) => {
  return (
    <ProjectCard title="Stock AI Predictor" status={metrics.status} color="border-blue-500">
      <MetricCard
        title="7-Day Accuracy"
        value={`${(metrics.accuracy7Day * 100).toFixed(1)}%`}
        trend={metrics.accuracy7Day > 0.6 ? 'up' : 'down'}
      />
      <MetricCard
        title="30-Day Accuracy"
        value={`${(metrics.accuracy30Day * 100).toFixed(1)}%`}
        trend={metrics.accuracy30Day > 0.55 ? 'up' : 'down'}
      />
      <MetricCard
        title="Portfolio Value"
        value={`$${metrics.portfolioValue.toLocaleString()}`}
        trend={metrics.portfolioChange > 0 ? 'up' : 'down'}
        subtitle={`${metrics.portfolioChange > 0 ? '+' : ''}${(metrics.portfolioChange * 100).toFixed(2)}%`}
      />
      <MetricCard
        title="Active Predictions"
        value={metrics.activePredictions}
        subtitle="Open positions"
      />
      <MetricCard
        title="Market Sentiment"
        value={metrics.sentiment.toUpperCase()}
        subtitle="AI analysis"
      />
      <MetricCard
        title="Ensemble Models"
        value={metrics.ensembleModels}
        subtitle="LSTM, GRU, Attention"
      />
    </ProjectCard>
  );
};

const MinerPanel: React.FC<{ metrics: MinerMetrics }> = ({ metrics }) => {
  const getHashRateDisplay = () => {
    if (metrics.hashRate >= 1000000000) {
      return `${(metrics.hashRate / 1000000000).toFixed(2)} GH/s`;
    } else if (metrics.hashRate >= 1000000) {
      return `${(metrics.hashRate / 1000000).toFixed(2)} MH/s`;
    } else if (metrics.hashRate >= 1000) {
      return `${(metrics.hashRate / 1000).toFixed(2)} KH/s`;
    }
    return `${metrics.hashRate.toFixed(2)} H/s`;
  };

  return (
    <ProjectCard title="Crypto Miner" status={metrics.status} color="border-yellow-500">
      <MetricCard
        title="Hash Rate"
        value={getHashRateDisplay()}
        trend={metrics.status === 'mining' ? 'up' : 'neutral'}
      />
      <MetricCard
        title="Valid Shares"
        value={metrics.validShares.toLocaleString()}
        subtitle={`${((metrics.validShares / (metrics.validShares + metrics.invalidShares + 1)) * 100).toFixed(1)}% accept rate`}
      />
      <MetricCard
        title="Difficulty"
        value={metrics.currentDifficulty.toExponential(2)}
        subtitle="Current target"
      />
      <MetricCard
        title="Est. Earnings"
        value={`$${metrics.estimatedEarnings.toFixed(4)}`}
        subtitle="Per day"
      />
      <MetricCard
        title="Thermal State"
        value={metrics.thermalState.toUpperCase()}
        subtitle={`Battery: ${metrics.batteryLevel}%`}
      />
      <MetricCard
        title="Mining Intensity"
        value={`${(metrics.miningIntensity * 100).toFixed(0)}%`}
        subtitle="Adaptive scheduler"
      />
    </ProjectCard>
  );
};

const IoTNetworkPanel: React.FC<{ metrics: IoTNetworkMetrics }> = ({ metrics }) => {
  return (
    <ProjectCard title="IoT Network" status={metrics.status} color="border-green-500">
      <MetricCard
        title="Connected Devices"
        value={metrics.connectedDevices}
        trend="up"
      />
      <MetricCard
        title="Active Nodes"
        value={metrics.activeNodes}
        subtitle="Mesh network"
      />
      <MetricCard
        title="Data Points"
        value={`${(metrics.dataPointsToday / 1000).toFixed(1)}K`}
        subtitle="Today"
      />
      <MetricCard
        title="Anomalies"
        value={metrics.anomaliesDetected}
        trend={metrics.anomaliesDetected > 10 ? 'down' : 'up'}
        subtitle="ML detected"
      />
      <MetricCard
        title="Mesh Peers"
        value={metrics.meshPeers}
        subtitle="P2P connections"
      />
      <MetricCard
        title="Pending Rewards"
        value={`${metrics.pendingRewards.toFixed(4)} ETH`}
        subtitle="Claimable"
      />
    </ProjectCard>
  );
};

const SystemHealthBar: React.FC<{
  aiHealth: number;
  stockHealth: number;
  minerHealth: number;
  iotHealth: number;
}> = ({ aiHealth, stockHealth, minerHealth, iotHealth }) => {
  const overall = (aiHealth + stockHealth + minerHealth + iotHealth) / 4;

  return (
    <div className="bg-gray-900 rounded-xl p-4 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">System Health Overview</h2>
        <span className={`text-2xl font-bold ${overall > 80 ? 'text-green-500' : overall > 50 ? 'text-yellow-500' : 'text-red-500'}`}>
          {overall.toFixed(0)}%
        </span>
      </div>
      <div className="grid grid-cols-4 gap-4">
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-400">AI-OS</span>
            <span className="text-purple-400">{aiHealth}%</span>
          </div>
          <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
            <div className="h-full bg-purple-500 transition-all duration-500" style={{ width: `${aiHealth}%` }} />
          </div>
        </div>
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-400">Stock AI</span>
            <span className="text-blue-400">{stockHealth}%</span>
          </div>
          <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
            <div className="h-full bg-blue-500 transition-all duration-500" style={{ width: `${stockHealth}%` }} />
          </div>
        </div>
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-400">Miner</span>
            <span className="text-yellow-400">{minerHealth}%</span>
          </div>
          <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
            <div className="h-full bg-yellow-500 transition-all duration-500" style={{ width: `${minerHealth}%` }} />
          </div>
        </div>
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-400">IoT Network</span>
            <span className="text-green-400">{iotHealth}%</span>
          </div>
          <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
            <div className="h-full bg-green-500 transition-all duration-500" style={{ width: `${iotHealth}%` }} />
          </div>
        </div>
      </div>
    </div>
  );
};

export const UnifiedDashboard: React.FC<UnifiedDashboardProps> = ({
  refreshInterval = 5000,
}) => {
  const [aiMetrics, setAIMetrics] = useState<AISystemMetrics>({
    status: 'online',
    activeConversations: 12,
    tokensProcessed: 45678900,
    toolExecutions: 234,
    averageLatency: 345,
    modelProvider: 'Claude 3.5',
    uptime: 14400,
  });

  const [stockMetrics, setStockMetrics] = useState<StockPredictorMetrics>({
    status: 'online',
    activePredictions: 8,
    accuracy7Day: 0.67,
    accuracy30Day: 0.58,
    portfolioValue: 125430,
    portfolioChange: 0.0234,
    sentiment: 'bullish',
    ensembleModels: 3,
  });

  const [minerMetrics, setMinerMetrics] = useState<MinerMetrics>({
    status: 'mining',
    hashRate: 45600,
    hashRateUnit: 'KH/s',
    validShares: 1234,
    invalidShares: 12,
    currentDifficulty: 2.5e12,
    estimatedEarnings: 0.0012,
    thermalState: 'normal',
    batteryLevel: 78,
    miningIntensity: 0.65,
  });

  const [iotMetrics, setIoTMetrics] = useState<IoTNetworkMetrics>({
    status: 'online',
    connectedDevices: 156,
    activeNodes: 23,
    dataPointsToday: 45600,
    anomaliesDetected: 3,
    meshPeers: 12,
    pendingRewards: 0.0456,
    networkLatency: 45,
  });

  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  // Simulate real-time updates (in production, this would fetch from APIs)
  const fetchMetrics = useCallback(async () => {
    try {
      // AI-OS metrics
      // const aiResponse = await fetch('/api/ai-os/metrics');
      // setAIMetrics(await aiResponse.json());

      // Stock predictor metrics
      // const stockResponse = await fetch('/api/stock-predictor/metrics');
      // setStockMetrics(await stockResponse.json());

      // Miner metrics
      // const minerResponse = await fetch('/api/miner/metrics');
      // setMinerMetrics(await minerResponse.json());

      // IoT metrics
      // const iotResponse = await fetch('/api/iot/metrics');
      // setIoTMetrics(await iotResponse.json());

      // Simulate data changes for demo
      setMinerMetrics(prev => ({
        ...prev,
        hashRate: prev.hashRate + (Math.random() - 0.5) * 1000,
        validShares: prev.validShares + Math.floor(Math.random() * 2),
      }));

      setIoTMetrics(prev => ({
        ...prev,
        dataPointsToday: prev.dataPointsToday + Math.floor(Math.random() * 100),
      }));

      setLastUpdated(new Date());
    } catch (error) {
      console.error('Error fetching metrics:', error);
    }
  }, []);

  useEffect(() => {
    const interval = setInterval(fetchMetrics, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchMetrics, refreshInterval]);

  // Calculate health scores
  const calculateHealth = useCallback((metrics: any, type: string): number => {
    switch (type) {
      case 'ai':
        return metrics.status === 'online' ? 100 : metrics.status === 'degraded' ? 60 : 0;
      case 'stock':
        return Math.min(100, metrics.accuracy7Day * 100 + 30);
      case 'miner':
        const shareRate = metrics.validShares / (metrics.validShares + metrics.invalidShares + 1);
        return shareRate * 100 * (metrics.status === 'mining' ? 1 : 0.5);
      case 'iot':
        return Math.min(100, (1 - metrics.anomaliesDetected / 100) * 100);
      default:
        return 0;
    }
  }, []);

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold">Project Command Center</h1>
            <p className="text-gray-400">Unified monitoring for all systems</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-500">Last updated</p>
            <p className="text-lg font-mono">{lastUpdated.toLocaleTimeString()}</p>
          </div>
        </div>

        {/* Health Overview */}
        <SystemHealthBar
          aiHealth={calculateHealth(aiMetrics, 'ai')}
          stockHealth={calculateHealth(stockMetrics, 'stock')}
          minerHealth={calculateHealth(minerMetrics, 'miner')}
          iotHealth={calculateHealth(iotMetrics, 'iot')}
        />

        {/* Project Panels */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <AISystemPanel metrics={aiMetrics} />
          <StockPredictorPanel metrics={stockMetrics} />
          <MinerPanel metrics={minerMetrics} />
          <IoTNetworkPanel metrics={iotMetrics} />
        </div>

        {/* Footer */}
        <div className="mt-6 text-center text-gray-500 text-sm">
          <p>Refreshing every {refreshInterval / 1000} seconds</p>
        </div>
      </div>
    </div>
  );
};

export default UnifiedDashboard;
