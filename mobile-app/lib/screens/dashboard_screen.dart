import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';
import '../services/websocket_service.dart';
import 'earnings_screen.dart';
import 'settings_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({Key? key}) : super(key: key);

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  int _selectedIndex = 0;
  late WebSocketService _webSocketService;

  final List<Widget> _screens = [
    const HomeTab(),
    const EarningsScreen(),
    const SettingsScreen(),
  ];

  final List<String> _titles = [
    'Dashboard',
    'Earnings',
    'Settings',
  ];

  @override
  void initState() {
    super.initState();
    _webSocketService = context.read<WebSocketService>();
    _webSocketService.connect();
  }

  @override
  void dispose() {
    _webSocketService.disconnect();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_titles[_selectedIndex]),
        backgroundColor: Colors.blue.shade700,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              _webSocketService.reconnect();
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Refreshing connection...'),
                  duration: Duration(seconds: 2),
                ),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () async {
              final authService = context.read<AuthService>();
              await authService.logout();
              if (mounted) {
                Navigator.of(context).pushReplacementNamed('/login');
              }
            },
          ),
        ],
      ),
      body: IndexedStack(
        index: _selectedIndex,
        children: _screens,
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _selectedIndex,
        onTap: (index) {
          setState(() {
            _selectedIndex = index;
          });
        },
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.dashboard),
            label: 'Dashboard',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.monetization_on),
            label: 'Earnings',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.settings),
            label: 'Settings',
          ),
        ],
      ),
    );
  }
}

class HomeTab extends StatelessWidget {
  const HomeTab({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Consumer<WebSocketService>(
      builder: (context, webSocketService, child) {
        return SingleChildScrollView(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Connection Status Card
              Card(
                elevation: 4,
                child: ListTile(
                  leading: Icon(
                    webSocketService.isConnected
                        ? Icons.wifi
                        : Icons.wifi_off,
                    color: webSocketService.isConnected
                        ? Colors.green
                        : Colors.red,
                  ),
                  title: Text(
                    webSocketService.isConnected
                        ? 'Connected'
                        : 'Disconnected',
                  ),
                  subtitle: const Text('Network Status'),
                ),
              ),
              const SizedBox(height: 16),

              // Device Stats Grid
              GridView.count(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                crossAxisCount: 2,
                childAspectRatio: 1.5,
                crossAxisSpacing: 16,
                mainAxisSpacing: 16,
                children: [
                  _buildStatCard(
                    'Active Devices',
                    webSocketService.activeDevices.toString(),
                    Icons.router,
                    Colors.blue,
                  ),
                  _buildStatCard(
                    'Data Transmitted',
                    '${webSocketService.totalBytesTransmitted} MB',
                    Icons.upload,
                    Colors.green,
                  ),
                  _buildStatCard(
                    'Total Earnings',
                    '\$${webSocketService.totalEarnings.toStringAsFixed(6)}',
                    Icons.account_balance_wallet,
                    Colors.orange,
                  ),
                  _buildStatCard(
                    'Network Quality',
                    '${webSocketService.networkQuality}%',
                    Icons.signal_cellular_4_bar,
                    Colors.purple,
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Recent Activity Card
              Card(
                elevation: 4,
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Recent Activity',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 12),
                      ...webSocketService.recentActivities
                          .take(5)
                          .map((activity) => ListTile(
                                dense: true,
                                leading: Icon(
                                  Icons.circle,
                                  size: 8,
                                  color: Colors.grey.shade400,
                                ),
                                title: Text(
                                  activity['message'] ?? '',
                                  style: const TextStyle(fontSize: 14),
                                ),
                                subtitle: Text(
                                  activity['timestamp'] ?? '',
                                  style: TextStyle(
                                    fontSize: 12,
                                    color: Colors.grey.shade600,
                                  ),
                                ),
                              ))
                          .toList(),
                      if (webSocketService.recentActivities.isEmpty)
                        const Padding(
                          padding: EdgeInsets.symmetric(vertical: 20),
                          child: Center(
                            child: Text(
                              'No recent activity',
                              style: TextStyle(
                                color: Colors.grey,
                                fontSize: 14,
                              ),
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildStatCard(String title, String value, IconData icon, Color color) {
    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 32, color: color),
            const SizedBox(height: 8),
            Text(
              value,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              title,
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey.shade600,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
