import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:permission_handler/permission_handler.dart';
import 'dart:convert';
import 'dart:async';

class NetworkSharingState extends ChangeNotifier {
  double _earnings = 0.0;
  bool _isSharing = false;
  WebSocketChannel? _channel;
  Timer? _earningsTimer;
  List<Map<String, dynamic>> _recentTransactions = [];

  double get earnings => _earnings;
  bool get isSharing => _isSharing;
  List<Map<String, dynamic>> get recentTransactions => _recentTransactions;

  void _connectToWebSocket() {
    try {
      _channel = WebSocketChannel.connect(
        Uri.parse('ws://localhost:8000/ws/mobile'),
      );
      _channel!.stream.listen(
        (data) {
          final message = json.decode(data);
          if (message['type'] == 'earnings_update') {
            _earnings += (message['amount'] ?? 0.0);
            _recentTransactions.insert(0, {
              'amount': message['amount'],
              'timestamp': DateTime.now(),
              'device_id': message['device_id'],
            });
            if (_recentTransactions.length > 10) {
              _recentTransactions.removeLast();
            }
            notifyListeners();
          }
        },
        onError: (error) {
          print('WebSocket error: $error');
        },
      );
    } catch (e) {
      print('WebSocket connection failed: $e');
    }
  }

  Future<void> enableSharing() async {
    // Request permissions
    final locationPermission = await Permission.location.request();
    final networkPermission = await Permission.phone.request();
    
    if (locationPermission.isGranted && networkPermission.isGranted) {
      _isSharing = true;
      _connectToWebSocket();
      
      // Start earnings simulation
      _earningsTimer = Timer.periodic(Duration(seconds: 10), (timer) {
        final earning = (0.1 + (DateTime.now().millisecond % 100) / 1000);
        _earnings += earning;
        _recentTransactions.insert(0, {
          'amount': earning,
          'timestamp': DateTime.now(),
          'device_id': 'mobile_device',
        });
        if (_recentTransactions.length > 10) {
          _recentTransactions.removeLast();
        }
        notifyListeners();
      });
      
      notifyListeners();
    } else {
      throw Exception('Required permissions not granted');
    }
  }

  void disableSharing() {
    _isSharing = false;
    _channel?.sink.close();
    _earningsTimer?.cancel();
    notifyListeners();
  }

  @override
  void dispose() {
    _channel?.sink.close();
    _earningsTimer?.cancel();
    super.dispose();
  }
}
