import 'package:flutter/material.dart';

class OnboardingScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Device Onboarding')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.device_hub, size: 80, color: Colors.blue),
            SizedBox(height: 24),
            Text('Welcome! Let\'s onboard your IoT device.', style: TextStyle(fontSize: 20)),
            SizedBox(height: 24),
            ElevatedButton(
              onPressed: () {
                // TODO: Implement onboarding logic
              },
              child: Text('Start Onboarding'),
            ),
          ],
        ),
      ),
    );
  }
}
