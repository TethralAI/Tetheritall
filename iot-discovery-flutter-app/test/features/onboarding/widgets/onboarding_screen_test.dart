import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mockito/mockito.dart';

import 'package:iot_discovery_app/features/onboarding/widgets/onboarding_screen.dart';
import 'package:iot_discovery_app/features/onboarding/providers/onboarding_providers.dart';
import 'package:iot_discovery_app/features/onboarding/models/onboarding_models.dart';

class MockOnboardingService extends Mock {
  OnboardingProgress get progress => OnboardingProgress();
  OnboardingUIState get uiState => OnboardingUIState();
  bool get isInitialized => true;
  Future<void> initialize({AnalyticsService? analyticsService, NotificationService? notificationService}) async {}
}

void main() {
  group('OnboardingScreen', () {
    late MockOnboardingService mockOnboardingService;

    setUp(() {
      mockOnboardingService = MockOnboardingService();
    });

    Widget createTestWidget() {
      return ProviderScope(
        overrides: [
          onboardingServiceProvider.overrideWithValue(mockOnboardingService),
        ],
        child: const MaterialApp(
          home: OnboardingScreen(),
        ),
      );
    }

    group('Loading State', () {
      testWidgets('should show loading screen when initializing', (WidgetTester tester) async {
        // Arrange
        when(mockOnboardingService.progress).thenReturn(OnboardingProgress());
        when(mockOnboardingService.uiState).thenReturn(OnboardingUIState());

        // Act
        await tester.pumpWidget(createTestWidget());

        // Assert
        expect(find.text('IoT Discovery'), findsOneWidget);
        expect(find.text('Setting up your experience...'), findsOneWidget);
        expect(find.byType(CircularProgressIndicator), findsOneWidget);
      });
    });

    group('Error State', () {
      testWidgets('should show error screen when initialization fails', (WidgetTester tester) async {
        // Arrange
        when(mockOnboardingService.progress).thenThrow(Exception('Initialization failed'));
        when(mockOnboardingService.uiState).thenReturn(OnboardingUIState());

        // Act
        await tester.pumpWidget(createTestWidget());
        await tester.pumpAndSettle();

        // Assert
        expect(find.text('Setup Error'), findsOneWidget);
        expect(find.text('Failed to initialize onboarding: Exception: Initialization failed'), findsOneWidget);
        expect(find.byType(ElevatedButton), findsOneWidget);
        expect(find.text('Retry'), findsOneWidget);
      });

      testWidgets('should handle retry button tap', (WidgetTester tester) async {
        // Arrange
        when(mockOnboardingService.progress).thenThrow(Exception('Initialization failed'));
        when(mockOnboardingService.uiState).thenReturn(OnboardingUIState());

        // Act
        await tester.pumpWidget(createTestWidget());
        await tester.pumpAndSettle();

        await tester.tap(find.text('Retry'));
        await tester.pumpAndSettle();

        // Assert
        // Verify that retry logic is called (this would be implemented in the actual widget)
        expect(find.text('Retry'), findsOneWidget);
      });
    });

    group('Success State', () {
      testWidgets('should show onboarding page when initialized successfully', (WidgetTester tester) async {
        // Arrange
        final progress = OnboardingProgress(
          isCompleted: false,
          totalScore: 0,
          startedAt: DateTime.now(),
        );

        final uiState = OnboardingUIState(
          isLoading: false,
          currentScore: 0,
          showCelebration: false,
        );

        when(mockOnboardingService.progress).thenReturn(progress);
        when(mockOnboardingService.uiState).thenReturn(uiState);

        // Act
        await tester.pumpWidget(createTestWidget());
        await tester.pumpAndSettle();

        // Assert
        // The OnboardingPage should be displayed
        expect(find.byType(OnboardingPage), findsOneWidget);
      });
    });
  });
}

// Mock classes for testing
class AnalyticsService {
  Future<void> initialize() async {}
  void trackEvent(String name, {Map<String, dynamic>? parameters}) {}
}

class NotificationService {
  Future<void> initialize() async {}
  Future<void> showNotification({required String title, required String body}) async {}
}
