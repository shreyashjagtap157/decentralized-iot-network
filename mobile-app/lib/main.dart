
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'dart:convert';
import 'home_page.dart';
import 'device_list.dart';
import 'settings_page.dart';
import 'screens/dashboard_screen.dart';
import 'screens/login_screen.dart';
import 'screens/onboarding_screen.dart';
import 'screens/wallet_screen.dart';

void main() {
  runApp(
    ChangeNotifierProvider(
      create: (context) => NetworkSharingState(),
      child: MyApp(),
    ),
  );
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Decentralized IoT',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        useMaterial3: true,
      ),
      initialRoute: '/dashboard',
      routes: {
        '/': (context) => LoginScreen(),
        '/login': (context) => LoginScreen(),
        '/dashboard': (context) => DashboardScreen(),
        '/devices': (context) => DeviceListPage(),
        '/settings': (context) => SettingsPage(),
        '/onboarding': (context) => OnboardingScreen(),
        '/wallet': (context) => WalletScreen(),
      },
    );
  }
}

/// State management for network sharing functionality
class NetworkSharingState extends ChangeNotifier {
  double _earnings = 0.0;
  bool _isSharing = false;
  WebSocketChannel? _channel;
  bool _isConnected = false;
  String _connectionStatus = 'Disconnected';

  // WebSocket URL - should be configured from environment
  static const String _wsUrl = String.fromEnvironment(
    'WS_URL',
    defaultValue: 'wss://api.example.com/metrics',
  );

  double get earnings => _earnings;
  bool get isSharing => _isSharing;
  bool get isConnected => _isConnected;
  String get connectionStatus => _connectionStatus;

  void _connectToWebSocket() {
    try {
      _channel = WebSocketChannel.connect(
        Uri.parse(_wsUrl),
      );
      _isConnected = true;
      _connectionStatus = 'Connected';
      
      _channel!.stream.listen(
        (data) {
          try {
            final metrics = jsonDecode(data);
            _earnings += (metrics['newEarnings'] as num?)?.toDouble() ?? 0.0;
            notifyListeners();
          } catch (e) {
            debugPrint('Error parsing WebSocket data: $e');
          }
        },
        onError: (error) {
          _isConnected = false;
          _connectionStatus = 'Error: $error';
          notifyListeners();
        },
        onDone: () {
          _isConnected = false;
          _connectionStatus = 'Disconnected';
          notifyListeners();
        },
      );
      notifyListeners();
    } catch (e) {
      _isConnected = false;
      _connectionStatus = 'Connection failed: $e';
      notifyListeners();
    }
  }

  Future<void> enableSharing() async {
    _isSharing = true;
    _connectionStatus = 'Connecting...';
    notifyListeners();
    
    _connectToWebSocket();
    
    // Simulate initial earnings for demo purposes
    Future.delayed(const Duration(seconds: 2), () {
      if (_isSharing) {
        _earnings += 0.5;
        notifyListeners();
      }
    });
  }

  void disableSharing() {
    _isSharing = false;
    _isConnected = false;
    _connectionStatus = 'Disconnected';
    _channel?.sink.close();
    _channel = null;
    notifyListeners();
  }

  void resetEarnings() {
    _earnings = 0.0;
    notifyListeners();
  }

  @override
  void dispose() {
    _channel?.sink.close();
    super.dispose();
  }
}

