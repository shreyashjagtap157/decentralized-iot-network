import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../main.dart';

class WalletScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Wallet')),
      body: Consumer<NetworkSharingState>(
        builder: (context, state, child) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.account_balance_wallet, size: 80, color: Colors.green),
                SizedBox(height: 24),
                Text('Your Wallet Balance', style: TextStyle(fontSize: 20)),
                SizedBox(height: 12),
                Text(
                  'Ξ ${state.earnings.toStringAsFixed(4)}',
                  style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold),
                ),
                SizedBox(height: 24),
                ElevatedButton(
                  onPressed: null, // Disabled until full blockchain integration
                  child: Text('Withdrawing Soon'),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
