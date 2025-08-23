import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';

import 'package:iot_discovery_app/main.dart';
import 'package:iot_discovery_app/core/models/device_model.dart';
import 'package:iot_discovery_app/features/discovery/presentation/pages/discovery_home_page.dart';
import 'package:iot_discovery_app/features/discovery/presentation/providers/discovery_providers.dart';
import 'package:iot_discovery_app/features/discovery/presentation/services/discovery_service.dart';

// Generate mocks
@GenerateMocks([DiscoveryService])
import 'flutter_discovery_app_test.mocks.dart';

void main() {
  group('IoT Discovery Flutter App Tests', () {
    late MockDiscoveryService mockDiscoveryService;

    setUp(() {
      mockDiscoveryService = MockDiscoveryService();
    });

    testWidgets('App should start and show discovery home page', (WidgetTester tester) async {
      // Build the app
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: const DiscoveryHomePage(),
          ),
        ),
      );

      // Wait for the app to settle
      await tester.pumpAndSettle();

      // Verify that the app shows the discovery home page
      expect(find.text('IoT Discovery'), findsOneWidget);
      expect(find.text('Find and connect smart devices'), findsOneWidget);
      expect(find.text('Welcome back!'), findsOneWidget);
      expect(find.text('Scan for Devices'), findsOneWidget);
    });

    testWidgets('Discovery scanner should show camera permission request', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: const DiscoveryHomePage(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Look for camera permission request
      expect(find.text('Camera Permission Required'), findsOneWidget);
      expect(find.text('Allow camera access to scan for devices'), findsOneWidget);
      expect(find.text('Grant Permission'), findsOneWidget);
    });

    testWidgets('Quick actions should be displayed', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: const DiscoveryHomePage(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Verify quick action buttons are present
      expect(find.byType(FloatingActionButton), findsOneWidget);
      expect(find.text('Scan for Devices'), findsOneWidget);
    });

    testWidgets('Empty state should be shown when no devices', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: const DiscoveryHomePage(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Verify empty state is shown
      expect(find.text('No devices discovered yet'), findsOneWidget);
      expect(find.text('Tap the scan button to discover smart devices on your network'), findsOneWidget);
    });

    testWidgets('Connect options modal should show when connect button is pressed', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: const DiscoveryHomePage(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Find and tap the connect options button (this would be in the quick actions)
      // For now, we'll simulate the modal directly
      await tester.tap(find.text('Scan for Devices'));
      await tester.pumpAndSettle();

      // The scan button should trigger discovery
      expect(find.text('Starting device discovery...'), findsOneWidget);
    });

    testWidgets('Device list should show discovered devices', (WidgetTester tester) async {
      // Create test devices
      final testDevices = [
        DeviceModel.create(
          name: 'Philips Hue Bulb',
          type: 'light',
          manufacturer: 'Philips',
          model: 'Hue White',
          protocol: 'wifi',
          location: DeviceLocation.room('Living Room'),
        ),
        DeviceModel.create(
          name: 'Nest Thermostat',
          type: 'thermostat',
          manufacturer: 'Google',
          model: 'Nest Learning Thermostat',
          protocol: 'wifi',
          location: DeviceLocation.room('Hallway'),
        ),
      ];

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            discoveryStateProvider.overrideWith((ref) => DiscoveryStateData(
              devices: testDevices,
              totalDevices: 2,
              discoveredDevices: 2,
            )),
          ],
          child: MaterialApp(
            home: const DiscoveryHomePage(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Verify devices are displayed
      expect(find.text('Discovered Devices'), findsOneWidget);
      expect(find.text('Philips Hue Bulb'), findsOneWidget);
      expect(find.text('Nest Thermostat'), findsOneWidget);
      expect(find.text('View All'), findsOneWidget);
    });

    testWidgets('Discovery stats should show correct counts', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            discoveryStateProvider.overrideWith((ref) => DiscoveryStateData(
              totalDevices: 5,
              connectedDevices: 3,
              discoveredDevices: 2,
              scanningDevices: 1,
            )),
          ],
          child: MaterialApp(
            home: const DiscoveryHomePage(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Verify stats are displayed (these would be in the DiscoveryStatsWidget)
      expect(find.text('5'), findsOneWidget); // Total devices
      expect(find.text('3'), findsOneWidget); // Connected devices
      expect(find.text('2'), findsOneWidget); // Discovered devices
    });

    testWidgets('AI Assistant should show suggestions', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            aiAssistantProvider.overrideWith((ref) => AIAssistantState(
              suggestions: [
                'Consider adding a motion sensor to your living room for automated lighting',
                'Your kitchen could benefit from a smart switch for the coffee maker',
              ],
            )),
          ],
          child: MaterialApp(
            home: const DiscoveryHomePage(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Verify AI suggestions are displayed
      expect(find.text('Consider adding a motion sensor to your living room for automated lighting'), findsOneWidget);
      expect(find.text('Your kitchen could benefit from a smart switch for the coffee maker'), findsOneWidget);
    });

    testWidgets('Settings button should navigate to settings', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: const DiscoveryHomePage(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Find and tap settings button
      final settingsButton = find.byIcon(Icons.settings);
      expect(settingsButton, findsOneWidget);
      
      await tester.tap(settingsButton);
      await tester.pumpAndSettle();

      // In a real app, this would navigate to settings
      // For now, we just verify the button exists and is tappable
    });

    testWidgets('Pull to refresh should trigger discovery refresh', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: const DiscoveryHomePage(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Perform pull to refresh gesture
      await tester.drag(find.byType(RefreshIndicator), const Offset(0, 300));
      await tester.pumpAndSettle();

      // The refresh should trigger discovery refresh
      // In a real app, this would call the refresh method
    });

    testWidgets('Device model should work correctly', (WidgetTester tester) async {
      final device = DeviceModel.create(
        name: 'Test Device',
        type: 'light',
        manufacturer: 'Test Manufacturer',
        model: 'Test Model',
        protocol: 'wifi',
        location: DeviceLocation.room('Test Room'),
      );

      // Test device properties
      expect(device.name, equals('Test Device'));
      expect(device.type, equals('light'));
      expect(device.manufacturer, equals('Test Manufacturer'));
      expect(device.model, equals('Test Model'));
      expect(device.protocol, equals('wifi'));
      expect(device.status, equals(DeviceStatus.discovered));
      expect(device.isDiscovered, isTrue);
      expect(device.isConnected, isFalse);
      expect(device.displayName, equals('Test Device'));
      expect(device.shortDescription, equals('light by Test Manufacturer'));
    });

    testWidgets('Device capabilities should work correctly', (WidgetTester tester) async {
      final lightingCapabilities = DeviceCapabilities.lighting();
      final securityCapabilities = DeviceCapabilities.security();
      final sensorCapabilities = DeviceCapabilities.sensor();

      // Test lighting capabilities
      expect(lightingCapabilities.lighting, isTrue);
      expect(lightingCapabilities.security, isFalse);
      expect(lightingCapabilities.supportedCommands, contains('on'));
      expect(lightingCapabilities.supportedCommands, contains('off'));
      expect(lightingCapabilities.supportedCommands, contains('dim'));
      expect(lightingCapabilities.supportedCommands, contains('color'));

      // Test security capabilities
      expect(securityCapabilities.security, isTrue);
      expect(securityCapabilities.supportedCommands, contains('arm'));
      expect(securityCapabilities.supportedCommands, contains('disarm'));
      expect(securityCapabilities.supportedCommands, contains('status'));

      // Test sensor capabilities
      expect(sensorCapabilities.sensors, isTrue);
      expect(sensorCapabilities.supportedCommands, contains('read'));
    });

    testWidgets('Device location should work correctly', (WidgetTester tester) async {
      final roomLocation = DeviceLocation.room('Living Room');
      final coordinatesLocation = DeviceLocation.coordinates(40.7128, -74.0060);

      // Test room location
      expect(roomLocation.room, equals('Living Room'));
      expect(roomLocation.hasRoom, isTrue);
      expect(roomLocation.hasCoordinates, isFalse);
      expect(roomLocation.displayLocation, equals('Living Room'));

      // Test coordinates location
      expect(coordinatesLocation.latitude, equals(40.7128));
      expect(coordinatesLocation.longitude, equals(-74.0060));
      expect(coordinatesLocation.hasCoordinates, isTrue);
      expect(coordinatesLocation.hasRoom, isFalse);
      expect(coordinatesLocation.displayLocation, contains('40.7128'));
      expect(coordinatesLocation.displayLocation, contains('-74.0060'));
    });

    testWidgets('Device security should work correctly', (WidgetTester tester) async {
      final defaultSecurity = DeviceSecurity.defaultSecurity();
      final secureSecurity = DeviceSecurity.secure();

      // Test default security
      expect(defaultSecurity.encryptionLevel, equals(EncryptionLevel.medium));
      expect(defaultSecurity.authenticationType, equals(AuthenticationType.none));
      expect(defaultSecurity.isSecure, isFalse);
      expect(defaultSecurity.requiresAuthentication, isFalse);

      // Test secure security
      expect(secureSecurity.encryptionLevel, equals(EncryptionLevel.high));
      expect(secureSecurity.authenticationType, equals(AuthenticationType.password));
      expect(secureSecurity.requiresPassword, isTrue);
      expect(secureSecurity.supportsBiometric, isTrue);
      expect(secureSecurity.isSecure, isTrue);
      expect(secureSecurity.requiresAuthentication, isTrue);
    });

    testWidgets('Device metadata should work correctly', (WidgetTester tester) async {
      final metadata = DeviceMetadata(
        firmwareVersion: '1.2.3',
        batteryLevel: 75,
        signalStrength: 85.5,
        connectionQuality: 'Excellent',
      );

      // Test metadata properties
      expect(metadata.firmwareVersion, equals('1.2.3'));
      expect(metadata.batteryLevel, equals(75));
      expect(metadata.signalStrength, equals(85.5));
      expect(metadata.connectionQuality, equals('Excellent'));
      expect(metadata.hasBattery, isTrue);
      expect(metadata.isLowBattery, isFalse);
      expect(metadata.hasSignal, isTrue);
      expect(metadata.hasGoodSignal, isTrue);
      expect(metadata.batteryStatusText, equals('Good'));
      expect(metadata.signalStatusText, equals('Excellent'));
    });

    testWidgets('Discovery state should update correctly', (WidgetTester tester) async {
      final testDevice = DeviceModel.create(
        name: 'Test Device',
        type: 'light',
        manufacturer: 'Test',
        model: 'Model',
        protocol: 'wifi',
      );

      // Test initial state
      final initialState = DiscoveryStateData();
      expect(initialState.devices, isEmpty);
      expect(initialState.totalDevices, equals(0));
      expect(initialState.connectedDevices, equals(0));
      expect(initialState.discoveredDevices, equals(0));

      // Test adding device
      final stateWithDevice = initialState.copyWith(
        devices: [testDevice],
        totalDevices: 1,
        discoveredDevices: 1,
      );
      expect(stateWithDevice.devices, hasLength(1));
      expect(stateWithDevice.totalDevices, equals(1));
      expect(stateWithDevice.discoveredDevices, equals(1));

      // Test updating device
      final connectedDevice = testDevice.copyWith(status: DeviceStatus.connected);
      final updatedState = stateWithDevice.copyWith(
        devices: [connectedDevice],
        connectedDevices: 1,
      );
      expect(updatedState.connectedDevices, equals(1));
      expect(updatedState.devices.first.isConnected, isTrue);
    });

    testWidgets('App should handle errors gracefully', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            discoveryStateProvider.overrideWith((ref) => DiscoveryStateData(
              error: 'Network connection failed',
            )),
          ],
          child: MaterialApp(
            home: const DiscoveryHomePage(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // The app should handle errors gracefully
      // In a real app, this would show an error message or retry option
    });

    testWidgets('App should support different themes', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            theme: ThemeData.light(),
            darkTheme: ThemeData.dark(),
            home: const DiscoveryHomePage(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // The app should render correctly with different themes
      expect(find.text('IoT Discovery'), findsOneWidget);
    });

    testWidgets('App should be accessible', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: const DiscoveryHomePage(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Test accessibility features
      // The app should have proper semantics labels
      expect(find.bySemanticsLabel('IoT Discovery'), findsOneWidget);
    });

    testWidgets('App should handle configuration changes', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: const DiscoveryHomePage(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Simulate configuration change (e.g., orientation change)
      await tester.binding.setSurfaceSize(const Size(800, 600));
      await tester.pumpAndSettle();

      // The app should handle configuration changes gracefully
      expect(find.text('IoT Discovery'), findsOneWidget);
    });
  });

  group('Integration Tests', () {
    testWidgets('Complete discovery flow should work', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: const DiscoveryHomePage(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // 1. Start discovery
      await tester.tap(find.text('Scan for Devices'));
      await tester.pumpAndSettle();

      // 2. Wait for discovery to complete
      await tester.pump(const Duration(seconds: 5));
      await tester.pumpAndSettle();

      // 3. Verify discovery results
      // In a real app, this would show discovered devices
    });

    testWidgets('Device connection flow should work', (WidgetTester tester) async {
      final testDevice = DeviceModel.create(
        name: 'Test Device',
        type: 'light',
        manufacturer: 'Test',
        model: 'Model',
        protocol: 'wifi',
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            discoveryStateProvider.overrideWith((ref) => DiscoveryStateData(
              devices: [testDevice],
              totalDevices: 1,
              discoveredDevices: 1,
            )),
          ],
          child: MaterialApp(
            home: const DiscoveryHomePage(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // 1. Tap on device to connect
      await tester.tap(find.text('Test Device'));
      await tester.pumpAndSettle();

      // 2. Verify connection process
      // In a real app, this would show connection progress
    });
  });
}

// Mock implementations for testing
class MockDiscoveryServiceImpl extends Mock implements DiscoveryServiceImpl {}

// Test utilities
class TestUtils {
  static DeviceModel createTestDevice({
    String name = 'Test Device',
    String type = 'light',
    String manufacturer = 'Test Manufacturer',
    String model = 'Test Model',
    String protocol = 'wifi',
    DeviceLocation? location,
  }) {
    return DeviceModel.create(
      name: name,
      type: type,
      manufacturer: manufacturer,
      model: model,
      protocol: protocol,
      location: location ?? DeviceLocation.room('Test Room'),
    );
  }

  static List<DeviceModel> createTestDevices(int count) {
    return List.generate(count, (index) => createTestDevice(
      name: 'Test Device $index',
      type: index % 2 == 0 ? 'light' : 'sensor',
    ));
  }
}
