import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/network_service.dart';

class HomeScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Network Sharing'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: Consumer<NetworkSharingState>(
        builder: (context, networkState, child) {
          return Padding(
            padding: EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Card(
                  child: Padding(
                    padding: EdgeInsets.all(16.0),
                    child: Column(
                      children: [
                        Icon(
                          networkState.isSharing 
                              ? Icons.wifi_tethering 
                              : Icons.wifi_tethering_off,
                          size: 64,
                          color: networkState.isSharing 
                              ? Colors.green 
                              : Colors.grey,
                        ),
                        SizedBox(height: 16),
                        Text(
                          networkState.isSharing 
                              ? 'Network Sharing Active' 
                              : 'Network Sharing Inactive',
                          style: Theme.of(context).textTheme.headlineSmall,
                          textAlign: TextAlign.center,
                        ),
                        SizedBox(height: 16),
                        Text(
                          'Current Earnings: \$${networkState.earnings.toStringAsFixed(6)}',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                      ],
                    ),
                  ),
                ),
                SizedBox(height: 24),
                ElevatedButton(
                  onPressed: networkState.isSharing 
                      ? networkState.disableSharing
                      : () async {
                          try {
                            await networkState.enableSharing();
                          } catch (e) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text('Failed to enable sharing: $e')),
                            );
                          }
                        },
                  style: ElevatedButton.styleFrom(
                    padding: EdgeInsets.symmetric(vertical: 16),
                    backgroundColor: networkState.isSharing 
                        ? Colors.red 
                        : Colors.green,
                  ),
                  child: Text(
                    networkState.isSharing ? 'Stop Sharing' : 'Start Sharing',
                    style: TextStyle(fontSize: 18, color: Colors.white),
                  ),
                ),
                SizedBox(height: 24),
                if (networkState.recentTransactions.isNotEmpty) ...[
                  Text(
                    'Recent Earnings',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  SizedBox(height: 8),
                  Expanded(
                    child: ListView.builder(
                      itemCount: networkState.recentTransactions.length,
                      itemBuilder: (context, index) {
                        final transaction = networkState.recentTransactions[index];
                        return ListTile(
                          leading: Icon(Icons.attach_money, color: Colors.green),
                          title: Text('\$${transaction['amount'].toStringAsFixed(6)}'),
                          subtitle: Text(transaction['timestamp'].toString()),
                          trailing: Text(transaction['device_id']),
                        );
                      },
                    ),
                  ),
                ],
              ],
            ),
          );
        },
      ),
    );
  }
}
