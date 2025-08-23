import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'package:iot_discovery_app/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('Onboarding Flow Integration Tests', () {
    testWidgets('Complete onboarding flow from start to finish', (tester) async {
      // Start the app
      app.main();
      await tester.pumpAndSettle();

      // Verify we start on the onboarding screen
      expect(find.text('IoT Discovery'), findsOneWidget);
      expect(find.text('Setting up your experience...'), findsOneWidget);

      // Wait for initialization to complete
      await tester.pumpAndSettle(const Duration(seconds: 3));

      // Verify onboarding page is displayed
      expect(find.byType(OnboardingPage), findsOneWidget);

      // Test device capture flow
      await _testDeviceCapture(tester);

      // Test photo collection flow
      await _testPhotoCollection(tester);

      // Test quest completion flow
      await _testQuestCompletion(tester);

      // Test achievement unlocking
      await _testAchievementUnlocking(tester);

      // Test onboarding completion
      await _testOnboardingCompletion(tester);
    });

    testWidgets('Onboarding with different device types', (tester) async {
      // Start the app
      app.main();
      await tester.pumpAndSettle();

      // Wait for initialization
      await tester.pumpAndSettle(const Duration(seconds: 3));

      // Test capturing different device types
      final deviceTypes = ['light', 'thermostat', 'camera', 'speaker', 'lock'];

      for (final deviceType in deviceTypes) {
        await _testSpecificDeviceCapture(tester, deviceType);
      }
    });

    testWidgets('Onboarding with photo collectibles', (tester) async {
      // Start the app
      app.main();
      await tester.pumpAndSettle();

      // Wait for initialization
      await tester.pumpAndSettle(const Duration(seconds: 3));

      // Test different photo types
      final photoTypes = [
        'smart_home',
        'device_photo',
        'achievement_photo',
        'rare_device',
        'automation_setup',
      ];

      for (final photoType in photoTypes) {
        await _testSpecificPhotoCollection(tester, photoType);
      }
    });

    testWidgets('Onboarding quest progression', (tester) async {
      // Start the app
      app.main();
      await tester.pumpAndSettle();

      // Wait for initialization
      await tester.pumpAndSettle(const Duration(seconds: 3));

      // Test quest progression
      await _testQuestProgression(tester);
    });

    testWidgets('Onboarding error handling', (tester) async {
      // Start the app
      app.main();
      await tester.pumpAndSettle();

      // Test error scenarios
      await _testErrorHandling(tester);
    });
  });
}

Future<void> _testDeviceCapture(WidgetTester tester) async {
  // Look for device capture section
  expect(find.text('Device Capture'), findsOneWidget);

  // Simulate device detection
  await tester.tap(find.text('Capture Device'));
  await tester.pumpAndSettle();

  // Verify device capture dialog or form
  expect(find.text('Device Details'), findsOneWidget);

  // Fill in device information
  await tester.enterText(find.byType(TextFormField).first, 'Smart Light Bulb');
  await tester.enterText(find.byType(TextFormField).at(1), 'Philips');
  await tester.enterText(find.byType(TextFormField).at(2), 'Hue White');

  // Submit device capture
  await tester.tap(find.text('Capture'));
  await tester.pumpAndSettle();

  // Verify success message
  expect(find.text('Device Captured!'), findsOneWidget);
  expect(find.text('+50 points'), findsOneWidget);
}

Future<void> _testPhotoCollection(WidgetTester tester) async {
  // Look for photo collection section
  expect(find.text('Photo Collectibles'), findsOneWidget);

  // Simulate photo capture
  await tester.tap(find.text('Take Photo'));
  await tester.pumpAndSettle();

  // Verify photo capture interface
  expect(find.text('Photo Details'), findsOneWidget);

  // Fill in photo information
  await tester.enterText(find.byType(TextFormField).first, 'My Smart Home');
  await tester.enterText(find.byType(TextFormField).at(1), 'Beautiful smart home setup');

  // Select photo type
  await tester.tap(find.text('Smart Home'));
  await tester.pumpAndSettle();

  // Add tags
  await tester.enterText(find.byType(TextFormField).at(2), 'smart_home, automation');

  // Submit photo collection
  await tester.tap(find.text('Collect'));
  await tester.pumpAndSettle();

  // Verify success message
  expect(find.text('Photo Collected!'), findsOneWidget);
  expect(find.text('+30 points'), findsOneWidget);
}

