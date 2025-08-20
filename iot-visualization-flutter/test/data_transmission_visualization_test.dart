import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:iot_visualization/iot_visualization.dart';

void main() {
  testWidgets('widget builds and shows FAB', (tester) async {
    final controller = DataTransmissionController();
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: DataTransmissionVisualization(
            controller: controller,
            enableDirectionalMapping: false,
          ),
        ),
      ),
    );

    expect(find.byType(DataTransmissionVisualization), findsOneWidget);
    expect(find.byType(FloatingActionButton), findsOneWidget);
  });
}
