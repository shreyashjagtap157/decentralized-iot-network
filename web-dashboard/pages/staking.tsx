import React, { useState, useEffect } from 'react';
import { api } from '../src/services/api';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  TextField,
  Slider,
  Chip,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  LinearProgress,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import LockIcon from '@mui/icons-material/Lock';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';

// ==================== Types ====================

interface StakingTier {
  id: number;
  name: string;
  minAmount: number;
  multiplier: number;
  minLockDays: number;
  color: string;
}

interface StakeInfo {
  amount: number;
  startTime: Date;
  lockDurationDays: number;
  multiplier: number;
  pendingRewards: number;
  tierName: string;
  canUnstakeWithoutPenalty: boolean;
}

interface StakingStats {
  totalStaked: number;
  rewardPool: number;
  totalStakers: number;
  apyEstimate: number;
}

// ==================== Styled Components ====================

const TierCard = styled(Card)<{ selected?: boolean; tierColor: string }>(
  ({ theme, selected, tierColor }) => ({
    cursor: 'pointer',
    border: selected ? `3px solid ${tierColor}` : '1px solid #e0e0e0',
    transition: 'all 0.3s ease',
    '&:hover': {
      transform: 'translateY(-4px)',
      boxShadow: theme.shadows[8],
    },
  })
);

const StatsCard = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  textAlign: 'center',
  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  color: 'white',
}));

// ==================== Component ====================

