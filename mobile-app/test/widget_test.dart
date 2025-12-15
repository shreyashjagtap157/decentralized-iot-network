import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:decentralized_iot_network/main.dart';
import 'package:decentralized_iot_network/screens/bridge_screen.dart';
import 'package:decentralized_iot_network/screens/nft_screen.dart';

void main() {
  testWidgets('App smoke test', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const MyApp());

    // Verify that our app starts
    expect(find.byType(MaterialApp), findsOneWidget);
  });

  testWidgets('Bridge Screen renders correctly', (WidgetTester tester) async {
    await tester.pumpWidget(const MaterialApp(home: BridgeScreen()));

    // Verify main components are present
    expect(find.text('Bridge Tokens'), findsOneWidget);
    expect(find.text('Source Chain'), findsOneWidget);
    expect(find.byType(DropdownButtonFormField<String>), findsNWidgets(2)); // Source & Dest
  });

  testWidgets('NFT Screen renders correctly', (WidgetTester tester) async {
    await tester.pumpWidget(const MaterialApp(home: NftScreen()));

    // Verify tabs are present
    expect(find.text('My Devices'), findsOneWidget);
    expect(find.text('Marketplace'), findsOneWidget);
    
    // Verify FAB is present
    expect(find.byIcon(Icons.add), findsOneWidget);
  });
}
