import React, { useState, useEffect } from 'react';
import { Container, Box, Typography, Paper, Button, Alert, Card, CardContent, Grid, Chip, CircularProgress } from '@mui/material';
import { AccountBalanceWallet as WalletIcon, Refresh as RefreshIcon, ExitToApp as WithdrawIcon } from '@mui/icons-material';
import { web3Service } from '../lib/web3';
import { useAuth } from '../contexts/AuthContext';

const WalletPage: React.FC = () => {
  const { user } = useAuth();
  const [account, setAccount] = useState<string | null>(null);
  const [balance, setBalance] = useState<string>('0');
  const [earnings, setEarnings] = useState<string>('0');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const connectWallet = async () => {
    setLoading(true);
    setError(null);
    try {
      const acc = await web3Service.connectWallet();
      if (acc) {
        setAccount(acc);
        await refreshData(acc);
      } else {
        setError("Please install MetaMask or another Web3 wallet.");
      }
    } catch (err: any) {
      setError(err.message || "Failed to connect wallet");
    } finally {
      setLoading(false);
    }
  };

  const refreshData = async (acc: string) => {
    try {
        const bal = await web3Service.getBalance();
        setBalance(bal);
        
        // Fetch contract earnings
        const earn = await web3Service.getUserEarnings(acc);
        setEarnings(earn);
    } catch (err) {
        console.error("Failed to refresh data", err);
    }
  };

  const handleWithdraw = async () => {
      setLoading(true);
      setError(null);
      setSuccess(null);
      try {
          await web3Service.withdrawEarnings();
          setSuccess("Withdrawal transaction submitted successfully!");
          if (account) await refreshData(account);
      } catch (err: any) {
          setError(err.message || "Withdrawal failed");
      } finally {
          setLoading(false);
      }
  };

  useEffect(() => {
      // Check if already connected
      if (web3Service.isConnected()) {
          const acc = web3Service.getAccount();
          if (acc) {
              setAccount(acc);
              refreshData(acc);
          }
      }
  }, []);

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
       <Box sx={{ 
        p: 3,
        mb: 4,
        borderRadius: 3,
        background: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
        color: 'white',
        boxShadow: '0 10px 40px rgba(56, 239, 125, 0.3)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <Box display="flex" alignItems="center" gap={2}>
            <WalletIcon fontSize="large" />
            <Box>
                <Typography variant="h4" fontWeight="bold">My Wallet</Typography>
                <Typography variant="body1" sx={{ opacity: 0.9 }}>Manage your earnings and rewards</Typography>
            </Box>
        </Box>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess(null)}>{success}</Alert>}

      {!account ? (
        <Paper sx={{ p: 6, textAlign: 'center', borderRadius: 3 }}>
             <Typography variant="h5" gutterBottom>Connect your Web3 Wallet</Typography>
             <Typography color="textSecondary" sx={{ mb: 4 }}>
                 Connect your MetaMask wallet to view your balance and claim network rewards.
             </Typography>
             <Button 
                variant="contained" 
                size="large" 
                onClick={connectWallet} 
                disabled={loading}
                sx={{ bgcolor: '#11998e', py: 1.5, px: 4 }}
            >
                 {loading ? <CircularProgress size={24} color="inherit" /> : 'Connect Wallet'}
             </Button>
        </Paper>
      ) : (
        <Grid container spacing={3}>
            <Grid item xs={12}>
                <Paper sx={{ p: 3, borderRadius: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box>
                        <Typography variant="overline" color="textSecondary">Connected Account</Typography>
                        <Typography variant="h6" sx={{ wordBreak: 'break-all', fontFamily: 'monospace' }}>
                            {account}
                        </Typography>
                    </Box>
                    <Chip label="Connected" color="success" variant="outlined" />
                </Paper>
            </Grid>

            <Grid item xs={12} md={6}>
                 <Card sx={{ borderRadius: 3, height: '100%' }}>
                     <CardContent>
                         <Typography color="textSecondary" gutterBottom>ETH Balance</Typography>
                         <Typography variant="h3" sx={{ color: '#11998e', fontWeight: 'bold' }}>
                             {parseFloat(balance).toFixed(4)} <Typography component="span" variant="h6" color="textSecondary">ETH</Typography>
                         </Typography>
                     </CardContent>
                 </Card>
            </Grid>

            <Grid item xs={12} md={6}>
                 <Card sx={{ borderRadius: 3, height: '100%' }}>
                     <CardContent>
                         <Typography color="textSecondary" gutterBottom>Pending Rewards</Typography>
                         <Typography variant="h3" sx={{ color: '#ff9800', fontWeight: 'bold' }}>
                             {parseFloat(earnings).toFixed(4)} <Typography component="span" variant="h6" color="textSecondary">NWR</Typography>
                         </Typography>
                         <Box sx={{ mt: 2 }}>
                            <Button 
                                variant="contained" 
                                color="warning" 
                                fullWidth 
                                onClick={handleWithdraw}
                                disabled={loading || parseFloat(earnings) <= 0}
                                startIcon={<WithdrawIcon />}
                            >
                                Claim Rewards
                            </Button>
                         </Box>
                     </CardContent>
                 </Card>
            </Grid>
        </Grid>
      )}
    </Container>
  );
};

export default WalletPage;
