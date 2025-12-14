import 'package:flutter/material.dart';

class HomePage extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Home')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('Welcome to the Decentralized IoT App!', style: TextStyle(fontSize: 20)),
            SizedBox(height: 32),
            ElevatedButton.icon(
              icon: Icon(Icons.dashboard),
              label: Text('Go to Dashboard'),
              onPressed: () => Navigator.pushNamed(context, '/dashboard'),
            ),
            SizedBox(height: 16),
            ElevatedButton.icon(
              icon: Icon(Icons.account_balance_wallet),
              label: Text('Wallet'),
              onPressed: () => Navigator.pushNamed(context, '/wallet'),
            ),
            SizedBox(height: 16),
            ElevatedButton.icon(
              icon: Icon(Icons.add),
              label: Text('Onboard Device'),
              onPressed: () => Navigator.pushNamed(context, '/onboarding'),
            ),
          ],
        ),
      ),
    );
  }
}
