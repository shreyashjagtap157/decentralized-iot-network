import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

class WebSocketService extends ChangeNotifier {
  static const String _baseUrl = 'ws://localhost:8000';
  WebSocketChannel? _channel;
  bool _isConnected = false;
  Timer? _reconnectTimer;
  Timer? _heartbeatTimer;
  
  // Dashboard data
  int _activeDevices = 0;
  double _totalBytesTransmitted = 0.0;
  double _totalEarnings = 0.0;
  int _networkQuality = 0;
  final List<Map<String, dynamic>> _recentActivities = [];
  
  // Getters
  bool get isConnected => _isConnected;
  int get activeDevices => _activeDevices;
  double get totalBytesTransmitted => _totalBytesTransmitted;
  double get totalEarnings => _totalEarnings;
  int get networkQuality => _networkQuality;
  List<Map<String, dynamic>> get recentActivities => List.unmodifiable(_recentActivities);

  Future<void> connect() async {
    if (_isConnected) return;

    try {
      _channel = WebSocketChannel.connect(
        Uri.parse('$_baseUrl/ws/dashboard'),
      );

      _isConnected = true;
      notifyListeners();

      _startHeartbeat();
      _listenToMessages();

      print('WebSocket connected successfully');
    } catch (e) {
      print('WebSocket connection error: $e');
      _isConnected = false;
      notifyListeners();
      _scheduleReconnect();
    }
  }

  void _listenToMessages() {
    _channel?.stream.listen(
      (data) {
        try {
          final message = json.decode(data);
          _handleMessage(message);
        } catch (e) {
          print('Error parsing WebSocket message: $e');
        }
      },
      onError: (error) {
        print('WebSocket error: $error');
        _handleDisconnection();
      },
      onDone: () {
        print('WebSocket connection closed');
        _handleDisconnection();
      },
    );
  }

  void _handleMessage(Map<String, dynamic> message) {
    final type = message['type'];
    final data = message['data'];

    switch (type) {
      case 'device_status':
        _updateDeviceStatus(data);
        break;
      case 'usage_data':
        _updateUsageData(data);
        break;
      case 'earnings_update':
        _updateEarnings(data);
        break;
      case 'network_quality':
        _updateNetworkQuality(data);
        break;
      case 'activity':
        _addActivity(data);
        break;
      case 'heartbeat':
        // Heartbeat response - connection is alive
        break;
      default:
        print('Unknown message type: $type');
    }

    notifyListeners();
  }

  void _updateDeviceStatus(Map<String, dynamic> data) {
    _activeDevices = data['active_devices'] ?? 0;
  }

  void _updateUsageData(Map<String, dynamic> data) {
    final bytesTransmitted = (data['bytes_transmitted'] ?? 0).toDouble();
    _totalBytesTransmitted += bytesTransmitted / (1024 * 1024); // Convert to MB
  }

  void _updateEarnings(Map<String, dynamic> data) {
    _totalEarnings = (data['total_earnings'] ?? 0.0).toDouble();
  }

  void _updateNetworkQuality(Map<String, dynamic> data) {
    _networkQuality = data['quality_score'] ?? 0;
  }

  void _addActivity(Map<String, dynamic> data) {
    final activity = {
      'message': data['message'] ?? '',
      'timestamp': DateTime.now().toString(),
      'type': data['type'] ?? 'info',
    };

    _recentActivities.insert(0, activity);
    
    // Keep only the last 20 activities
    if (_recentActivities.length > 20) {
      _recentActivities.removeRange(20, _recentActivities.length);
    }
  }

  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(const Duration(seconds: 30), (timer) {
      if (_isConnected && _channel != null) {
        try {
          _channel!.sink.add(json.encode({
            'type': 'heartbeat',
            'timestamp': DateTime.now().toIso8601String(),
          }));
        } catch (e) {
          print('Heartbeat error: $e');
          _handleDisconnection();
        }
      }
    });
  }

  void _handleDisconnection() {
    _isConnected = false;
    _heartbeatTimer?.cancel();
    notifyListeners();
    _scheduleReconnect();
  }

  void _scheduleReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 5), () {
      if (!_isConnected) {
        print('Attempting to reconnect WebSocket...');
        connect();
      }
    });
  }

  Future<void> disconnect() async {
    _isConnected = false;
    _reconnectTimer?.cancel();
    _heartbeatTimer?.cancel();
    
    try {
      await _channel?.sink.close();
    } catch (e) {
      print('Error closing WebSocket: $e');
    }
    
    _channel = null;
    notifyListeners();
  }

  Future<void> reconnect() async {
    await disconnect();
    await Future.delayed(const Duration(milliseconds: 500));
    await connect();
  }

  // Send custom messages
  void sendMessage(Map<String, dynamic> message) {
    if (_isConnected && _channel != null) {
      try {
        _channel!.sink.add(json.encode(message));
      } catch (e) {
        print('Error sending message: $e');
      }
    }
  }

  // Device control methods
  void requestDeviceList() {
    sendMessage({
      'type': 'get_devices',
      'timestamp': DateTime.now().toIso8601String(),
    });
  }

  void requestEarningsUpdate() {
    sendMessage({
      'type': 'get_earnings',
      'timestamp': DateTime.now().toIso8601String(),
    });
  }

  void requestNetworkStats() {
    sendMessage({
      'type': 'get_network_stats',
      'timestamp': DateTime.now().toIso8601String(),
    });
  }

  @override
  void dispose() {
    disconnect();
    super.dispose();
  }
}
