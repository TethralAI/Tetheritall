import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:iot_visualization/iot_visualization.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('benchmark: average frame under 20ms with 25 beams', (tester) async {
    final controller = DataTransmissionController();
    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData.dark(),
        home: Scaffold(
          body: DataTransmissionVisualization(
            controller: controller,
            enableDirectionalMapping: false,
            autoSpawnEnabled: false,
            maxConcurrentBeams: 30,
            particleCount: 6,
            performanceMode: PerformanceMode.low,
          ),
        ),
      ),
    );

    final rng = Random(1);
    for (int i = 0; i < 25; i++) {
      final isOutgoing = rng.nextBool();
      final loc = DeviceLocation(x: rng.nextDouble() * 5 - 2.5, y: rng.nextDouble() * 5 - 2.5);
      if (isOutgoing) {
        controller.onDataSent('d$i', 1.0 + rng.nextDouble() * 5.0, loc);
      } else {
        controller.onDataReceived('d$i', 1.0 + rng.nextDouble() * 5.0, loc);
      }
    }

    final stopwatch = Stopwatch()..start();
    int frames = 0;
    while (stopwatch.elapsedMilliseconds < 1000) {
      await tester.pump(const Duration(milliseconds: 16));
      frames++;
    }
    final avgFrameMs = stopwatch.elapsedMilliseconds / frames;
    debugPrint('Average frame: ${avgFrameMs.toStringAsFixed(2)} ms over $frames frames');

    expect(avgFrameMs, lessThan(20.0));
  });
}
