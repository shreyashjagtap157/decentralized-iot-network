import 'package:flutter/material.dart';

/// Device NFT data
class DeviceNFT {
  final int tokenId;
  final String deviceId;
  final String deviceType;
  final DateTime registrationDate;
  final double totalRewardsEarned;
  final double totalDataTransferredGB;
  final int qualityScore;
  final bool isActive;
  final String imageUrl;

  DeviceNFT({
    required this.tokenId,
    required this.deviceId,
    required this.deviceType,
    required this.registrationDate,
    required this.totalRewardsEarned,
    required this.totalDataTransferredGB,
    required this.qualityScore,
    required this.isActive,
    required this.imageUrl,
  });

  String get tier {
    if (qualityScore >= 90) return 'Diamond';
    if (qualityScore >= 75) return 'Gold';
    if (qualityScore >= 50) return 'Silver';
    return 'Bronze';
  }

  Color get tierColor {
    if (qualityScore >= 90) return Color(0xFFB9F2FF);
    if (qualityScore >= 75) return Color(0xFFFFD700);
    if (qualityScore >= 50) return Color(0xFFC0C0C0);
    return Color(0xFFCD7F32);
  }
}

class NFTScreen extends StatefulWidget {
  const NFTScreen({Key? key}) : super(key: key);

  @override
  State<NFTScreen> createState() => _NFTScreenState();
}