Future<void> _testQuestCompletion(WidgetTester tester) async {
  // Look for quests section
  expect(find.text('Quests'), findsOneWidget);

  // Find and start a quest
  await tester.tap(find.text('First Device Quest'));
  await tester.pumpAndSettle();

  // Verify quest details
  expect(find.text('Quest Details'), findsOneWidget);
  expect(find.text('Capture your first IoT device'), findsOneWidget);

  // Complete quest objective
  await tester.tap(find.text('Complete Objective'));
  await tester.pumpAndSettle();

  // Verify quest completion
  expect(find.text('Quest Completed!'), findsOneWidget);
  expect(find.text('+100 points'), findsOneWidget);
}

Future<void> _testAchievementUnlocking(WidgetTester tester) async {
  // Look for achievements section
  expect(find.text('Achievements'), findsOneWidget);

  // Verify achievement is unlocked
  expect(find.text('First Device'), findsOneWidget);
  expect(find.text('Unlocked'), findsOneWidget);

  // Verify achievement notification
  expect(find.text('Achievement Unlocked!'), findsOneWidget);
  expect(find.text('+25 points'), findsOneWidget);
}

Future<void> _testOnboardingCompletion(WidgetTester tester) async {
  // Look for completion button
  expect(find.text('Complete Onboarding'), findsOneWidget);

  // Complete onboarding
  await tester.tap(find.text('Complete Onboarding'));
  await tester.pumpAndSettle();

  // Verify completion dialog
  expect(find.text('Onboarding Complete!'), findsOneWidget);
  expect(find.text('Congratulations!'), findsOneWidget);

  // Continue to main app
  await tester.tap(find.text('Continue'));
  await tester.pumpAndSettle();

  // Verify we're now on the home screen
  expect(find.text('Welcome to IoT Discovery!'), findsOneWidget);
  expect(find.text('Discover and manage your smart devices'), findsOneWidget);
}

Future<void> _testSpecificDeviceCapture(WidgetTester tester, String deviceType) async {
  // Navigate to device capture
  await tester.tap(find.text('Capture Device'));
  await tester.pumpAndSettle();

  // Fill device information
  await tester.enterText(find.byType(TextFormField).first, 'Test $deviceType');
  await tester.enterText(find.byType(TextFormField).at(1), 'TestBrand');
  await tester.enterText(find.byType(TextFormField).at(2), 'TestModel');

  // Select device type
  await tester.tap(find.text('Device Type'));
  await tester.pumpAndSettle();
  await tester.tap(find.text(deviceType));
  await tester.pumpAndSettle();

  // Capture device
  await tester.tap(find.text('Capture'));
  await tester.pumpAndSettle();

  // Verify capture
  expect(find.text('Device Captured!'), findsOneWidget);
}

Future<void> _testSpecificPhotoCollection(WidgetTester tester, String photoType) async {
  // Navigate to photo collection
  await tester.tap(find.text('Take Photo'));
  await tester.pumpAndSettle();

  // Fill photo information
  await tester.enterText(find.byType(TextFormField).first, 'Test $photoType Photo');
  await tester.enterText(find.byType(TextFormField).at(1), 'Test description');

  // Select photo type
  await tester.tap(find.text('Photo Type'));
  await tester.pumpAndSettle();
  await tester.tap(find.text(photoType));
  await tester.pumpAndSettle();

  // Collect photo
  await tester.tap(find.text('Collect'));
  await tester.pumpAndSettle();

  // Verify collection
  expect(find.text('Photo Collected!'), findsOneWidget);
}

Future<void> _testQuestProgression(WidgetTester tester) async {
  // Check initial quest state
  expect(find.text('First Device Quest'), findsOneWidget);
  expect(find.text('0/1'), findsOneWidget);

  // Complete first objective
  await tester.tap(find.text('First Device Quest'));
  await tester.pumpAndSettle();
  await tester.tap(find.text('Capture First Device'));
  await tester.pumpAndSettle();

  // Verify progress update
  expect(find.text('1/1'), findsOneWidget);
  expect(find.text('Completed'), findsOneWidget);

  // Check next quest
  expect(find.text('Photo Collector Quest'), findsOneWidget);
  expect(find.text('0/3'), findsOneWidget);
}

Future<void> _testErrorHandling(WidgetTester tester) async {
  // Test network error simulation
  await tester.tap(find.text('Simulate Error'));
  await tester.pumpAndSettle();

  // Verify error message
  expect(find.text('Connection Error'), findsOneWidget);
  expect(find.text('Please check your internet connection'), findsOneWidget);

  // Test retry functionality
  await tester.tap(find.text('Retry'));
  await tester.pumpAndSettle();

  // Verify recovery
  expect(find.text('Connection Error'), findsNothing);
}