export default function StakingPage() {
  // State
  const [loading, setLoading] = useState(true);
  const [stakeAmount, setStakeAmount] = useState<number>(1000);
  const [lockDays, setLockDays] = useState<number>(30);
  const [selectedTier, setSelectedTier] = useState<number>(1);
  const [userStake, setUserStake] = useState<StakeInfo | null>(null);
  const [stats, setStats] = useState<StakingStats | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogAction, setDialogAction] = useState<'stake' | 'unstake' | 'claim'>('stake');
  const [walletBalance, setWalletBalance] = useState<number>(50000);

  // Tiers
  const tiers: StakingTier[] = [
    { id: 0, name: 'Bronze', minAmount: 1000, multiplier: 1.0, minLockDays: 7, color: '#CD7F32' },
    { id: 1, name: 'Silver', minAmount: 10000, multiplier: 1.25, minLockDays: 30, color: '#C0C0C0' },
    { id: 2, name: 'Gold', minAmount: 50000, multiplier: 1.5, minLockDays: 90, color: '#FFD700' },
    { id: 3, name: 'Platinum', minAmount: 100000, multiplier: 2.0, minLockDays: 180, color: '#E5E4E2' },
    { id: 4, name: 'Diamond', minAmount: 500000, multiplier: 3.0, minLockDays: 365, color: '#B9F2FF' },
  ];

  // Load data
  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      // Fetch real data from API
      // In a real app we would get the address from a wallet context
      const demoAddress = "0x1234567890123456789012345678901234567890"; 
      
      const [statsData, userData] = await Promise.all([
        api.getStakingStats(),
        api.getUserStake(demoAddress).catch(() => null) // Handle new users gracefully
      ]);

      if (statsData) {
        setStats({
          totalStaked: statsData.total_staked,
          rewardPool: statsData.reward_pool,
          totalStakers: statsData.total_stakers,
          apyEstimate: statsData.apy,
        });
      }

      if (userData) {
        setUserStake({
          amount: userData.amount,
          startTime: new Date(userData.start_time), // API returns ISO string
          lockDurationDays: userData.lock_days,
          multiplier: userData.multiplier,
          pendingRewards: userData.pending_rewards,
          tierName: userData.tier_name,
          canUnstakeWithoutPenalty: !userData.is_locked,
        });
      }
    } catch (error) {
      console.error('Failed to fetch staking data:', error);
      // Fallback to demo data if API fails (for demo purposes)
      setStats({
        totalStaked: 15000000,
        rewardPool: 500000,
        totalStakers: 1250,
        apyEstimate: 12.5,
      });
    }
    setLoading(false);
  };

  // Calculate estimated rewards
  const calculateEstimatedRewards = () => {
    const tier = tiers.find(t => t.id === selectedTier);
    if (!tier) return 0;
    const yearlyRate = stats?.apyEstimate || 12.5;
    const dailyRate = yearlyRate / 365;
    return stakeAmount * (dailyRate / 100) * lockDays * tier.multiplier;
  };

  // Get applicable tier
  const getApplicableTier = () => {
    for (let i = tiers.length - 1; i >= 0; i--) {
      if (stakeAmount >= tiers[i].minAmount && lockDays >= tiers[i].minLockDays) {
        return tiers[i];
      }
    }
    return tiers[0];
  };

  // Handle stake
  const handleStake = () => {
    setDialogAction('stake');
    setDialogOpen(true);
  };

  // Handle unstake
  const handleUnstake = () => {
    setDialogAction('unstake');
    setDialogOpen(true);
  };

  // Handle claim
  const handleClaim = () => {
    setDialogAction('claim');
    setDialogOpen(true);
  };

  // Confirm action
  const confirmAction = async () => {
    // In production, call contract via Web3
    setDialogOpen(false);
    await fetchData();
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress size={60} />
      </Box>
    );
  }

  const applicableTier = getApplicableTier();

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" fontWeight="bold" gutterBottom>
        💎 NWR Staking
      </Typography>
      <Typography variant="body1" color="textSecondary" mb={4}>
        Stake your NWR tokens to earn rewards and boost your device earnings
      </Typography>

      {/* Stats Cards */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard>
            <Typography variant="overline">Total Staked</Typography>
            <Typography variant="h4">{stats?.totalStaked.toLocaleString()}</Typography>
            <Typography variant="caption">NWR</Typography>
          </StatsCard>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard>
            <Typography variant="overline">Reward Pool</Typography>
            <Typography variant="h4">{stats?.rewardPool.toLocaleString()}</Typography>
            <Typography variant="caption">NWR</Typography>
          </StatsCard>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard>
            <Typography variant="overline">Total Stakers</Typography>
            <Typography variant="h4">{stats?.totalStakers.toLocaleString()}</Typography>
            <Typography variant="caption">Users</Typography>
          </StatsCard>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard>
            <Typography variant="overline">Est. APY</Typography>
            <Typography variant="h4">{stats?.apyEstimate}%</Typography>
            <Typography variant="caption">Base Rate</Typography>
          </StatsCard>
        </Grid>
      </Grid>

      <Grid container spacing={4}>
        {/* Left - Stake Form */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <LockIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Stake Tokens
              </Typography>

              {/* Amount Input */}
              <TextField
                fullWidth
                label="Stake Amount"
                type="number"
                value={stakeAmount}
                onChange={(e) => setStakeAmount(Number(e.target.value))}
                sx={{ mb: 3 }}
                InputProps={{
                  endAdornment: <Typography color="textSecondary">NWR</Typography>,
                }}
                helperText={`Balance: ${walletBalance.toLocaleString()} NWR`}
              />

              {/* Lock Duration Slider */}
              <Typography gutterBottom>Lock Duration: {lockDays} days</Typography>
              <Slider
                value={lockDays}
                onChange={(_, value) => setLockDays(value as number)}
                min={7}
                max={365}
                marks={[
                  { value: 7, label: '7d' },
                  { value: 30, label: '30d' },
                  { value: 90, label: '90d' },
                  { value: 180, label: '180d' },
                  { value: 365, label: '1y' },
                ]}
                sx={{ mb: 3 }}
              />

              {/* Selected Tier */}
              <Alert severity="info" sx={{ mb: 3 }}>
                <Typography>
                  <strong>Your Tier:</strong> {applicableTier.name} ({applicableTier.multiplier}x multiplier)
                </Typography>
                <Typography variant="body2">
                  Estimated rewards: ~{calculateEstimatedRewards().toFixed(2)} NWR
                </Typography>
              </Alert>

              <Button
                variant="contained"
                fullWidth
                size="large"
                onClick={handleStake}
                disabled={stakeAmount <= 0 || stakeAmount > walletBalance}
              >
                Stake {stakeAmount.toLocaleString()} NWR
              </Button>
            </CardContent>
          </Card>

          {/* Tiers */}
          <Typography variant="h6" sx={{ mt: 4, mb: 2 }}>
            Staking Tiers
          </Typography>
          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Tier</TableCell>
                  <TableCell align="right">Min Stake</TableCell>
                  <TableCell align="right">Min Lock</TableCell>
                  <TableCell align="right">Multiplier</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {tiers.map((tier) => (
                  <TableRow
                    key={tier.id}
                    sx={{
                      backgroundColor:
                        applicableTier.id === tier.id ? `${tier.color}20` : 'inherit',
                    }}
                  >
                    <TableCell>
                      <Chip
                        label={tier.name}
                        size="small"
                        sx={{ backgroundColor: tier.color }}
                      />
                    </TableCell>
                    <TableCell align="right">{tier.minAmount.toLocaleString()}</TableCell>
                    <TableCell align="right">{tier.minLockDays}d</TableCell>
                    <TableCell align="right">{tier.multiplier}x</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Grid>

        {/* Right - Current Stake */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <AccountBalanceWalletIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Your Stake
              </Typography>

              {userStake ? (
                <>
                  <Box sx={{ mb: 3 }}>
                    <Typography variant="h3" color="primary">
                      {userStake.amount.toLocaleString()} NWR
                    </Typography>
                    <Chip
                      label={userStake.tierName}
                      color="primary"
                      sx={{ mt: 1 }}
                    />
                  </Box>

                  <Grid container spacing={2} sx={{ mb: 3 }}>
                    <Grid item xs={6}>
                      <Typography variant="overline" color="textSecondary">
                        Lock Duration
                      </Typography>
                      <Typography variant="h6">
                        {userStake.lockDurationDays} days
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="overline" color="textSecondary">
                        Multiplier
                      </Typography>
                      <Typography variant="h6">{userStake.multiplier}x</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="overline" color="textSecondary">
                        Pending Rewards
                      </Typography>
                      <Typography variant="h6" color="success.main">
                        {userStake.pendingRewards.toFixed(2)} NWR
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="overline" color="textSecondary">
                        Staked Since
                      </Typography>
                      <Typography variant="h6">
                        {userStake.startTime.toLocaleDateString()}
                      </Typography>
                    </Grid>
                  </Grid>

                  {!userStake.canUnstakeWithoutPenalty && (
                    <Alert severity="warning" sx={{ mb: 2 }}>
                      Early unstaking will incur a 10% penalty
                    </Alert>
                  )}

                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <Button
                      variant="contained"
                      color="success"
                      onClick={handleClaim}
                      disabled={userStake.pendingRewards <= 0}
                    >
                      Claim Rewards
                    </Button>
                    <Button variant="outlined" color="error" onClick={handleUnstake}>
                      Unstake
                    </Button>
                  </Box>
                </>
              ) : (
                <Alert severity="info">
                  You don't have any staked tokens. Stake now to earn rewards!
                </Alert>
              )}
            </CardContent>
          </Card>

          {/* FAQ */}
          <Card sx={{ mt: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                ❓ FAQ
              </Typography>
              <Typography variant="body2" paragraph>
                <strong>How are rewards calculated?</strong>
                <br />
                Rewards = Staked Amount × Daily Rate × Days × Tier Multiplier
              </Typography>
              <Typography variant="body2" paragraph>
                <strong>Can I unstake early?</strong>
                <br />
                Yes, but you'll pay a 10% penalty. After lock period, no penalty.
              </Typography>
              <Typography variant="body2">
                <strong>When can I claim rewards?</strong>
                <br />
                Rewards accumulate in real-time and can be claimed anytime.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Confirmation Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>
          {dialogAction === 'stake' && 'Confirm Stake'}
          {dialogAction === 'unstake' && 'Confirm Unstake'}
          {dialogAction === 'claim' && 'Claim Rewards'}
        </DialogTitle>
        <DialogContent>
          {dialogAction === 'stake' && (
            <Typography>
              You are about to stake <strong>{stakeAmount.toLocaleString()} NWR</strong> for{' '}
              <strong>{lockDays} days</strong>. You will earn {applicableTier.multiplier}x rewards.
            </Typography>
          )}
          {dialogAction === 'unstake' && (
            <Typography>
              {userStake?.canUnstakeWithoutPenalty
                ? 'Your stake is fully unlocked. No penalty will be applied.'
                : 'Early unstaking will result in a 10% penalty.'}
            </Typography>
          )}
          {dialogAction === 'claim' && (
            <Typography>
              You are claiming <strong>{userStake?.pendingRewards.toFixed(2)} NWR</strong> in rewards.
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button onClick={confirmAction} variant="contained" color="primary">
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
