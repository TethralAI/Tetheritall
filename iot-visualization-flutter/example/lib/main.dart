import 'package:flutter/material.dart';
import 'package:iot_visualization/iot_visualization.dart';

void main() {
  runApp(const DemoApp());
}

class DemoApp extends StatelessWidget {
  const DemoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: const DemoScreen(),
      theme: ThemeData.dark(),
      debugShowCheckedModeBanner: false,
    );
  }
}

class DemoScreen extends StatefulWidget {
  const DemoScreen({super.key});

  @override
  State<DemoScreen> createState() => _DemoScreenState();
}

class _DemoScreenState extends State<DemoScreen> {
  final controller = DataTransmissionController();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: DataTransmissionVisualization(
          controller: controller,
          hubColor: Colors.cyan,
          maxConcurrentBeams: 30,
          enableDirectionalMapping: true,
          beamSpawnInterval: const Duration(milliseconds: 280),
          particleCount: 6,
          colorResolver: ({required bool isOutgoing, String? deviceId}) {
            if (deviceId == 'camera') return Colors.purpleAccent;
            return isOutgoing ? const Color(0xFF00E5FF) : const Color(0xFFFFA726);
          },
        ),
      ),
    );
  }
}
