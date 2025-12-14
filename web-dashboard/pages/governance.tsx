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
  Chip,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Avatar,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Divider,
  IconButton,
  Badge,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import HowToVoteIcon from '@mui/icons-material/HowToVote';
import AddIcon from '@mui/icons-material/Add';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import ThumbUpIcon from '@mui/icons-material/ThumbUp';
import ThumbDownIcon from '@mui/icons-material/ThumbDown';

// ==================== Types ====================

type ProposalState = 'pending' | 'active' | 'succeeded' | 'defeated' | 'executed' | 'canceled';
type ProposalType = 'parameter' | 'oracle' | 'emergency' | 'upgrade' | 'treasury';

interface Proposal {
  id: number;
  title: string;
  description: string;
  proposer: string;
  proposalType: ProposalType;
  state: ProposalState;
  forVotes: number;
  againstVotes: number;
  abstainVotes: number;
  startTime: Date;
  endTime: Date;
  executed: boolean;
}

interface GovernanceParams {
  votingDelay: number;
  votingPeriod: number;
  proposalThreshold: number;
  quorumVotes: number;
}

// ==================== Styled Components ====================

const ProposalCard = styled(Card)<{ state: ProposalState }>(({ theme, state }) => ({
  marginBottom: theme.spacing(2),
  borderLeft: `4px solid ${
    state === 'active'
      ? theme.palette.primary.main
      : state === 'succeeded'
      ? theme.palette.success.main
      : state === 'defeated'
      ? theme.palette.error.main
      : state === 'executed'
      ? theme.palette.success.dark
      : theme.palette.grey[400]
  }`,
}));

const VoteBar = styled(Box)(({ theme }) => ({
  display: 'flex',
  height: 8,
  borderRadius: 4,
  overflow: 'hidden',
  backgroundColor: theme.palette.grey[200],
}));

// ==================== Component ====================

