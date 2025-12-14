import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress,
  Stepper,
  Step,
  StepLabel,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import SwapHorizIcon from '@mui/icons-material/SwapHoriz';
import HistoryIcon from '@mui/icons-material/History';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';

// ==================== Types ====================

interface Chain {
  id: number;
  name: string;
  icon: string;
  enabled: boolean;
  minAmount: number;
  maxAmount: number;
  dailyRemaining: number;
  explorerUrl: string;
}

interface BridgeHistory {
  id: string;
  fromChain: number;
  toChain: number;
  amount: number;
  fee: number;
  status: 'pending' | 'completed' | 'failed';
  timestamp: Date;
  txHash: string;
}

// ==================== Styled Components ====================

const ChainCard = styled(Card)<{ selected?: boolean }>(({ theme, selected }) => ({
  cursor: 'pointer',
  border: selected ? `2px solid ${theme.palette.primary.main}` : '1px solid #e0e0e0',
  transition: 'all 0.2s ease',
  '&:hover': {
    borderColor: theme.palette.primary.light,
  },
}));

// ==================== Component ====================

export default function BridgePage() {
  const [loading, setLoading] = useState(true);
  const [chains, setChains] = useState<Chain[]>([]);
  const [fromChain, setFromChain] = useState<number>(1);
  const [toChain, setToChain] = useState<number>(137);
  const [amount, setAmount] = useState<string>('');
  const [recipient, setRecipient] = useState<string>('');
  const [useSameAddress, setUseSameAddress] = useState(true);
  const [history, setHistory] = useState<BridgeHistory[]>([]);
  const [activeStep, setActiveStep] = useState(0);
  const [bridgeInProgress, setBridgeInProgress] = useState(false);
  const [walletBalance, setWalletBalance] = useState(50000);
  const FEE_PERCENTAGE = 0.5;

  // Chain configurations
  const chainConfigs: Chain[] = [
    { id: 1, name: 'Ethereum', icon: '⟠', enabled: true, minAmount: 100, maxAmount: 1000000, dailyRemaining: 5000000, explorerUrl: 'https://etherscan.io' },
    { id: 137, name: 'Polygon', icon: '🟣', enabled: true, minAmount: 10, maxAmount: 1000000, dailyRemaining: 8000000, explorerUrl: 'https://polygonscan.com' },
    { id: 56, name: 'BNB Chain', icon: '🟡', enabled: true, minAmount: 10, maxAmount: 1000000, dailyRemaining: 7000000, explorerUrl: 'https://bscscan.com' },
    { id: 42161, name: 'Arbitrum', icon: '🔵', enabled: true, minAmount: 50, maxAmount: 1000000, dailyRemaining: 4000000, explorerUrl: 'https://arbiscan.io' },
    { id: 10, name: 'Optimism', icon: '🔴', enabled: false, minAmount: 50, maxAmount: 1000000, dailyRemaining: 0, explorerUrl: 'https://optimistic.etherscan.io' },
  ];

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      setChains(chainConfigs);
      setHistory([
        {
          id: 'br_001',
          fromChain: 1,
          toChain: 137,
          amount: 5000,
          fee: 25,
          status: 'completed',
          timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
          txHash: '0x1234...5678',
        },
        {
          id: 'br_002',
          fromChain: 137,
          toChain: 56,
          amount: 10000,
          fee: 50,
          status: 'pending',
          timestamp: new Date(Date.now() - 1 * 60 * 60 * 1000),
          txHash: '0xabcd...ef01',
        },
      ]);
    } catch (error) {
      console.error('Failed to fetch bridge data:', error);
    }
    setLoading(false);
  };

  const getChainName = (id: number) => chains.find(c => c.id === id)?.name || `Chain ${id}`;
  const getChainIcon = (id: number) => chains.find(c => c.id === id)?.icon || '🔗';

  const calculateFee = () => {
    const amountNum = parseFloat(amount) || 0;
    return amountNum * (FEE_PERCENTAGE / 100);
  };

  const calculateReceived = () => {
    const amountNum = parseFloat(amount) || 0;
    return amountNum - calculateFee();
  };

  const swapChains = () => {
    const temp = fromChain;
    setFromChain(toChain);
    setToChain(temp);
  };

  const validateBridge = () => {
    const amountNum = parseFloat(amount) || 0;
    const destChain = chains.find(c => c.id === toChain);
    
    if (amountNum <= 0) return 'Enter an amount';
    if (amountNum > walletBalance) return 'Insufficient balance';
    if (destChain && amountNum < destChain.minAmount) return `Minimum ${destChain.minAmount} NWR`;
    if (destChain && amountNum > destChain.maxAmount) return `Maximum ${destChain.maxAmount} NWR`;
    if (destChain && amountNum > destChain.dailyRemaining) return 'Exceeds daily limit';
    if (fromChain === toChain) return 'Select different chains';
    
    return null;
  };

  const handleBridge = async () => {
    setBridgeInProgress(true);
    setActiveStep(1);
    
    // Simulate bridge process
    await new Promise(resolve => setTimeout(resolve, 2000));
    setActiveStep(2);
    await new Promise(resolve => setTimeout(resolve, 2000));
    setActiveStep(3);
    
    setBridgeInProgress(false);
    await fetchData();
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress size={60} />
      </Box>
    );
  }

  const validationError = validateBridge();
  const destChain = chains.find(c => c.id === toChain);

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" fontWeight="bold" gutterBottom>
        🌉 Cross-Chain Bridge
      </Typography>
      <Typography variant="body1" color="textSecondary" mb={4}>
        Transfer NWR tokens between supported chains
      </Typography>

      <Grid container spacing={4}>
        {/* Bridge Form */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              {/* From Chain */}
              <Typography variant="overline" color="textSecondary">From</Typography>
              <FormControl fullWidth sx={{ mb: 3 }}>
                <Select
                  value={fromChain}
                  onChange={(e) => setFromChain(e.target.value as number)}
                >
                  {chains.filter(c => c.enabled).map(chain => (
                    <MenuItem key={chain.id} value={chain.id}>
                      {chain.icon} {chain.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {/* Swap Button */}
              <Box display="flex" justifyContent="center" my={1}>
                <IconButton onClick={swapChains} color="primary">
                  <SwapHorizIcon sx={{ transform: 'rotate(90deg)' }} />
                </IconButton>
              </Box>

              {/* To Chain */}
              <Typography variant="overline" color="textSecondary">To</Typography>
              <FormControl fullWidth sx={{ mb: 3 }}>
                <Select
                  value={toChain}
                  onChange={(e) => setToChain(e.target.value as number)}
                >
                  {chains.filter(c => c.enabled && c.id !== fromChain).map(chain => (
                    <MenuItem key={chain.id} value={chain.id}>
                      {chain.icon} {chain.name}
                      {chain.dailyRemaining < 1000000 && (
                        <Chip 
                          label={`${(chain.dailyRemaining / 1000000).toFixed(1)}M remaining`} 
                          size="small" 
                          sx={{ ml: 1 }} 
                        />
                      )}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {/* Amount */}
              <TextField
                fullWidth
                label="Amount"
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                sx={{ mb: 2 }}
                InputProps={{
                  endAdornment: <Typography color="textSecondary">NWR</Typography>,
                }}
                helperText={`Balance: ${walletBalance.toLocaleString()} NWR • Min: ${destChain?.minAmount || 0} NWR`}
              />

              {/* Fee Breakdown */}
              {parseFloat(amount) > 0 && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2">Bridge Fee ({FEE_PERCENTAGE}%)</Typography>
                    <Typography variant="body2">{calculateFee().toFixed(2)} NWR</Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between" mt={1}>
                    <Typography variant="body2" fontWeight="bold">You'll receive</Typography>
                    <Typography variant="body2" fontWeight="bold">{calculateReceived().toFixed(2)} NWR</Typography>
                  </Box>
                </Alert>
              )}

              {validationError && (
                <Alert severity="error" sx={{ mb: 2 }}>{validationError}</Alert>
              )}

              <Button
                variant="contained"
                fullWidth
                size="large"
                onClick={handleBridge}
                disabled={!!validationError || bridgeInProgress}
              >
                {bridgeInProgress ? <CircularProgress size={24} /> : 'Bridge Tokens'}
              </Button>

              {/* Progress Stepper */}
              {bridgeInProgress && (
                <Box mt={3}>
                  <Stepper activeStep={activeStep}>
                    <Step><StepLabel>Approve</StepLabel></Step>
                    <Step><StepLabel>Lock Tokens</StepLabel></Step>
                    <Step><StepLabel>Confirm</StepLabel></Step>
                  </Stepper>
                </Box>
              )}
            </CardContent>
          </Card>

          {/* Supported Chains */}
          <Typography variant="h6" sx={{ mt: 4, mb: 2 }}>Supported Chains</Typography>
          <Grid container spacing={2}>
            {chains.map(chain => (
              <Grid item xs={6} sm={4} key={chain.id}>
                <ChainCard>
                  <CardContent sx={{ textAlign: 'center', py: 2 }}>
                    <Typography variant="h4">{chain.icon}</Typography>
                    <Typography variant="body2">{chain.name}</Typography>
                    <Chip 
                      label={chain.enabled ? 'Active' : 'Coming Soon'} 
                      size="small" 
                      color={chain.enabled ? 'success' : 'default'}
                      sx={{ mt: 1 }}
                    />
                  </CardContent>
                </ChainCard>
              </Grid>
            ))}
          </Grid>
        </Grid>

        {/* History */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <HistoryIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Bridge History
              </Typography>

              {history.length === 0 ? (
                <Alert severity="info">No bridge history yet</Alert>
              ) : (
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Route</TableCell>
                        <TableCell align="right">Amount</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {history.map(tx => (
                        <TableRow key={tx.id}>
                          <TableCell>
                            <Typography variant="body2">
                              {getChainIcon(tx.fromChain)} → {getChainIcon(tx.toChain)}
                            </Typography>
                            <Typography variant="caption" color="textSecondary">
                              {tx.timestamp.toLocaleDateString()}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="body2">{tx.amount.toLocaleString()}</Typography>
                            <Typography variant="caption" color="textSecondary">
                              -{tx.fee} fee
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={tx.status}
                              size="small"
                              color={
                                tx.status === 'completed' ? 'success' :
                                tx.status === 'pending' ? 'warning' : 'error'
                              }
                            />
                          </TableCell>
                          <TableCell>
                            <Tooltip title="Copy TX Hash">
                              <IconButton size="small" onClick={() => copyToClipboard(tx.txHash)}>
                                <ContentCopyIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="View on Explorer">
                              <IconButton size="small">
                                <OpenInNewIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>

          {/* Info Card */}
          <Card sx={{ mt: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>ℹ️ Bridge Info</Typography>
              <Typography variant="body2" paragraph>
                <strong>Fee:</strong> {FEE_PERCENTAGE}% of transfer amount
              </Typography>
              <Typography variant="body2" paragraph>
                <strong>Time:</strong> ~5-30 minutes depending on network congestion
              </Typography>
              <Typography variant="body2" paragraph>
                <strong>Security:</strong> Multi-signature validation with 3/5 validators
              </Typography>
              <Typography variant="body2">
                <strong>Daily Limits:</strong> Up to 10M NWR per chain per day
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
}