class _NFTScreenState extends State<NFTScreen> {
  bool _isLoading = true;
  List<DeviceNFT> _devices = [];
  int _totalRewards = 0;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    await Future.delayed(Duration(milliseconds: 500));
    setState(() {
      _devices = [
        DeviceNFT(
          tokenId: 1,
          deviceId: 'ESP32_ABC123',
          deviceType: 'ESP32',
          registrationDate: DateTime.now().subtract(Duration(days: 120)),
          totalRewardsEarned: 1523.45,
          totalDataTransferredGB: 245.8,
          qualityScore: 92,
          isActive: true,
          imageUrl: 'https://api.iot-network.io/nft/1/image.png',
        ),
        DeviceNFT(
          tokenId: 2,
          deviceId: 'PI_XYZ789',
          deviceType: 'Raspberry Pi',
          registrationDate: DateTime.now().subtract(Duration(days: 45)),
          totalRewardsEarned: 456.78,
          totalDataTransferredGB: 89.2,
          qualityScore: 78,
          isActive: true,
          imageUrl: 'https://api.iot-network.io/nft/2/image.png',
        ),
        DeviceNFT(
          tokenId: 3,
          deviceId: 'ESP32_DEF456',
          deviceType: 'ESP32',
          registrationDate: DateTime.now().subtract(Duration(days: 200)),
          totalRewardsEarned: 2341.00,
          totalDataTransferredGB: 512.4,
          qualityScore: 45,
          isActive: false,
          imageUrl: 'https://api.iot-network.io/nft/3/image.png',
        ),
      ];
      _totalRewards = _devices.fold(0, (sum, d) => sum + d.totalRewardsEarned.round());
      _isLoading = false;
    });
  }

  Future<void> _showMintDialog() async {
    String? deviceId;
    String deviceType = 'ESP32';

    final result = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Mint New Device NFT'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              decoration: InputDecoration(
                labelText: 'Device ID',
                hintText: 'e.g., ESP32_ABC123',
              ),
              onChanged: (value) => deviceId = value,
            ),
            SizedBox(height: 16),
            DropdownButtonFormField<String>(
              value: deviceType,
              items: ['ESP32', 'Raspberry Pi', 'Arduino', 'Custom'].map((t) => 
                DropdownMenuItem(value: t, child: Text(t))
              ).toList(),
              onChanged: (value) => deviceType = value!,
              decoration: InputDecoration(labelText: 'Device Type'),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text('Cancel')),
          ElevatedButton(onPressed: () => Navigator.pop(context, true), child: Text('Mint NFT')),
        ],
      ),
    );

    if (result == true && deviceId != null && deviceId!.isNotEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Minting NFT for device $deviceId...')),
      );
    }
  }

  void _showDeviceDetails(DeviceNFT device) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => Container(
        padding: EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [device.tierColor, Colors.white],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Center(
                    child: Text(
                      device.deviceType == 'ESP32' ? '📡' : '🖥️',
                      style: TextStyle(fontSize: 40),
                    ),
                  ),
                ),
                SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(device.deviceType, style: Theme.of(context).textTheme.titleLarge),
                      Text('Token #${device.tokenId}', style: TextStyle(color: Colors.grey)),
                      Chip(
                        label: Text(device.tier),
                        backgroundColor: device.tierColor,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            SizedBox(height: 24),
            _buildDetailRow('Device ID', device.deviceId),
            _buildDetailRow('Registration', device.registrationDate.toString().substring(0, 10)),
            _buildDetailRow('Quality Score', '${device.qualityScore}%'),
            _buildDetailRow('Status', device.isActive ? 'Active' : 'Inactive'),
            Divider(height: 24),
            _buildDetailRow('Total Rewards', '${device.totalRewardsEarned.toStringAsFixed(2)} NWR'),
            _buildDetailRow('Data Transferred', '${device.totalDataTransferredGB.toStringAsFixed(1)} GB'),
            SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () {},
                    icon: Icon(Icons.open_in_new),
                    label: Text('View on Explorer'),
                  ),
                ),
                SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: device.isActive ? () {
                      Navigator.pop(context);
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Device deactivated')),
                      );
                    } : null,
                    icon: Icon(Icons.power_settings_new),
                    label: Text(device.isActive ? 'Deactivate' : 'Inactive'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: device.isActive ? Colors.red : Colors.grey,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(color: Colors.grey)),
          Text(value, style: TextStyle(fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: Text('Device NFTs')),
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text('🎨 Device NFTs'),
        elevation: 0,
        actions: [
          IconButton(
            icon: Icon(Icons.add),
            onPressed: _showMintDialog,
          ),
        ],
      ),
      body: Column(
        children: [
          // Stats Banner
          Container(
            padding: EdgeInsets.all(16),
            color: Theme.of(context).primaryColor.withOpacity(0.1),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildStat('Devices', _devices.length.toString()),
                _buildStat('Active', _devices.where((d) => d.isActive).length.toString()),
                _buildStat('Total Rewards', '${_totalRewards} NWR'),
              ],
            ),
          ),
          
          // Device List
          Expanded(
            child: _devices.isEmpty
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.devices, size: 64, color: Colors.grey),
                        SizedBox(height: 16),
                        Text('No device NFTs yet'),
                        SizedBox(height: 8),
                        ElevatedButton(
                          onPressed: _showMintDialog,
                          child: Text('Mint Your First Device'),
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    padding: EdgeInsets.all(16),
                    itemCount: _devices.length,
                    itemBuilder: (context, index) {
                      final device = _devices[index];
                      return Card(
                        margin: EdgeInsets.only(bottom: 12),
                        child: InkWell(
                          onTap: () => _showDeviceDetails(device),
                          borderRadius: BorderRadius.circular(12),
                          child: Padding(
                            padding: EdgeInsets.all(12),
                            child: Row(
                              children: [
                                Container(
                                  width: 60,
                                  height: 60,
                                  decoration: BoxDecoration(
                                    gradient: LinearGradient(
                                      colors: [device.tierColor, Colors.white],
                                      begin: Alignment.topLeft,
                                      end: Alignment.bottomRight,
                                    ),
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: Center(
                                    child: Text(
                                      device.deviceType == 'ESP32' ? '📡' : '🖥️',
                                      style: TextStyle(fontSize: 28),
                                    ),
                                  ),
                                ),
                                SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        children: [
                                          Text(device.deviceType, style: TextStyle(fontWeight: FontWeight.bold)),
                                          SizedBox(width: 8),
                                          Container(
                                            padding: EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                            decoration: BoxDecoration(
                                              color: device.tierColor,
                                              borderRadius: BorderRadius.circular(4),
                                            ),
                                            child: Text(device.tier, style: TextStyle(fontSize: 10)),
                                          ),
                                        ],
                                      ),
                                      Text(device.deviceId, style: TextStyle(color: Colors.grey, fontSize: 12)),
                                      SizedBox(height: 4),
                                      Row(
                                        children: [
                                          Icon(Icons.star, size: 14, color: Colors.amber),
                                          Text(' ${device.qualityScore}%', style: TextStyle(fontSize: 12)),
                                          SizedBox(width: 12),
                                          Icon(Icons.monetization_on, size: 14, color: Colors.green),
                                          Text(' ${device.totalRewardsEarned.toStringAsFixed(0)} NWR', style: TextStyle(fontSize: 12)),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                                Container(
                                  width: 8,
                                  height: 8,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: device.isActive ? Colors.green : Colors.red,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showMintDialog,
        icon: Icon(Icons.add),
        label: Text('Mint NFT'),
      ),
    );
  }

  Widget _buildStat(String label, String value) {
    return Column(
      children: [
        Text(value, style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
        Text(label, style: TextStyle(color: Colors.grey, fontSize: 12)),
      ],
    );
  }
}
