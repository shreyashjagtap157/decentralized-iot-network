import 'package:flutter/material.dart';

/// Chain configuration
class Chain {
  final int id;
  final String name;
  final String icon;
  final bool enabled;
  final double minAmount;
  final double maxAmount;
  final double dailyRemaining;

  Chain({
    required this.id,
    required this.name,
    required this.icon,
    required this.enabled,
    required this.minAmount,
    required this.maxAmount,
    required this.dailyRemaining,
  });
}

/// Bridge history entry
class BridgeHistory {
  final String id;
  final int fromChain;
  final int toChain;
  final double amount;
  final double fee;
  final String status;
  final DateTime timestamp;

  BridgeHistory({
    required this.id,
    required this.fromChain,
    required this.toChain,
    required this.amount,
    required this.fee,
    required this.status,
    required this.timestamp,
  });
}

class BridgeScreen extends StatefulWidget {
  const BridgeScreen({Key? key}) : super(key: key);

  @override
  State<BridgeScreen> createState() => _BridgeScreenState();
}

class _BridgeScreenState extends State<BridgeScreen> {
  bool _isLoading = true;
  double _amount = 0;
  int _fromChain = 1;
  int _toChain = 137;
  double _walletBalance = 50000;
  final double _feePercentage = 0.5;

  final List<Chain> _chains = [
    Chain(id: 1, name: 'Ethereum', icon: '⟠', enabled: true, minAmount: 100, maxAmount: 1000000, dailyRemaining: 5000000),
    Chain(id: 137, name: 'Polygon', icon: '🟣', enabled: true, minAmount: 10, maxAmount: 1000000, dailyRemaining: 8000000),
    Chain(id: 56, name: 'BNB Chain', icon: '🟡', enabled: true, minAmount: 10, maxAmount: 1000000, dailyRemaining: 7000000),
    Chain(id: 42161, name: 'Arbitrum', icon: '🔵', enabled: true, minAmount: 50, maxAmount: 1000000, dailyRemaining: 4000000),
  ];

