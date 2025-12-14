import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

/// Staking tier information
class StakingTier {
  final int id;
  final String name;
  final double minAmount;
  final double multiplier;
  final int minLockDays;
  final Color color;

  const StakingTier({
    required this.id,
    required this.name,
    required this.minAmount,
    required this.multiplier,
    required this.minLockDays,
    required this.color,
  });
}

/// User's stake information
class StakeInfo {
  final double amount;
  final DateTime startTime;
  final int lockDurationDays;
  final double multiplier;
  final double pendingRewards;
  final String tierName;
  final bool canUnstakeWithoutPenalty;

  StakeInfo({
    required this.amount,
    required this.startTime,
    required this.lockDurationDays,
    required this.multiplier,
    required this.pendingRewards,
    required this.tierName,
    required this.canUnstakeWithoutPenalty,
  });
}

class StakingScreen extends StatefulWidget {
  const StakingScreen({Key? key}) : super(key: key);

  @override
  State<StakingScreen> createState() => _StakingScreenState();
}

class _StakingScreenState extends State<StakingScreen> {
  bool _isLoading = true;
  double _stakeAmount = 1000;
  int _lockDays = 30;
  double _walletBalance = 50000;
  StakeInfo? _userStake;

  final List<StakingTier> _tiers = [
    StakingTier(id: 0, name: 'Bronze', minAmount: 1000, multiplier: 1.0, minLockDays: 7, color: Color(0xFFCD7F32)),
    StakingTier(id: 1, name: 'Silver', minAmount: 10000, multiplier: 1.25, minLockDays: 30, color: Color(0xFFC0C0C0)),
    StakingTier(id: 2, name: 'Gold', minAmount: 50000, multiplier: 1.5, minLockDays: 90, color: Color(0xFFFFD700)),
    StakingTier(id: 3, name: 'Platinum', minAmount: 100000, multiplier: 2.0, minLockDays: 180, color: Color(0xFFE5E4E2)),
    StakingTier(id: 4, name: 'Diamond', minAmount: 500000, multiplier: 3.0, minLockDays: 365, color: Color(0xFFB9F2FF)),
  ];

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    await Future.delayed(Duration(milliseconds: 500));
    setState(() {
      _userStake = StakeInfo(
        amount: 25000,
        startTime: DateTime.now().subtract(Duration(days: 30)),
        lockDurationDays: 90,
        multiplier: 1.5,
        pendingRewards: 312.5,
        tierName: 'Gold',
        canUnstakeWithoutPenalty: false,
      );
      _isLoading = false;
    });
  }

  StakingTier _getApplicableTier() {
    for (int i = _tiers.length - 1; i >= 0; i--) {
      if (_stakeAmount >= _tiers[i].minAmount && _lockDays >= _tiers[i].minLockDays) {
        return _tiers[i];
      }
    }
    return _tiers[0];
  }

  double _calculateEstimatedRewards() {
    final tier = _getApplicableTier();
    final yearlyRate = 12.5 / 100;
    final dailyRate = yearlyRate / 365;
    return _stakeAmount * dailyRate * _lockDays * tier.multiplier;
  }

  Future<void> _handleStake() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Confirm Stake'),
        content: Text(
          'You are about to stake ${_stakeAmount.toStringAsFixed(0)} NWR for $_lockDays days.\n\n'
          'Tier: ${_getApplicableTier().name} (${_getApplicableTier().multiplier}x)',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text('Cancel')),
          ElevatedButton(onPressed: () => Navigator.pop(context, true), child: Text('Confirm')),
        ],
      ),
    );

    if (confirmed == true) {
      // Call staking service
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Staking transaction submitted')),
      );
    }
  }

  Future<void> _handleClaimRewards() async {
    if (_userStake == null || _userStake!.pendingRewards <= 0) return;
    
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Claiming ${_userStake!.pendingRewards.toStringAsFixed(2)} NWR rewards')),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: Text('Staking')),
        body: Center(child: CircularProgressIndicator()),
      );
    }

    final applicableTier = _getApplicableTier();

    return Scaffold(
      appBar: AppBar(
        title: Text('💎 NWR Staking'),
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Current Stake Card
            if (_userStake != null) ...[
              _buildCurrentStakeCard(),
              SizedBox(height: 24),
            ],

            // Stake Form
            Card(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Stake Tokens', style: Theme.of(context).textTheme.titleLarge),
                    SizedBox(height: 16),
                    
                    // Amount Input
                    TextField(
                      decoration: InputDecoration(
                        labelText: 'Amount',
                        suffixText: 'NWR',
                        helperText: 'Balance: ${_walletBalance.toStringAsFixed(0)} NWR',
                      ),
                      keyboardType: TextInputType.number,
                      onChanged: (value) {
                        setState(() {
                          _stakeAmount = double.tryParse(value) ?? 0;
                        });
                      },
                    ),
                    SizedBox(height: 24),

                    // Lock Duration Slider
                    Text('Lock Duration: $_lockDays days'),
                    Slider(
                      value: _lockDays.toDouble(),
                      min: 7,
                      max: 365,
                      divisions: 50,
                      label: '$_lockDays days',
                      onChanged: (value) {
                        setState(() {
                          _lockDays = value.round();
                        });
                      },
                    ),
                    SizedBox(height: 16),

                    // Tier Info
                    Container(
                      padding: EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: applicableTier.color.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.star, color: applicableTier.color),
                          SizedBox(width: 8),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('${applicableTier.name} Tier', style: TextStyle(fontWeight: FontWeight.bold)),
                                Text('${applicableTier.multiplier}x multiplier • Est. ${_calculateEstimatedRewards().toStringAsFixed(2)} NWR'),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    SizedBox(height: 16),

                    // Stake Button
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: _stakeAmount > 0 && _stakeAmount <= _walletBalance ? _handleStake : null,
                        child: Padding(
                          padding: EdgeInsets.symmetric(vertical: 12),
                          child: Text('Stake ${_stakeAmount.toStringAsFixed(0)} NWR'),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            SizedBox(height: 24),

            // Tiers Table
            Text('Staking Tiers', style: Theme.of(context).textTheme.titleLarge),
            SizedBox(height: 8),
            Card(
              child: Column(
                children: _tiers.map((tier) => ListTile(
                  leading: CircleAvatar(backgroundColor: tier.color, radius: 16),
                  title: Text(tier.name),
                  subtitle: Text('Min: ${tier.minAmount.toStringAsFixed(0)} NWR • ${tier.minLockDays}d lock'),
                  trailing: Text('${tier.multiplier}x', style: TextStyle(fontWeight: FontWeight.bold)),
                )).toList(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCurrentStakeCard() {
    return Card(
      color: Theme.of(context).primaryColor.withOpacity(0.1),
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('Your Stake', style: Theme.of(context).textTheme.titleMedium),
                Chip(label: Text(_userStake!.tierName)),
              ],
            ),
            SizedBox(height: 8),
            Text(
              '${_userStake!.amount.toStringAsFixed(0)} NWR',
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: Theme.of(context).primaryColor,
              ),
            ),
            SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _buildStatItem('Multiplier', '${_userStake!.multiplier}x'),
                _buildStatItem('Lock', '${_userStake!.lockDurationDays}d'),
                _buildStatItem('Rewards', '${_userStake!.pendingRewards.toStringAsFixed(2)}'),
              ],
            ),
            SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    onPressed: _userStake!.pendingRewards > 0 ? _handleClaimRewards : null,
                    child: Text('Claim Rewards'),
                  ),
                ),
                SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton(
                    onPressed: () {},
                    style: OutlinedButton.styleFrom(foregroundColor: Colors.red),
                    child: Text('Unstake'),
                  ),
                ),
              ],
            ),
            if (!_userStake!.canUnstakeWithoutPenalty)
              Padding(
                padding: EdgeInsets.only(top: 8),
                child: Text(
                  '⚠️ Early unstaking will incur 10% penalty',
                  style: TextStyle(color: Colors.orange, fontSize: 12),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatItem(String label, String value) {
    return Column(
      children: [
        Text(value, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
        Text(label, style: TextStyle(color: Colors.grey)),
      ],
    );
  }
}
