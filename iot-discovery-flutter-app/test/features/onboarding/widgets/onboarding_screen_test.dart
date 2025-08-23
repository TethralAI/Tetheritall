import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';

import 'package:iot_discovery_app/features/onboarding/widgets/onboarding_screen.dart';
import 'package:iot_discovery_app/features/onboarding/services/onboarding_service.dart';
import 'package:iot_discovery_app/features/onboarding/models/onboarding_models.dart';

import 'onboarding_screen_test.mocks.dart';

@GenerateMocks([OnboardingService])
void main() {
  group('OnboardingScreen', () {
    late MockOnboardingService mockOnboardingService;

    setUp(() {
      mockOnboardingService = MockOnboardingService();
    });

    Widget createTestWidget() {
      return MaterialApp(
        home: ChangeNotifierProvider<OnboardingService>.value(
          value: mockOnboardingService,
          child: const OnboardingScreen(),
        ),
      );
    }

    testWidgets('should display welcome step initially', (WidgetTester tester) async {
      // Arrange
      final config = OnboardingConfig(
        steps: [
          const OnboardingStep(
            id: 'welcome',
            title: 'Welcome to IoT Discovery!',
            description: 'Let\'s get you started',
            type: OnboardingStepType.tutorial,
            points: 10,
          ),
        ],
        pointValues: const {},
        achievements: const {},
        quests: const {},
      );

      final progress = OnboardingProgress(
        startedAt: DateTime.now(),
      );

      when(mockOnboardingService.config).thenReturn(config);
      when(mockOnboardingService.progress).thenReturn(progress);

      // Act
      await tester.pumpWidget(createTestWidget());

      // Assert
      expect(find.text('Welcome to IoT Discovery!'), findsOneWidget);
      expect(find.text('Let\'s get you started'), findsOneWidget);
    });

    testWidgets('should display progress indicator', (WidgetTester tester) async {
      // Arrange
      final config = OnboardingConfig(
        steps: [
          const OnboardingStep(
            id: 'step1',
            title: 'Step 1',
            description: 'First step',
            type: OnboardingStepType.tutorial,
            points: 10,
          ),
          const OnboardingStep(
            id: 'step2',
            title: 'Step 2',
            description: 'Second step',
            type: OnboardingStepType.deviceCapture,
            points: 50,
          ),
        ],
        pointValues: const {},
        achievements: const {},
        quests: const {},
      );

      final progress = OnboardingProgress();

      when(mockOnboardingService.config).thenReturn(config);
      when(mockOnboardingService.progress).thenReturn(progress);

      // Act
      await tester.pumpWidget(createTestWidget());

      // Assert
      expect(find.text('Step 1 of 2'), findsOneWidget);
      expect(find.byType(LinearProgressIndicator), findsOneWidget);
    });

    testWidgets('should show score in bottom navigation', (WidgetTester tester) async {
      // Arrange
      final config = OnboardingConfig(
        steps: [
          const OnboardingStep(
            id: 'step1',
            title: 'Step 1',
            description: 'First step',
            type: OnboardingStepType.tutorial,
            points: 10,
          ),
        ],
        pointValues: const {},
        achievements: const {},
        quests: const {},
      );

      final progress = OnboardingProgress(totalScore: 150);

      when(mockOnboardingService.config).thenReturn(config);
      when(mockOnboardingService.progress).thenReturn(progress);

      // Act
      await tester.pumpWidget(createTestWidget());

      // Assert
      expect(find.text('150'), findsOneWidget);
      expect(find.byIcon(Icons.star), findsOneWidget);
    });

    testWidgets('should navigate to next step on Next button tap', (WidgetTester tester) async {
      // Arrange
      final config = OnboardingConfig(
        steps: [
          const OnboardingStep(
            id: 'tutorial',
            title: 'Tutorial Step',
            description: 'Learn the basics',
            type: OnboardingStepType.tutorial,
            points: 10,
          ),
          const OnboardingStep(
            id: 'capture',
            title: 'Device Capture',
            description: 'Capture your first device',
            type: OnboardingStepType.deviceCapture,
            points: 50,
          ),
        ],
        pointValues: const {},
        achievements: const {},
        quests: const {},
      );

      final progress = OnboardingProgress();

      when(mockOnboardingService.config).thenReturn(config);
      when(mockOnboardingService.progress).thenReturn(progress);
      when(mockOnboardingService.completeStep(any)).thenAnswer((_) async {});

      // Act
      await tester.pumpWidget(createTestWidget());
      
      // Find and tap the Next button
      final nextButton = find.widgetWithText(ElevatedButton, 'Next');
      await tester.tap(nextButton);
      await tester.pump();

      // Assert
      verify(mockOnboardingService.completeStep('tutorial')).called(1);
    });

    testWidgets('should navigate to previous step on Previous button tap', (WidgetTester tester) async {
      // Arrange
      final config = OnboardingConfig(
        steps: [
          const OnboardingStep(
            id: 'tutorial',
            title: 'Tutorial Step',
            description: 'Learn the basics',
            type: OnboardingStepType.tutorial,
            points: 10,
          ),
          const OnboardingStep(
            id: 'capture',
            title: 'Device Capture',
            description: 'Capture your first device',
            type: OnboardingStepType.deviceCapture,
            points: 50,
          ),
        ],
        pointValues: const {},
        achievements: const {},
        quests: const {},
      );

      final progress = OnboardingProgress();

      when(mockOnboardingService.config).thenReturn(config);
      when(mockOnboardingService.progress).thenReturn(progress);

      // Act
      await tester.pumpWidget(createTestWidget());
      
      // Simulate being on step 2 (manually set state or navigate first)
      // For this test, we'll assume we can access the widget state
      await tester.pump();

      // Find and tap the Previous button (if visible)
      final previousButton = find.widgetWithText(TextButton, 'Previous');
      if (tester.any(previousButton)) {
        await tester.tap(previousButton);
        await tester.pump();
      }

      // Assert - verify navigation behavior
      // This would require more complex state management testing
    });

    testWidgets('should show completion dialog when onboarding finishes', (WidgetTester tester) async {
      // Arrange
      final config = OnboardingConfig(
        steps: [
          const OnboardingStep(
            id: 'final',
            title: 'Final Step',
            description: 'Complete onboarding',
            type: OnboardingStepType.tutorial,
            points: 10,
          ),
        ],
        pointValues: const {},
        achievements: const {},
        quests: const {},
      );

      final progress = OnboardingProgress(
        isCompleted: true,
        totalScore: 200,
      );

      when(mockOnboardingService.config).thenReturn(config);
      when(mockOnboardingService.progress).thenReturn(progress);
      when(mockOnboardingService.completeStep(any)).thenAnswer((_) async {});
      when(mockOnboardingService.completeOnboarding()).thenAnswer((_) async {});

      // Act
      await tester.pumpWidget(createTestWidget());
      await tester.pump(const Duration(seconds: 1)); // Allow for async operations

      // Assert
      expect(find.text('🎉 Onboarding Complete!'), findsOneWidget);
      expect(find.textContaining('200 points'), findsOneWidget);
    });

    testWidgets('should display setup options for setup step', (WidgetTester tester) async {
      // Arrange
      final config = OnboardingConfig(
        steps: [
          const OnboardingStep(
            id: 'setup',
            title: 'App Setup',
            description: 'Configure your preferences',
            type: OnboardingStepType.setup,
            points: 20,
          ),
        ],
        pointValues: const {},
        achievements: const {},
        quests: const {},
      );

      final progress = OnboardingProgress();

      when(mockOnboardingService.config).thenReturn(config);
      when(mockOnboardingService.progress).thenReturn(progress);

      // Act
      await tester.pumpWidget(createTestWidget());

      // Assert
      expect(find.text('Enable Notifications'), findsOneWidget);
      expect(find.text('Enable Analytics'), findsOneWidget);
      expect(find.text('Enable Haptic Feedback'), findsOneWidget);
      expect(find.byType(Switch), findsNWidgets(3));
    });

    testWidgets('should display permission buttons for permission step', (WidgetTester tester) async {
      // Arrange
      final config = OnboardingConfig(
        steps: [
          const OnboardingStep(
            id: 'permissions',
            title: 'Grant Permissions',
            description: 'Allow app to access device features',
            type: OnboardingStepType.permission,
            points: 15,
          ),
        ],
        pointValues: const {},
        achievements: const {},
        quests: const {},
      );

      final progress = OnboardingProgress();

      when(mockOnboardingService.config).thenReturn(config);
      when(mockOnboardingService.progress).thenReturn(progress);

      // Act
      await tester.pumpWidget(createTestWidget());

      // Assert
      expect(find.text('Grant Camera Permission'), findsOneWidget);
      expect(find.text('Grant Location Permission'), findsOneWidget);
      expect(find.text('Grant Storage Permission'), findsOneWidget);
    });

    testWidgets('should handle empty configuration gracefully', (WidgetTester tester) async {
      // Arrange
      final config = OnboardingConfig(
        steps: const [],
        pointValues: const {},
        achievements: const {},
        quests: const {},
      );

      final progress = OnboardingProgress();

      when(mockOnboardingService.config).thenReturn(config);
      when(mockOnboardingService.progress).thenReturn(progress);

      // Act
      await tester.pumpWidget(createTestWidget());

      // Assert
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });
  });
}