export default function GovernancePage() {
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState(0);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [params, setParams] = useState<GovernanceParams | null>(null);
  const [votingPower, setVotingPower] = useState(0);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [voteDialogOpen, setVoteDialogOpen] = useState(false);
  const [selectedProposal, setSelectedProposal] = useState<Proposal | null>(null);
  const [newProposal, setNewProposal] = useState({ title: '', description: '', type: 'parameter' as ProposalType });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      // Mock data
      setProposals([
        {
          id: 5,
          title: 'Increase Base Reward Rate by 10%',
          description: 'This proposal suggests increasing the base reward rate from 0.000001 to 0.0000011 NWR per byte to incentivize more device participation.',
          proposer: '0x1234...5678',
          proposalType: 'parameter',
          state: 'active',
          forVotes: 125000,
          againstVotes: 45000,
          abstainVotes: 5000,
          startTime: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
          endTime: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000),
          executed: false,
        },
        {
          id: 4,
          title: 'Add Arbitrum Bridge Support',
          description: 'Enable cross-chain bridging to Arbitrum One for lower transaction fees.',
          proposer: '0xabcd...ef01',
          proposalType: 'upgrade',
          state: 'succeeded',
          forVotes: 200000,
          againstVotes: 30000,
          abstainVotes: 10000,
          startTime: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000),
          endTime: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000),
          executed: false,
        },
        {
          id: 3,
          title: 'Reduce Early Unstaking Penalty',
          description: 'Reduce early unstaking penalty from 10% to 5%.',
          proposer: '0x9876...5432',
          proposalType: 'parameter',
          state: 'defeated',
          forVotes: 50000,
          againstVotes: 150000,
          abstainVotes: 20000,
          startTime: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000),
          endTime: new Date(Date.now() - 8 * 24 * 60 * 60 * 1000),
          executed: false,
        },
      ]);
      setParams({
        votingDelay: 86400,
        votingPeriod: 604800,
        proposalThreshold: 10000,
        quorumVotes: 100000,
      });
      setVotingPower(25000);
    } catch (error) {
      console.error('Failed to fetch governance data:', error);
    }
    setLoading(false);
  };

  const getStateChip = (state: ProposalState) => {
    const colors: Record<ProposalState, 'default' | 'primary' | 'success' | 'error' | 'info' | 'warning'> = {
      pending: 'default',
      active: 'primary',
      succeeded: 'success',
      defeated: 'error',
      executed: 'success',
      canceled: 'warning',
    };
    return <Chip label={state.toUpperCase()} color={colors[state]} size="small" />;
  };

  const getTypeChip = (type: ProposalType) => {
    const labels: Record<ProposalType, string> = {
      parameter: '⚙️ Parameter',
      oracle: '🔮 Oracle',
      emergency: '🚨 Emergency',
      upgrade: '⬆️ Upgrade',
      treasury: '💰 Treasury',
    };
    return <Chip label={labels[type]} size="small" variant="outlined" />;
  };

  const calculateVotePercentage = (proposal: Proposal) => {
    const total = proposal.forVotes + proposal.againstVotes + proposal.abstainVotes;
    if (total === 0) return { for: 0, against: 0, abstain: 0 };
    return {
      for: (proposal.forVotes / total) * 100,
      against: (proposal.againstVotes / total) * 100,
      abstain: (proposal.abstainVotes / total) * 100,
    };
  };

  const getRemainingTime = (endTime: Date) => {
    const now = Date.now();
    const end = endTime.getTime();
    if (now >= end) return 'Ended';
    const hours = Math.floor((end - now) / (1000 * 60 * 60));
    const days = Math.floor(hours / 24);
    if (days > 0) return `${days}d ${hours % 24}h remaining`;
    return `${hours}h remaining`;
  };

  const handleVote = (proposal: Proposal) => {
    setSelectedProposal(proposal);
    setVoteDialogOpen(true);
  };

  const submitVote = async (support: number) => {
    // In production, call contract
    setVoteDialogOpen(false);
    await fetchData();
  };

  const createProposal = async () => {
    // In production, call contract
    setCreateDialogOpen(false);
    await fetchData();
  };

  const filteredProposals = proposals.filter((p) => {
    if (tab === 0) return true;
    if (tab === 1) return p.state === 'active';
    if (tab === 2) return ['succeeded', 'defeated', 'executed'].includes(p.state);
    return true;
  });

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress size={60} />
      </Box>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
        <Box>
          <Typography variant="h4" fontWeight="bold">
            🏛️ Governance
          </Typography>
          <Typography variant="body1" color="textSecondary">
            Participate in network governance by voting on proposals
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialogOpen(true)}
          disabled={votingPower < (params?.proposalThreshold || 10000)}
        >
          Create Proposal
        </Button>
      </Box>

      {/* Stats */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>Your Voting Power</Typography>
              <Typography variant="h5">{votingPower.toLocaleString()} NWR</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>Proposal Threshold</Typography>
              <Typography variant="h5">{params?.proposalThreshold.toLocaleString()} NWR</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>Quorum Required</Typography>
              <Typography variant="h5">{params?.quorumVotes.toLocaleString()} NWR</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>Voting Period</Typography>
              <Typography variant="h5">{(params?.votingPeriod || 0) / 86400} days</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs */}
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
        <Tab label={`All (${proposals.length})`} />
        <Tab label={`Active (${proposals.filter(p => p.state === 'active').length})`} />
        <Tab label="Completed" />
      </Tabs>

      {/* Proposals List */}
      {filteredProposals.length === 0 ? (
        <Alert severity="info">No proposals found</Alert>
      ) : (
        filteredProposals.map((proposal) => {
          const percentages = calculateVotePercentage(proposal);
          return (
            <ProposalCard key={proposal.id} state={proposal.state}>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
                  <Box>
                    <Box display="flex" gap={1} mb={1}>
                      {getStateChip(proposal.state)}
                      {getTypeChip(proposal.proposalType)}
                    </Box>
                    <Typography variant="h6">{proposal.title}</Typography>
                    <Typography variant="caption" color="textSecondary">
                      ID: {proposal.id} • by {proposal.proposer}
                    </Typography>
                  </Box>
                  {proposal.state === 'active' && (
                    <Button variant="contained" onClick={() => handleVote(proposal)}>
                      Vote
                    </Button>
                  )}
                </Box>

                <Typography variant="body2" color="textSecondary" mb={2}>
                  {proposal.description}
                </Typography>

                {/* Vote Bar */}
                <Box mb={1}>
                  <VoteBar>
                    <Box sx={{ width: `${percentages.for}%`, backgroundColor: '#4caf50' }} />
                    <Box sx={{ width: `${percentages.against}%`, backgroundColor: '#f44336' }} />
                    <Box sx={{ width: `${percentages.abstain}%`, backgroundColor: '#9e9e9e' }} />
                  </VoteBar>
                </Box>

                <Box display="flex" justifyContent="space-between">
                  <Typography variant="caption">
                    <ThumbUpIcon sx={{ fontSize: 14, mr: 0.5, color: 'success.main' }} />
                    For: {proposal.forVotes.toLocaleString()} ({percentages.for.toFixed(1)}%)
                  </Typography>
                  <Typography variant="caption">
                    <ThumbDownIcon sx={{ fontSize: 14, mr: 0.5, color: 'error.main' }} />
                    Against: {proposal.againstVotes.toLocaleString()} ({percentages.against.toFixed(1)}%)
                  </Typography>
                  <Typography variant="caption">
                    <AccessTimeIcon sx={{ fontSize: 14, mr: 0.5 }} />
                    {getRemainingTime(proposal.endTime)}
                  </Typography>
                </Box>
              </CardContent>
            </ProposalCard>
          );
        })
      )}

      {/* Vote Dialog */}
      <Dialog open={voteDialogOpen} onClose={() => setVoteDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Vote on Proposal #{selectedProposal?.id}</DialogTitle>
        <DialogContent>
          <Typography variant="h6" gutterBottom>{selectedProposal?.title}</Typography>
          <Typography variant="body2" color="textSecondary" mb={3}>
            {selectedProposal?.description}
          </Typography>
          <Alert severity="info" sx={{ mb: 2 }}>
            Your voting power: <strong>{votingPower.toLocaleString()} NWR</strong>
          </Alert>
        </DialogContent>
        <DialogActions sx={{ justifyContent: 'space-around', p: 2 }}>
          <Button variant="contained" color="success" onClick={() => submitVote(1)} size="large" startIcon={<ThumbUpIcon />}>
            For
          </Button>
          <Button variant="outlined" onClick={() => submitVote(2)} size="large">
            Abstain
          </Button>
          <Button variant="contained" color="error" onClick={() => submitVote(0)} size="large" startIcon={<ThumbDownIcon />}>
            Against
          </Button>
        </DialogActions>
      </Dialog>

      {/* Create Proposal Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create Proposal</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Title"
            value={newProposal.title}
            onChange={(e) => setNewProposal({ ...newProposal, title: e.target.value })}
            sx={{ mt: 2, mb: 2 }}
          />
          <TextField
            fullWidth
            label="Description"
            multiline
            rows={4}
            value={newProposal.description}
            onChange={(e) => setNewProposal({ ...newProposal, description: e.target.value })}
            sx={{ mb: 2 }}
          />
          <Alert severity="warning">
            Creating a proposal requires {params?.proposalThreshold.toLocaleString()} NWR voting power.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button onClick={createProposal} variant="contained" disabled={!newProposal.title || !newProposal.description}>
            Submit Proposal
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
