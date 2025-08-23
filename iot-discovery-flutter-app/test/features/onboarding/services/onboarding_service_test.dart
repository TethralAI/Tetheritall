import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';
import 'dart:io';

import 'package:iot_discovery_app/features/onboarding/services/onboarding_service.dart';
import 'package:iot_discovery_app/features/onboarding/models/onboarding_models.dart';
import 'package:iot_discovery_app/core/services/analytics_service.dart';
import 'package:iot_discovery_app/core/services/notification_service.dart';

import 'onboarding_service_test.mocks.dart';

@GenerateMocks([AnalyticsService, NotificationService])
void main() {
  group('OnboardingService', () {
    late OnboardingService onboardingService;
    late MockAnalyticsService mockAnalytics;
    late MockNotificationService mockNotifications;

    setUp(() {
      onboardingService = OnboardingService();
      mockAnalytics = MockAnalyticsService();
      mockNotifications = MockNotificationService();
    });

    group('Initialization', () {
      test('should initialize successfully', () async {
        // Act
        await onboardingService.initialize(
          analyticsService: mockAnalytics,
          notificationService: mockNotifications,
        );

        // Assert
        expect(onboardingService.config.steps, isNotEmpty);
        expect(onboardingService.config.pointValues, isNotEmpty);
        expect(onboardingService.config.achievements, isNotEmpty);
      });

      test('should create default configuration', () async {
        // Act
        await onboardingService.initialize(
          analyticsService: mockAnalytics,
          notificationService: mockNotifications,
        );

        // Assert
        final config = onboardingService.config;
        expect(config.steps, hasLength(greaterThan(0)));
        expect(config.pointValues['device_capture'], equals(50));
        expect(config.pointValues['photo_collectible'], equals(30));
        expect(config.pointValues['quest_completion'], equals(100));
      });
    });

    group('Device Capture', () {
      test('should capture device successfully', () async {
        // Arrange
        await onboardingService.initialize(
          analyticsService: mockAnalytics,
          notificationService: mockNotifications,
        );

        // Act
        final deviceCapture = await onboardingService.captureDevice(
          deviceId: 'test_device_1',
          deviceName: 'Test Device',
          deviceType: 'smart_speaker',
          deviceBrand: 'TestBrand',
          deviceModel: 'TestModel',
          deviceData: {'verified': true, 'has_photo': true},
        );

        // Assert
        expect(deviceCapture, isNotNull);
        expect(deviceCapture!.deviceName, equals('Test Device'));
        expect(deviceCapture.deviceType, equals('smart_speaker'));
        expect(deviceCapture.points, greaterThan(0));
        expect(onboardingService.progress.capturedDevices, contains(deviceCapture));
      });

      test('should calculate correct points for device capture', () async {
        // Arrange
        await onboardingService.initialize(
          analyticsService: mockAnalytics,
          notificationService: mockNotifications,
        );

        // Act
        final deviceCapture = await onboardingService.captureDevice(
          deviceId: 'test_device_1',
          deviceName: 'Smart Speaker',
          deviceType: 'smart_speaker',
          deviceData: {'verified': true, 'has_photo': true},
        );

        // Assert
        expect(deviceCapture!.points, equals(85)); // 50 base + 25 bonus + 10 verified
      });

      test('should track analytics for device capture', () async {
        // Arrange
        await onboardingService.initialize(
          analyticsService: mockAnalytics,
          notificationService: mockNotifications,
        );

        // Act
        await onboardingService.captureDevice(
          deviceId: 'test_device_1',
          deviceName: 'Test Device',
          deviceType: 'smart_speaker',
          deviceData: {},
        );

        // Assert
        verify(mockAnalytics.trackEvent('device_captured', parameters: anyNamed('parameters')));
      });
    });

    group('Photo Collectibles', () {
      test('should collect photo successfully', () async {
        // Arrange
        await onboardingService.initialize(
          analyticsService: mockAnalytics,
          notificationService: mockNotifications,
        );

        // Create a temporary test file
        final testFile = File('test_photo.jpg');
        await testFile.writeAsBytes([1, 2, 3, 4]); // Dummy image data

        // Act
        final collectible = await onboardingService.collectPhoto(
          title: 'Test Photo',
          description: 'A test photo',
          type: PhotoCollectibleType.devicePhoto,
          photoFile: testFile,
          tags: ['test', 'device'],
        );

        // Assert
        expect(collectible, isNotNull);
        expect(collectible!.title, equals('Test Photo'));
        expect(collectible.type, equals(PhotoCollectibleType.devicePhoto));
        expect(collectible.points, greaterThan(0));
        expect(onboardingService.progress.collectedPhotos, contains(collectible));

        // Cleanup
        await testFile.delete();
      });

      test('should calculate rarity correctly', () async {
        // Arrange
        await onboardingService.initialize(
          analyticsService: mockAnalytics,
          notificationService: mockNotifications,
        );

        final testFile = File('test_photo.jpg');
        await testFile.writeAsBytes([1, 2, 3, 4]);

        // Act
        final collectible = await onboardingService.collectPhoto(
          title: 'Achievement Photo',
          description: 'A rare achievement photo',
          type: PhotoCollectibleType.achievementPhoto,
          photoFile: testFile,
          metadata: {'time_of_day': 'night', 'weather': 'special'},
        );

        // Assert
        expect(collectible!.rarity, greaterThan(0.8));
        expect(collectible.isRare, isTrue);

        // Cleanup
        await testFile.delete();
      });
    });

    group('Quest Progress', () {
      test('should update quest progress correctly', () async {
        // Arrange
        await onboardingService.initialize(
          analyticsService: mockAnalytics,
          notificationService: mockNotifications,
        );

        // Act
        await onboardingService.updateQuestProgress(
          questId: 'first_routine',
          progress: 1,
          objective: 'setup_completed',
        );

        // Assert
        final quest = onboardingService.progress.questProgress
            .firstWhere((q) => q.questId == 'first_routine');
        expect(quest.currentProgress, equals(1));
        expect(quest.status, equals(QuestStatus.completed));
        expect(quest.completedObjectives, contains('setup_completed'));
      });

      test('should complete quest when target reached', () async {
        // Arrange
        await onboardingService.initialize(
          analyticsService: mockAnalytics,
          notificationService: mockNotifications,
        );

        // Act
        await onboardingService.updateQuestProgress(
          questId: 'first_routine',
          progress: 1,
        );

        // Assert
        final quest = onboardingService.progress.questProgress
            .firstWhere((q) => q.questId == 'first_routine');
        expect(quest.status, equals(QuestStatus.completed));
        expect(quest.completedAt, isNotNull);
      });
    });

    group('Achievements', () {
      test('should unlock first device achievement', () async {
        // Arrange
        await onboardingService.initialize(
          analyticsService: mockAnalytics,
          notificationService: mockNotifications,
        );

        // Act
        await onboardingService.captureDevice(
          deviceId: 'test_device_1',
          deviceName: 'First Device',
          deviceType: 'smart_speaker',
          deviceData: {},
        );

        // Allow time for achievement checking
        await Future.delayed(const Duration(milliseconds: 100));

        // Assert
        final firstDeviceAchievement = onboardingService.config.achievements['first_device'];
        expect(firstDeviceAchievement?.isUnlocked, isTrue);
      });

      test('should unlock device master achievement after 10 devices', () async {
        // Arrange
        await onboardingService.initialize(
          analyticsService: mockAnalytics,
          notificationService: mockNotifications,
        );

        // Act - Capture 10 devices
        for (int i = 0; i < 10; i++) {
          await onboardingService.captureDevice(
            deviceId: 'test_device_$i',
            deviceName: 'Device $i',
            deviceType: 'smart_speaker',
            deviceData: {},
          );
        }

        // Allow time for achievement checking
        await Future.delayed(const Duration(milliseconds: 100));

        // Assert
        final deviceMasterAchievement = onboardingService.config.achievements['device_master'];
        expect(deviceMasterAchievement?.isUnlocked, isTrue);
      });
    });

    group('Onboarding Completion', () {
      test('should complete onboarding', () async {
        // Arrange
        await onboardingService.initialize(
          analyticsService: mockAnalytics,
          notificationService: mockNotifications,
        );

        // Act
        await onboardingService.completeOnboarding();

        // Assert
        expect(onboardingService.progress.isCompleted, isTrue);
        expect(onboardingService.progress.completedAt, isNotNull);
        verify(mockAnalytics.trackEvent('onboarding_completed', parameters: anyNamed('parameters')));
      });

      test('should track completion analytics', () async {
        // Arrange
        await onboardingService.initialize(
          analyticsService: mockAnalytics,
          notificationService: mockNotifications,
        );

        // Capture some devices and photos first
        await onboardingService.captureDevice(
          deviceId: 'test_device_1',
          deviceName: 'Test Device',
          deviceType: 'smart_speaker',
          deviceData: {},
        );

        final testFile = File('test_photo.jpg');
        await testFile.writeAsBytes([1, 2, 3, 4]);
        await onboardingService.collectPhoto(
          title: 'Test Photo',
          description: 'Test',
          type: PhotoCollectibleType.devicePhoto,
          photoFile: testFile,
        );

        // Act
        await onboardingService.completeOnboarding();

        // Assert
        verify(mockAnalytics.trackEvent('onboarding_completed', parameters: argThat(
          allOf([
            isA<Map<String, dynamic>>(),
            predicate<Map<String, dynamic>>((params) => params['devices_captured'] == 1),
            predicate<Map<String, dynamic>>((params) => params['photos_collected'] == 1),
          ]),
          named: 'parameters',
        )));

        // Cleanup
        await testFile.delete();
      });
    });

    group('Progress Reset', () {
      test('should reset progress correctly', () async {
        // Arrange
        await onboardingService.initialize(
          analyticsService: mockAnalytics,
          notificationService: mockNotifications,
        );

        // Capture a device first
        await onboardingService.captureDevice(
          deviceId: 'test_device_1',
          deviceName: 'Test Device',
          deviceType: 'smart_speaker',
          deviceData: {},
        );

        // Act
        await onboardingService.resetProgress();

        // Assert
        expect(onboardingService.progress.capturedDevices, isEmpty);
        expect(onboardingService.progress.collectedPhotos, isEmpty);
        expect(onboardingService.progress.totalScore, equals(0));
        expect(onboardingService.progress.isCompleted, isFalse);
        verify(mockAnalytics.trackEvent('onboarding_reset'));
      });
    });
  });
}
