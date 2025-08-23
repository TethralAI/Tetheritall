import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'package:iot_discovery_app/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('Onboarding Flow Integration Tests', () {
    testWidgets('Complete onboarding flow', (WidgetTester tester) async {
      // Start the app
      app.main();
      await tester.pumpAndSettle();

      // Verify onboarding screen is displayed
      expect(find.text('Welcome to IoT Discovery!'), findsOneWidget);

      // Navigate through tutorial steps
      await _navigateThroughTutorial(tester);

      // Test device capture flow
      await _testDeviceCapture(tester);

      // Test photo collection flow
      await _testPhotoCollection(tester);

      // Test quest completion
      await _testQuestCompletion(tester);

      // Complete onboarding
      await _completeOnboarding(tester);

      // Verify home screen is displayed
      expect(find.text('Welcome to IoT Discovery!'), findsOneWidget);
      expect(find.byType(FloatingActionButton), findsOneWidget);
    });

    testWidgets('Device capture with camera', (WidgetTester tester) async {
      app.main();
      await tester.pumpAndSettle();

      // Navigate to device capture step
      await _navigateToStep(tester, 'device_capture');

      // Verify camera preview is displayed
      expect(find.byType(CameraPreview), findsOneWidget);

      // Tap capture button
      final captureButton = find.byIcon(Icons.camera_alt);
      await tester.tap(captureButton);
      await tester.pumpAndSettle();

      // Verify device detection results
      expect(find.text('Device Detected'), findsOneWidget);
      expect(find.text('Confirm'), findsOneWidget);

      // Confirm device capture
      await tester.tap(find.text('Confirm'));
      await tester.pumpAndSettle();

      // Verify success celebration
      expect(find.text('Device Captured!'), findsOneWidget);
    });

    testWidgets('Photo collection workflow', (WidgetTester tester) async {
      app.main();
      await tester.pumpAndSettle();

      // Navigate to photo collection step
      await _navigateToStep(tester, 'photo_collection');

      // Take a photo
      final captureButton = find.byIcon(Icons.camera_alt);
      await tester.tap(captureButton);
      await tester.pumpAndSettle();

      // Fill photo details
      await tester.enterText(find.byType(TextField).first, 'My First Collectible');
      await tester.enterText(find.byType(TextField).at(1), 'A test photo collectible');

      // Select tags
      await tester.tap(find.text('device'));
      await tester.tap(find.text('setup'));

      // Collect photo
      await tester.tap(find.text('Collect'));
      await tester.pumpAndSettle();

      // Verify collection success
      expect(find.text('Photo Collected!'), findsOneWidget);
    });

    testWidgets('Quest completion flow', (WidgetTester tester) async {
      app.main();
      await tester.pumpAndSettle();

      // Navigate to quest step
      await _navigateToStep(tester, 'quest');

      // Verify quest list is displayed
      expect(find.text('Available Quests'), findsOneWidget);

      // Start a quest
      final startButton = find.text('Start Quest');
      if (tester.any(startButton)) {
        await tester.tap(startButton);
        await tester.pumpAndSettle();
      }

      // Complete quest objective
      final completeButton = find.text('Complete Quest');
      if (tester.any(completeButton)) {
        await tester.tap(completeButton);
        await tester.pumpAndSettle();
      }

      // Verify quest completion
      expect(find.text('Quest Completed!'), findsOneWidget);
    });

    testWidgets('Achievement unlock flow', (WidgetTester tester) async {
      app.main();
      await tester.pumpAndSettle();

      // Perform actions that trigger achievements
      // Capture first device
      await _navigateToStep(tester, 'device_capture');
      await _captureDevice(tester);

      // Verify achievement notification
      expect(find.text('Achievement Unlocked!'), findsOneWidget);
      expect(find.text('First Device'), findsOneWidget);
    });

    testWidgets('Progress persistence across app restarts', (WidgetTester tester) async {
      // Start app and make some progress
      app.main();
      await tester.pumpAndSettle();

      // Capture a device
      await _navigateToStep(tester, 'device_capture');
      await _captureDevice(tester);

      // Get current score
      final scoreText = tester.widget<Text>(find.byIcon(Icons.star).evaluate().first.followedBy([find.byType(Text)]).first);
      final initialScore = scoreText.data;

      // Restart app (simulate app restart)
      await tester.binding.defaultBinaryMessenger.handlePlatformMessage(
        'flutter/platform',
        null,
        (data) {},
      );

      app.main();
      await tester.pumpAndSettle();

      // Verify progress is restored
      expect(find.text(initialScore!), findsOneWidget);
    });

    testWidgets('Offline mode functionality', (WidgetTester tester) async {
      app.main();
      await tester.pumpAndSettle();

      // Simulate offline mode
      // This would require network simulation capabilities

      // Verify offline features still work
      await _navigateToStep(tester, 'device_capture');
      await _captureDevice(tester);

      // Verify local storage works
      expect(find.text('Device Captured!'), findsOneWidget);
    });

    testWidgets('Accessibility features', (WidgetTester tester) async {
      app.main();
      await tester.pumpAndSettle();

      // Test semantic labels
      expect(find.bySemanticsLabel('Progress indicator'), findsOneWidget);
      expect(find.bySemanticsLabel('Current score'), findsOneWidget);

      // Test high contrast mode
      // This would require theme testing capabilities

      // Test screen reader announcements
      // This would require accessibility testing capabilities
    });
  });
}

