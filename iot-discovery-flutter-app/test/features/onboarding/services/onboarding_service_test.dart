import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';

import 'package:iot_discovery_app/features/onboarding/services/onboarding_service.dart';
import 'package:iot_discovery_app/core/services/analytics_service.dart';
import 'package:iot_discovery_app/core/services/notification_service.dart';
import 'package:iot_discovery_app/features/onboarding/models/onboarding_models.dart';

import 'onboarding_service_test.mocks.dart';

@GenerateMocks([AnalyticsService, NotificationService])
void main() {
  group('OnboardingService', () {
    late OnboardingService onboardingService;
    late MockAnalyticsService mockAnalyticsService;
    late MockNotificationService mockNotificationService;

    setUp(() {
      mockAnalyticsService = MockAnalyticsService();
      mockNotificationService = MockNotificationService();
      onboardingService = OnboardingService();
    });

    group('Initialization', () {
      test('should initialize successfully', () async {
        // Arrange
        when(mockAnalyticsService.initialize()).thenAnswer((_) async {});
        when(mockNotificationService.initialize()).thenAnswer((_) async {});

        // Act
        await onboardingService.initialize(
          analyticsService: mockAnalyticsService,
          notificationService: mockNotificationService,
        );

        // Assert
        expect(onboardingService.isInitialized, isTrue);
        verify(mockAnalyticsService.initialize()).called(1);
        verify(mockNotificationService.initialize()).called(1);
      });

      test('should not initialize twice', () async {
        // Arrange
        when(mockAnalyticsService.initialize()).thenAnswer((_) async {});
        when(mockNotificationService.initialize()).thenAnswer((_) async {});

        // Act
        await onboardingService.initialize(
          analyticsService: mockAnalyticsService,
          notificationService: mockNotificationService,
        );
        await onboardingService.initialize(
          analyticsService: mockAnalyticsService,
          notificationService: mockNotificationService,
        );

        // Assert
        verify(mockAnalyticsService.initialize()).called(1);
        verify(mockNotificationService.initialize()).called(1);
      });
    });

    group('Device Capture', () {
      test('should capture device successfully', () async {
        // Arrange
        await onboardingService.initialize(
          analyticsService: mockAnalyticsService,
          notificationService: mockNotificationService,
        );

        const deviceId = 'test_device_001';
        const deviceName = 'Test Smart Light';
        const deviceType = 'light';
        const deviceBrand = 'Philips';
        const deviceModel = 'Hue White';

        // Act
        final result = await onboardingService.captureDevice(
          deviceId: deviceId,
          deviceName: deviceName,
          deviceType: deviceType,
          deviceBrand: deviceBrand,
          deviceModel: deviceModel,
          deviceData: {'test': 'data'},
        );

        // Assert
        expect(result, isNotNull);
        expect(result!.deviceId, equals(deviceId));
        expect(result.deviceName, equals(deviceName));
        expect(result.deviceType, equals(deviceType));
        expect(result.deviceBrand, equals(deviceBrand));
        expect(result.deviceModel, equals(deviceModel));
        expect(result.isVerified, isTrue);
        expect(result.points, greaterThan(0));

        verify(mockAnalyticsService.trackDeviceCapture(
          deviceType,
          deviceBrand,
          any,
        )).called(1);
      });

      test('should calculate points correctly for different device types', () async {
        // Arrange
        await onboardingService.initialize(
          analyticsService: mockAnalyticsService,
          notificationService: mockNotificationService,
        );

        // Act & Assert
        final lightResult = await onboardingService.captureDevice(
          deviceId: 'light_001',
          deviceName: 'Smart Light',
          deviceType: 'light',
          deviceData: {},
        );

        final thermostatResult = await onboardingService.captureDevice(
          deviceId: 'thermostat_001',
          deviceName: 'Smart Thermostat',
          deviceType: 'thermostat',
          deviceData: {},
        );

        expect(lightResult!.points, greaterThan(0));
        expect(thermostatResult!.points, greaterThan(0));
        // Thermostats should generally give more points than lights
        expect(thermostatResult.points, greaterThanOrEqualTo(lightResult.points));
      });
    });

    group('Photo Collection', () {
      test('should collect photo successfully', () async {
        // Arrange
        await onboardingService.initialize(
          analyticsService: mockAnalyticsService,
          notificationService: mockNotificationService,
        );

        const title = 'My Smart Home';
        const description = 'A beautiful photo of my smart home setup';
        const photoType = PhotoCollectibleType.smartHome;

        // Act
        final result = await onboardingService.collectPhoto(
          title: title,
          description: description,
          type: photoType,
          photoPath: '/test/path/photo.jpg',
          tags: ['smart_home', 'automation'],
        );

        // Assert
        expect(result, isNotNull);
        expect(result!.title, equals(title));
        expect(result.description, equals(description));
        expect(result.type, equals(photoType));
        expect(result.tags, contains('smart_home'));
        expect(result.points, greaterThan(0));

        verify(mockAnalyticsService.trackPhotoCollection(
          photoType.name,
          any,
          any,
        )).called(1);
      });

      test('should calculate rarity correctly', () async {
        // Arrange
        await onboardingService.initialize(
          analyticsService: mockAnalyticsService,
          notificationService: mockNotificationService,
        );

        // Act
        final commonResult = await onboardingService.collectPhoto(
          title: 'Common Photo',
          description: 'A common photo',
          type: PhotoCollectibleType.smartHome,
          photoPath: '/test/path/common.jpg',
        );

        final rareResult = await onboardingService.collectPhoto(
          title: 'Rare Photo',
          description: 'A rare photo',
          type: PhotoCollectibleType.rareDevice,
          photoPath: '/test/path/rare.jpg',
        );

        // Assert
        expect(commonResult!.isRare, isFalse);
        expect(rareResult!.isRare, isTrue);
        expect(rareResult.points, greaterThan(commonResult.points));
      });
    });

    group('Quest Progress', () {
      test('should update quest progress successfully', () async {
        // Arrange
        await onboardingService.initialize(
          analyticsService: mockAnalyticsService,
          notificationService: mockNotificationService,
        );

        const questId = 'first_device_quest';
        const objective = 'capture_first_device';

        // Act
        await onboardingService.updateQuestProgress(
          questId: questId,
          progress: 1,
          objective: objective,
        );

        // Assert
        final progress = onboardingService.progress;
        final quest = progress.questProgress.firstWhere((q) => q.questId == questId);
        expect(quest.progress, equals(1));
        expect(quest.objectives, contains(objective));

        verify(mockAnalyticsService.trackQuestProgress(
          questId,
          'in_progress',
          1,
        )).called(1);
      });

      test('should complete quest when all objectives are met', () async {
        // Arrange
        await onboardingService.initialize(
          analyticsService: mockAnalyticsService,
          notificationService: mockNotificationService,
        );

        const questId = 'permissions_quest';

        // Act
        await onboardingService.updateQuestProgress(
          questId: questId,
          progress: 1,
          objective: 'camera_permission',
        );
        await onboardingService.updateQuestProgress(
          questId: questId,
          progress: 1,
          objective: 'location_permission',
        );

        // Assert
        final progress = onboardingService.progress;
        final quest = progress.questProgress.firstWhere((q) => q.questId == questId);
        expect(quest.status, equals(QuestStatus.completed));

        verify(mockNotificationService.showQuestCompletionNotification(
          questTitle: any,
          points: any,
        )).called(1);
      });
    });

    group('Achievement System', () {
      test('should unlock first device achievement', () async {
        // Arrange
        await onboardingService.initialize(
          analyticsService: mockAnalyticsService,
          notificationService: mockNotificationService,
        );

        // Act
        await onboardingService.captureDevice(
          deviceId: 'first_device',
          deviceName: 'First Device',
          deviceType: 'light',
          deviceData: {},
        );

        // Assert
        final progress = onboardingService.progress;
        final achievement = progress.achievements.firstWhere(
          (a) => a.id == 'first_device_achievement',
        );
        expect(achievement.isUnlocked, isTrue);

        verify(mockNotificationService.showAchievementNotification(
          achievementTitle: any,
          achievementDescription: any,
          points: any,
        )).called(1);
      });

      test('should unlock photo collector achievement', () async {
        // Arrange
        await onboardingService.initialize(
          analyticsService: mockAnalyticsService,
          notificationService: mockNotificationService,
        );

        // Act
        for (int i = 0; i < 5; i++) {
          await onboardingService.collectPhoto(
            title: 'Photo $i',
            description: 'Test photo $i',
            type: PhotoCollectibleType.smartHome,
            photoPath: '/test/path/photo$i.jpg',
          );
        }

        // Assert
        final progress = onboardingService.progress;
        final achievement = progress.achievements.firstWhere(
          (a) => a.id == 'photo_collector_achievement',
        );
        expect(achievement.isUnlocked, isTrue);
      });
    });

    group('Onboarding Completion', () {
      test('should complete onboarding successfully', () async {
        // Arrange
        await onboardingService.initialize(
          analyticsService: mockAnalyticsService,
          notificationService: mockNotificationService,
        );

        // Act
        await onboardingService.completeOnboarding();

        // Assert
        expect(onboardingService.isCompleted, isTrue);
        expect(onboardingService.progress.isCompleted, isTrue);
        expect(onboardingService.progress.completedAt, isNotNull);

        verify(mockAnalyticsService.trackOnboardingCompletion(
          totalScore: any,
          duration: any,
          devicesCaptures: any,
          photosCollected: any,
          questsCompleted: any,
          achievementsUnlocked: any,
        )).called(1);

        verify(mockNotificationService.showOnboardingCompletionNotification(
          totalScore: any,
        )).called(1);
      });
    });

    group('Score Calculation', () {
      test('should calculate total score correctly', () async {
        // Arrange
        await onboardingService.initialize(
          analyticsService: mockAnalyticsService,
          notificationService: mockNotificationService,
        );

        // Act
        await onboardingService.captureDevice(
          deviceId: 'device_1',
          deviceName: 'Device 1',
          deviceType: 'light',
          deviceData: {},
        );

        await onboardingService.collectPhoto(
          title: 'Photo 1',
          description: 'Test photo',
          type: PhotoCollectibleType.smartHome,
          photoPath: '/test/path/photo1.jpg',
        );

        // Assert
        final progress = onboardingService.progress;
        final expectedScore = progress.capturedDevices.fold<int>(
          0,
          (sum, device) => sum + device.points,
        ) + progress.collectedPhotos.fold<int>(
          0,
          (sum, photo) => sum + photo.points,
        );

        expect(progress.totalScore, equals(expectedScore));
      });
    });

    group('Persistence', () {
      test('should save and load progress correctly', () async {
        // Arrange
        await onboardingService.initialize(
          analyticsService: mockAnalyticsService,
          notificationService: mockNotificationService,
        );

        // Act
        await onboardingService.captureDevice(
          deviceId: 'test_device',
          deviceName: 'Test Device',
          deviceType: 'light',
          deviceData: {},
        );

        await onboardingService.saveProgress();

        // Create new service instance to test loading
        final newService = OnboardingService();
        await newService.initialize(
          analyticsService: mockAnalyticsService,
          notificationService: mockNotificationService,
        );

        // Assert
        expect(newService.progress.capturedDevices.length, equals(1));
        expect(newService.progress.capturedDevices.first.deviceName, equals('Test Device'));
      });
    });
  });
}
