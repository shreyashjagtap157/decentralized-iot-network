import 'package:flutter/material.dart';

class DeviceCard extends StatelessWidget {
  final String deviceName;
  final String status;
  final VoidCallback? onTap;

  const DeviceCard({
    required this.deviceName,
    required this.status,
    this.onTap,
    Key? key,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: Icon(Icons.devices),
        title: Text(deviceName),
        subtitle: Text('Status: $status'),
        trailing: Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}
