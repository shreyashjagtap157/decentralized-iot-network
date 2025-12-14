import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';
import '../services/network_service.dart';

class SettingsScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Settings'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: ListView(
        children: [
          _buildSection(
            context,
            'Account',
            [
              ListTile(
                leading: Icon(Icons.person),
                title: Text('Profile'),
                subtitle: Text('Manage your profile'),
                onTap: () {
                  // Navigate to profile screen
                },
              ),
              ListTile(
                leading: Icon(Icons.logout),
                title: Text('Logout'),
                subtitle: Text('Sign out of your account'),
                onTap: () {
                  Provider.of<AuthService>(context, listen: false).logout();
                },
              ),
            ],
          ),
          _buildSection(
            context,
            'Network Sharing',
            [
              Consumer<NetworkSharingState>(
                builder: (context, networkState, child) {
                  return SwitchListTile(
                    secondary: Icon(Icons.wifi_tethering),
                    title: Text('Auto-enable sharing'),
                    subtitle: Text('Automatically start sharing when app opens'),
                    value: networkState.isSharing,
                    onChanged: (value) {
                      if (value) {
                        networkState.enableSharing();
                      } else {
                        networkState.disableSharing();
                      }
                    },
                  );
                },
              ),
              ListTile(
                leading: Icon(Icons.speed),
                title: Text('Bandwidth limit'),
                subtitle: Text('Set maximum bandwidth for sharing'),
                onTap: () {
                  _showBandwidthDialog(context);
                },
              ),
            ],
          ),
          _buildSection(
            context,
            'Privacy & Security',
            [
              SwitchListTile(
                secondary: Icon(Icons.fingerprint),
                title: Text('Biometric authentication'),
                subtitle: Text('Use fingerprint or face ID'),
                value: true,
                onChanged: (value) {
                  // Implement biometric toggle
                },
              ),
              ListTile(
                leading: Icon(Icons.privacy_tip),
                title: Text('Privacy policy'),
                subtitle: Text('View our privacy policy'),
                onTap: () {
                  // Show privacy policy
                },
              ),
            ],
          ),
          _buildSection(
            context,
            'About',
            [
              ListTile(
                leading: Icon(Icons.info),
                title: Text('App version'),
                subtitle: Text('1.0.0'),
              ),
              ListTile(
                leading: Icon(Icons.help),
                title: Text('Help & Support'),
                subtitle: Text('Get help with the app'),
                onTap: () {
                  // Show help screen
                },
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSection(BuildContext context, String title, List<Widget> children) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: EdgeInsets.fromLTRB(16, 16, 16, 8),
          child: Text(
            title,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: Theme.of(context).primaryColor,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        ...children,
        Divider(),
      ],
    );
  }

  void _showBandwidthDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Bandwidth Limit'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Select maximum bandwidth for network sharing:'),
            SizedBox(height: 16),
            DropdownButton<String>(
              value: '10 MB/s',
              items: ['1 MB/s', '5 MB/s', '10 MB/s', '20 MB/s', 'Unlimited']
                  .map((e) => DropdownMenuItem(value: e, child: Text(e)))
                  .toList(),
              onChanged: (value) {
                // Save bandwidth preference
              },
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text('Save'),
          ),
        ],
      ),
    );
  }
}
