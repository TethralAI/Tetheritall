import 'package:flutter/material.dart';
import 'package:iot_visualization/iot_visualization.dart';
import 'package:shared_preferences/shared_preferences.dart';

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
  double allowance = 1.0;
  DeviceLocation lampLoc = const DeviceLocation(x: 2, y: -1);
  DeviceLocation thermoLoc = const DeviceLocation(x: -1, y: 0.5);
  bool autoSpawn = true;
  int activeBeams = 0;

  @override
  void initState() {
    super.initState();
    _loadPrefs();
  }

  Future<void> _loadPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    final savedAllowance = prefs.getDouble('allowance') ?? allowance;
    final savedAutoSpawn = prefs.getBool('autoSpawn') ?? autoSpawn;
    setState(() {
      allowance = savedAllowance;
      autoSpawn = savedAutoSpawn;
    });
    controller.setDataAllowance(allowance);
    controller.setAutoSpawnEnabled(autoSpawn);
  }

  Future<void> _saveAllowance(double v) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble('allowance', v);
  }

  Future<void> _saveAutoSpawn(bool v) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('autoSpawn', v);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Stack(
          children: [
            DataTransmissionVisualization(
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
              autoSpawnEnabled: autoSpawn,
              showHud: true,
              onStats: ({required int activeBeams, required double allowance01, required double fps}) {
                setState(() {
                  this.activeBeams = activeBeams;
                });
              },
            ),
            Positioned(
              left: 12,
              right: 12,
              bottom: 88,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text('Data allowance: ${(allowance * 100).round()}%', textAlign: TextAlign.center),
                  Slider(
                    value: allowance,
                    onChanged: (v) {
                      setState(() => allowance = v);
                      controller.setDataAllowance(v);
                      _saveAllowance(v);
                    },
                  ),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Switch(
                        value: autoSpawn,
                        onChanged: (v) {
                          setState(() => autoSpawn = v);
                          controller.setAutoSpawnEnabled(v);
                          _saveAutoSpawn(v);
                        },
                      ),
                      const SizedBox(width: 8),
                      const Text('Auto-spawn'),
                      const SizedBox(width: 16),
                      Text('Active beams: $activeBeams'),
                    ],
                  ),
                  Wrap(
                    alignment: WrapAlignment.center,
                    spacing: 8,
                    children: [
                      ElevatedButton(
                        onPressed: () {
                          controller.onDataSent('lamp-1', 2.5, lampLoc);
                        },
                        child: const Text('Send to Lamp'),
                      ),
                      ElevatedButton(
                        onPressed: () {
                          controller.onDataReceived('thermo', 1.0, thermoLoc);
                        },
                        child: const Text('Recv from Thermo'),
                      ),
                      ElevatedButton(
                        onPressed: () {
                          // Move lamp clockwise-ish
                          lampLoc = DeviceLocation(x: lampLoc.x * 0.8, y: lampLoc.y * 0.8 + 0.2);
                          controller.updateDevicePosition('lamp-1', lampLoc);
                        },
                        child: const Text('Move Lamp'),
                      ),
                      ElevatedButton(
                        onPressed: () {
                          // Move thermo counter-clockwise-ish
                          thermoLoc = DeviceLocation(x: thermoLoc.x * 0.8 - 0.2, y: thermoLoc.y * 0.8);
                          controller.updateDevicePosition('thermo', thermoLoc);
                        },
                        child: const Text('Move Thermo'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}