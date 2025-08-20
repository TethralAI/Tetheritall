import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:iot_visualization/iot_visualization.dart';

void main() {
  testWidgets('golden - initial frame', (tester) async {
    final controller = DataTransmissionController();
    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData.dark(),
        home: Scaffold(
          body: SizedBox(
            width: 400,
            height: 300,
            child: DataTransmissionVisualization(
              controller: controller,
              enableDirectionalMapping: false,
              enableStarfield: true,
              autoSpawnEnabled: false,
              starfieldSeed: 42,
              particleCount: 4,
            ),
          ),
        ),
      ),
    );
    await expectLater(
      find.byType(DataTransmissionVisualization),
      matchesGoldenFile('goldens/initial.png'),
    );
  });
}
