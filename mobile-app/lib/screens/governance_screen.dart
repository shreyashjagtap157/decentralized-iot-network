import 'package:flutter/material.dart';

/// Proposal state enum
enum ProposalState { pending, active, succeeded, defeated, executed, canceled }

/// Governance proposal
class Proposal {
  final int id;
  final String title;
  final String description;
  final String proposer;
  final ProposalState state;
  final double forVotes;
  final double againstVotes;
  final double abstainVotes;
  final DateTime endTime;

  Proposal({
    required this.id,
    required this.title,
    required this.description,
    required this.proposer,
    required this.state,
    required this.forVotes,
    required this.againstVotes,
    required this.abstainVotes,
    required this.endTime,
  });

  double get totalVotes => forVotes + againstVotes + abstainVotes;
  double get forPercentage => totalVotes > 0 ? (forVotes / totalVotes) * 100 : 0;
  double get againstPercentage => totalVotes > 0 ? (againstVotes / totalVotes) * 100 : 0;
}

class GovernanceScreen extends StatefulWidget {
  const GovernanceScreen({Key? key}) : super(key: key);

  @override
  State<GovernanceScreen> createState() => _GovernanceScreenState();
}

class _GovernanceScreenState extends State<GovernanceScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isLoading = true;
  List<Proposal> _proposals = [];
  double _votingPower = 0;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _loadData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    await Future.delayed(Duration(milliseconds: 500));
    setState(() {
      _votingPower = 25000;
      _proposals = [
        Proposal(
          id: 5,
          title: 'Increase Base Reward Rate by 10%',
          description: 'This proposal suggests increasing the base reward rate from 0.000001 to 0.0000011 NWR per byte.',
          proposer: '0x1234...5678',
          state: ProposalState.active,
          forVotes: 125000,
          againstVotes: 45000,
          abstainVotes: 5000,
          endTime: DateTime.now().add(Duration(days: 5)),
        ),
        Proposal(
          id: 4,
          title: 'Add Arbitrum Bridge Support',
          description: 'Enable cross-chain bridging to Arbitrum One for lower transaction fees.',
          proposer: '0xabcd...ef01',
          state: ProposalState.succeeded,
          forVotes: 200000,
          againstVotes: 30000,
          abstainVotes: 10000,
          endTime: DateTime.now().subtract(Duration(days: 3)),
        ),
        Proposal(
          id: 3,
          title: 'Reduce Early Unstaking Penalty',
          description: 'Reduce early unstaking penalty from 10% to 5%.',
          proposer: '0x9876...5432',
          state: ProposalState.defeated,
          forVotes: 50000,
          againstVotes: 150000,
          abstainVotes: 20000,
          endTime: DateTime.now().subtract(Duration(days: 8)),
        ),
      ];
      _isLoading = false;
    });
  }

  List<Proposal> _getFilteredProposals(int tabIndex) {
    switch (tabIndex) {
      case 1:
        return _proposals.where((p) => p.state == ProposalState.active).toList();
      case 2:
        return _proposals.where((p) => 
          p.state == ProposalState.succeeded || 
          p.state == ProposalState.defeated ||
          p.state == ProposalState.executed
        ).toList();
      default:
        return _proposals;
    }
  }

  Color _getStateColor(ProposalState state) {
    switch (state) {
      case ProposalState.active:
        return Colors.blue;
      case ProposalState.succeeded:
        return Colors.green;
      case ProposalState.defeated:
        return Colors.red;
      case ProposalState.executed:
        return Colors.green.shade800;
      case ProposalState.pending:
        return Colors.grey;
      case ProposalState.canceled:
        return Colors.orange;
    }
  }

  String _getRemainingTime(DateTime endTime) {
    final now = DateTime.now();
    if (now.isAfter(endTime)) return 'Ended';
    final diff = endTime.difference(now);
    if (diff.inDays > 0) return '${diff.inDays}d ${diff.inHours % 24}h left';
    return '${diff.inHours}h left';
  }

  Future<void> _showVoteDialog(Proposal proposal) async {
    final result = await showModalBottomSheet<int>(
      context: context,
      builder: (context) => Padding(
        padding: EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Vote on Proposal #${proposal.id}', style: Theme.of(context).textTheme.titleLarge),
            SizedBox(height: 8),
            Text(proposal.title, textAlign: TextAlign.center),
            SizedBox(height: 16),
            Text('Your voting power: ${_votingPower.toStringAsFixed(0)} NWR'),
            SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    onPressed: () => Navigator.pop(context, 1),
                    style: ElevatedButton.styleFrom(backgroundColor: Colors.green),
                    child: Padding(
                      padding: EdgeInsets.symmetric(vertical: 12),
                      child: Column(
                        children: [Icon(Icons.thumb_up), Text('For')],
                      ),
                    ),
                  ),
                ),
                SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => Navigator.pop(context, 2),
                    child: Padding(
                      padding: EdgeInsets.symmetric(vertical: 12),
                      child: Column(
                        children: [Icon(Icons.remove), Text('Abstain')],
                      ),
                    ),
                  ),
                ),
                SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton(
                    onPressed: () => Navigator.pop(context, 0),
                    style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
                    child: Padding(
                      padding: EdgeInsets.symmetric(vertical: 12),
                      child: Column(
                        children: [Icon(Icons.thumb_down), Text('Against')],
                      ),
                    ),
                  ),
                ),
              ],
            ),
            SizedBox(height: 16),
          ],
        ),
      ),
    );

    if (result != null) {
      final voteType = result == 1 ? 'For' : result == 0 ? 'Against' : 'Abstain';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Voted "$voteType" on proposal #${proposal.id}')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('🏛️ Governance'),
        bottom: TabBar(
          controller: _tabController,
          tabs: [
            Tab(text: 'All (${_proposals.length})'),
            Tab(text: 'Active (${_proposals.where((p) => p.state == ProposalState.active).length})'),
            Tab(text: 'Completed'),
          ],
        ),
      ),
      body: _isLoading
          ? Center(child: CircularProgressIndicator())
          : Column(
              children: [
                // Voting Power Card
                Container(
                  margin: EdgeInsets.all(16),
                  padding: EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [Colors.purple, Colors.deepPurple],
                    ),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Your Voting Power', style: TextStyle(color: Colors.white70)),
                          Text(
                            '${_votingPower.toStringAsFixed(0)} NWR',
                            style: TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                      Icon(Icons.how_to_vote, color: Colors.white54, size: 40),
                    ],
                  ),
                ),

                // Proposals List
                Expanded(
                  child: TabBarView(
                    controller: _tabController,
                    children: List.generate(3, (tabIndex) {
                      final proposals = _getFilteredProposals(tabIndex);
                      if (proposals.isEmpty) {
                        return Center(child: Text('No proposals found'));
                      }
                      return ListView.builder(
                        padding: EdgeInsets.symmetric(horizontal: 16),
                        itemCount: proposals.length,
                        itemBuilder: (context, index) => _buildProposalCard(proposals[index]),
                      );
                    }),
                  ),
                ),
              ],
            ),
    );
  }

  Widget _buildProposalCard(Proposal proposal) {
    return Card(
      margin: EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                Container(
                  padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: _getStateColor(proposal.state),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    proposal.state.name.toUpperCase(),
                    style: TextStyle(color: Colors.white, fontSize: 12),
                  ),
                ),
                Spacer(),
                Text('#${proposal.id}', style: TextStyle(color: Colors.grey)),
              ],
            ),
            SizedBox(height: 8),
            
            // Title
            Text(proposal.title, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            SizedBox(height: 4),
            Text(
              proposal.description,
              style: TextStyle(color: Colors.grey.shade600),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            SizedBox(height: 12),
            
            // Vote Bar
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: Row(
                children: [
                  Expanded(
                    flex: proposal.forPercentage.round().clamp(1, 100),
                    child: Container(height: 8, color: Colors.green),
                  ),
                  Expanded(
                    flex: proposal.againstPercentage.round().clamp(1, 100),
                    child: Container(height: 8, color: Colors.red),
                  ),
                ],
              ),
            ),
            SizedBox(height: 8),
            
            // Stats
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('👍 ${proposal.forPercentage.toStringAsFixed(1)}%', style: TextStyle(color: Colors.green)),
                Text('👎 ${proposal.againstPercentage.toStringAsFixed(1)}%', style: TextStyle(color: Colors.red)),
                Text('⏱️ ${_getRemainingTime(proposal.endTime)}', style: TextStyle(color: Colors.grey)),
              ],
            ),
            
            // Vote Button
            if (proposal.state == ProposalState.active) ...[
              SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () => _showVoteDialog(proposal),
                  child: Text('Vote'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