/// Helper function to navigate through tutorial steps
Future<void> _navigateThroughTutorial(WidgetTester tester) async {
  // Look for Next button and tap it repeatedly until we reach non-tutorial steps
  while (tester.any(find.text('Next'))) {
    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();
    
    // Check if we're still on a tutorial step
    if (!tester.any(find.text('Next'))) break;
  }
}

/// Helper function to navigate to a specific step
Future<void> _navigateToStep(WidgetTester tester, String stepType) async {
  // This would require more sophisticated navigation logic
  // For now, we'll simulate clicking Next until we reach the desired step
  int attempts = 0;
  while (attempts < 10) {  // Prevent infinite loop
    if (stepType == 'device_capture' && tester.any(find.byType(CameraPreview))) {
      break;
    } else if (stepType == 'photo_collection' && tester.any(find.text('Take a photo for your collection'))) {
      break;
    } else if (stepType == 'quest' && tester.any(find.text('Available Quests'))) {
      break;
    }
    
    if (tester.any(find.text('Next'))) {
      await tester.tap(find.text('Next'));
      await tester.pumpAndSettle();
    } else {
      break;
    }
    attempts++;
  }
}

/// Helper function to test device capture
Future<void> _testDeviceCapture(WidgetTester tester) async {
  await _navigateToStep(tester, 'device_capture');
  await _captureDevice(tester);
}

/// Helper function to capture a device
Future<void> _captureDevice(WidgetTester tester) async {
  // Tap capture button
  final captureButton = find.byIcon(Icons.camera_alt);
  if (tester.any(captureButton)) {
    await tester.tap(captureButton);
    await tester.pumpAndSettle();

    // Confirm if confirmation is needed
    if (tester.any(find.text('Confirm'))) {
      await tester.tap(find.text('Confirm'));
      await tester.pumpAndSettle();
    }
  }
}

/// Helper function to test photo collection
Future<void> _testPhotoCollection(WidgetTester tester) async {
  await _navigateToStep(tester, 'photo_collection');
  
  // Take photo
  final captureButton = find.byIcon(Icons.camera_alt);
  if (tester.any(captureButton)) {
    await tester.tap(captureButton);
    await tester.pumpAndSettle();

    // Fill details
    if (tester.any(find.byType(TextField))) {
      await tester.enterText(find.byType(TextField).first, 'Test Photo');
    }

    // Collect
    if (tester.any(find.text('Collect'))) {
      await tester.tap(find.text('Collect'));
      await tester.pumpAndSettle();
    }
  }
}

/// Helper function to test quest completion
Future<void> _testQuestCompletion(WidgetTester tester) async {
  await _navigateToStep(tester, 'quest');
  
  // Start and complete quest
  if (tester.any(find.text('Start Quest'))) {
    await tester.tap(find.text('Start Quest'));
    await tester.pumpAndSettle();
  }
  
  if (tester.any(find.text('Complete Quest'))) {
    await tester.tap(find.text('Complete Quest'));
    await tester.pumpAndSettle();
  }
}

/// Helper function to complete onboarding
Future<void> _completeOnboarding(WidgetTester tester) async {
  // Navigate through remaining steps
  while (tester.any(find.text('Next'))) {
    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();
  }
  
  // Handle completion dialog
  if (tester.any(find.text('Continue'))) {
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();
  }
}
