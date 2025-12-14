import 'package:flutter/material.dart';
import 'widgets/device_card.dart';

class DeviceListPage extends StatelessWidget {
  final List<Map<String, String>> devices = [
    {'name': 'Sensor Node 1', 'status': 'Online'},
    {'name': 'Relay Node 2', 'status': 'Offline'},
    {'name': 'Gateway 3', 'status': 'Online'},
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Devices')),
      body: devices.isEmpty
          ? const Center(child: Text('No devices found.'))
          : ListView.builder(
              itemCount: devices.length,
              itemBuilder: (context, index) {
                final device = devices[index];
                return DeviceCard(
                  deviceName: device['name']!,
                  status: device['status']!,
                  onTap: () {
                    // TODO: Show device details
                  },
                );
              },
            ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          Navigator.pushNamed(context, '/onboarding');
        },
        icon: Icon(Icons.add),
        label: Text('Add Device'),
      ),
    );
  }
}