  List<BridgeHistory> _history = [];

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    await Future.delayed(Duration(milliseconds: 500));
    setState(() {
      _history = [
        BridgeHistory(
          id: 'br_001',
          fromChain: 1,
          toChain: 137,
          amount: 5000,
          fee: 25,
          status: 'completed',
          timestamp: DateTime.now().subtract(Duration(days: 2)),
        ),
        BridgeHistory(
          id: 'br_002',
          fromChain: 137,
          toChain: 56,
          amount: 10000,
          fee: 50,
          status: 'pending',
          timestamp: DateTime.now().subtract(Duration(hours: 1)),
        ),
      ];
      _isLoading = false;
    });
  }

  String _getChainName(int id) => _chains.firstWhere((c) => c.id == id, orElse: () => _chains[0]).name;
  String _getChainIcon(int id) => _chains.firstWhere((c) => c.id == id, orElse: () => _chains[0]).icon;

  double get _fee => _amount * _feePercentage / 100;
  double get _received => _amount - _fee;

  String? _validateBridge() {
    if (_amount <= 0) return 'Enter an amount';
    if (_amount > _walletBalance) return 'Insufficient balance';
    final destChain = _chains.firstWhere((c) => c.id == _toChain);
    if (_amount < destChain.minAmount) return 'Minimum ${destChain.minAmount} NWR';
    if (_amount > destChain.maxAmount) return 'Maximum ${destChain.maxAmount} NWR';
    if (_fromChain == _toChain) return 'Select different chains';
    return null;
  }

  Future<void> _handleBridge() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Confirm Bridge'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('From: ${_getChainIcon(_fromChain)} ${_getChainName(_fromChain)}'),
            Text('To: ${_getChainIcon(_toChain)} ${_getChainName(_toChain)}'),
            SizedBox(height: 8),
            Text('Amount: ${_amount.toStringAsFixed(2)} NWR'),
            Text('Fee: ${_fee.toStringAsFixed(2)} NWR'),
            Text('You receive: ${_received.toStringAsFixed(2)} NWR', style: TextStyle(fontWeight: FontWeight.bold)),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text('Cancel')),
          ElevatedButton(onPressed: () => Navigator.pop(context, true), child: Text('Bridge')),
        ],
      ),
    );

    if (confirmed == true) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Bridge transaction submitted')),
      );
    }
  }

  void _swapChains() {
    setState(() {
      final temp = _fromChain;
      _fromChain = _toChain;
      _toChain = temp;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: Text('Bridge')),
        body: Center(child: CircularProgressIndicator()),
      );
    }

    final validationError = _validateBridge();

    return Scaffold(
      appBar: AppBar(
        title: Text('🌉 Cross-Chain Bridge'),
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Bridge Form
            Card(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('From', style: TextStyle(color: Colors.grey)),
                    DropdownButtonFormField<int>(
                      value: _fromChain,
                      items: _chains.where((c) => c.enabled).map((c) => DropdownMenuItem(
                        value: c.id,
                        child: Text('${c.icon} ${c.name}'),
                      )).toList(),
                      onChanged: (value) => setState(() => _fromChain = value!),
                      decoration: InputDecoration(border: OutlineInputBorder()),
                    ),
                    SizedBox(height: 8),
                    
                    Center(
                      child: IconButton(
                        onPressed: _swapChains,
                        icon: Icon(Icons.swap_vert, size: 32),
                        color: Theme.of(context).primaryColor,
                      ),
                    ),
                    
                    Text('To', style: TextStyle(color: Colors.grey)),
                    DropdownButtonFormField<int>(
                      value: _toChain,
                      items: _chains.where((c) => c.enabled && c.id != _fromChain).map((c) => DropdownMenuItem(
                        value: c.id,
                        child: Text('${c.icon} ${c.name}'),
                      )).toList(),
                      onChanged: (value) => setState(() => _toChain = value!),
                      decoration: InputDecoration(border: OutlineInputBorder()),
                    ),
                    SizedBox(height: 16),
                    
                    TextField(
                      decoration: InputDecoration(
                        labelText: 'Amount',
                        suffixText: 'NWR',
                        helperText: 'Balance: ${_walletBalance.toStringAsFixed(0)} NWR',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType: TextInputType.number,
                      onChanged: (value) => setState(() => _amount = double.tryParse(value) ?? 0),
                    ),
                    SizedBox(height: 16),
                    
                    if (_amount > 0) ...[
                      Container(
                        padding: EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.blue.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Column(
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text('Fee ($_feePercentage%)'),
                                Text('${_fee.toStringAsFixed(2)} NWR'),
                              ],
                            ),
                            SizedBox(height: 4),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text('You\'ll receive', style: TextStyle(fontWeight: FontWeight.bold)),
                                Text('${_received.toStringAsFixed(2)} NWR', style: TextStyle(fontWeight: FontWeight.bold)),
                              ],
                            ),
                          ],
                        ),
                      ),
                      SizedBox(height: 16),
                    ],
                    
                    if (validationError != null)
                      Padding(
                        padding: EdgeInsets.only(bottom: 8),
                        child: Text(validationError, style: TextStyle(color: Colors.red)),
                      ),
                    
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: validationError == null ? _handleBridge : null,
                        child: Padding(
                          padding: EdgeInsets.symmetric(vertical: 12),
                          child: Text('Bridge Tokens'),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            SizedBox(height: 24),
            
            // History
            Text('Bridge History', style: Theme.of(context).textTheme.titleLarge),
            SizedBox(height: 8),
            if (_history.isEmpty)
              Card(child: Padding(
                padding: EdgeInsets.all(16),
                child: Text('No bridge history yet'),
              ))
            else
              ...(_history.map((h) => Card(
                child: ListTile(
                  leading: Text('${_getChainIcon(h.fromChain)} → ${_getChainIcon(h.toChain)}', style: TextStyle(fontSize: 20)),
                  title: Text('${h.amount.toStringAsFixed(0)} NWR'),
                  subtitle: Text('Fee: ${h.fee.toStringAsFixed(2)} • ${h.timestamp.toString().substring(0, 16)}'),
                  trailing: Chip(
                    label: Text(h.status),
                    backgroundColor: h.status == 'completed' ? Colors.green : Colors.orange,
                    labelStyle: TextStyle(color: Colors.white),
                  ),
                ),
              ))),
          ],
        ),
      ),
    );
  }
}
