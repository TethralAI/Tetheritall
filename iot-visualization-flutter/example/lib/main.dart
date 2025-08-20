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
  // Persisted settings
  bool enableStarfield = true;
  bool reduceMotion = false;
  bool showHud = true;
  int targetFps = 60;
  VisualizationTheme presetTheme = VisualizationTheme.blue;
  int particleCount = 6;
  int maxBeams = 30;
  int spawnMs = 280;
  double speedScale = 1.0;
  PerformanceMode perfMode = PerformanceMode.normal;

  @override
  void initState() {
    super.initState();
    _loadPrefs();
  }

  Future<void> _loadPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    final savedAllowance = prefs.getDouble('allowance') ?? allowance;
    final savedAutoSpawn = prefs.getBool('autoSpawn') ?? autoSpawn;
    enableStarfield = prefs.getBool('enableStarfield') ?? enableStarfield;
    reduceMotion = prefs.getBool('reduceMotion') ?? reduceMotion;
    showHud = prefs.getBool('showHud') ?? showHud;
    targetFps = prefs.getInt('targetFps') ?? targetFps;
    final themeStr = prefs.getString('presetTheme') ?? 'blue';
    presetTheme = _themeFromString(themeStr);
    particleCount = prefs.getInt('particleCount') ?? particleCount;
    maxBeams = prefs.getInt('maxBeams') ?? maxBeams;
    spawnMs = prefs.getInt('spawnMs') ?? spawnMs;
    speedScale = prefs.getDouble('speedScale') ?? speedScale;
    final perfStr = prefs.getString('perfMode') ?? 'normal';
    perfMode = perfStr == 'low' ? PerformanceMode.low : PerformanceMode.normal;
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

  Future<void> _saveBool(String key, bool v) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(key, v);
  }

  Future<void> _saveInt(String key, int v) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(key, v);
  }

  Future<void> _saveDouble(String key, double v) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble(key, v);
  }

  Future<void> _saveString(String key, String v) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(key, v);
  }

  VisualizationTheme _themeFromString(String name) {
    switch (name) {
      case 'green':
        return VisualizationTheme.green;
      case 'purple':
        return VisualizationTheme.purple;
      case 'orange':
        return VisualizationTheme.orange;
      case 'blue':
      default:
        return VisualizationTheme.blue;
    }
  }

  String _themeToString(VisualizationTheme theme) {
    switch (theme) {
      case VisualizationTheme.green:
        return 'green';
      case VisualizationTheme.purple:
        return 'purple';
      case VisualizationTheme.orange:
        return 'orange';
      case VisualizationTheme.blue:
      default:
        return 'blue';
    }
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
              maxConcurrentBeams: maxBeams,
              enableDirectionalMapping: true,
              beamSpawnInterval: Duration(milliseconds: spawnMs),
              particleCount: particleCount,
              colorResolver: ({required bool isOutgoing, String? deviceId}) {
                if (deviceId == 'camera') return Colors.purpleAccent;
                return isOutgoing ? const Color(0xFF00E5FF) : const Color(0xFFFFA726);
              },
              autoSpawnEnabled: autoSpawn,
              showHud: showHud,
              enableStarfield: enableStarfield,
              reduceMotion: reduceMotion,
              targetFps: targetFps,
              presetTheme: presetTheme,
              globalSpeedScale: speedScale,
              performanceMode: perfMode,
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
                  const SizedBox(height: 4),
                  Wrap(
                    alignment: WrapAlignment.center,
                    spacing: 12,
                    runSpacing: 8,
                    children: [
                      Row(mainAxisSize: MainAxisSize.min, children: [
                        const Text('HUD'),
                        Switch(
                          value: showHud,
                          onChanged: (v) {
                            setState(() => showHud = v);
                            _saveBool('showHud', v);
                          },
                        ),
                      ]),
                      Row(mainAxisSize: MainAxisSize.min, children: [
                        const Text('Starfield'),
                        Switch(
                          value: enableStarfield,
                          onChanged: (v) {
                            setState(() => enableStarfield = v);
                            _saveBool('enableStarfield', v);
                          },
                        ),
                      ]),
                      Row(mainAxisSize: MainAxisSize.min, children: [
                        const Text('Reduce motion'),
                        Switch(
                          value: reduceMotion,
                          onChanged: (v) {
                            setState(() => reduceMotion = v);
                            _saveBool('reduceMotion', v);
                          },
                        ),
                      ]),
                      Row(mainAxisSize: MainAxisSize.min, children: [
                        const Text('FPS'),
                        const SizedBox(width: 6),
                        DropdownButton<int>(
                          value: targetFps,
                          items: const [DropdownMenuItem(value: 30, child: Text('30')), DropdownMenuItem(value: 60, child: Text('60'))],
                          onChanged: (v) {
                            if (v == null) return;
                            setState(() => targetFps = v);
                            _saveInt('targetFps', v);
                          },
                        ),
                      ]),
                      Row(mainAxisSize: MainAxisSize.min, children: [
                        const Text('Theme'),
                        const SizedBox(width: 6),
                        DropdownButton<String>(
                          value: _themeToString(presetTheme),
                          items: const [
                            DropdownMenuItem(value: 'blue', child: Text('Blue')),
                            DropdownMenuItem(value: 'green', child: Text('Green')),
                            DropdownMenuItem(value: 'purple', child: Text('Purple')),
                            DropdownMenuItem(value: 'orange', child: Text('Orange')),
                          ],
                          onChanged: (v) {
                            if (v == null) return;
                            setState(() => presetTheme = _themeFromString(v));
                            _saveString('presetTheme', v);
                          },
                        ),
                      ]),
                      Row(mainAxisSize: MainAxisSize.min, children: [
                        const Text('Particles'),
                        const SizedBox(width: 6),
                        DropdownButton<int>(
                          value: particleCount,
                          items: const [2, 4, 6, 8, 10]
                              .map((e) => DropdownMenuItem(value: e, child: Text('$e')))
                              .toList(),
                          onChanged: (v) {
                            if (v == null) return;
                            setState(() => particleCount = v);
                            _saveInt('particleCount', v);
                          },
                        ),
                      ]),
                      Row(mainAxisSize: MainAxisSize.min, children: [
                        const Text('Max beams'),
                        const SizedBox(width: 6),
                        DropdownButton<int>(
                          value: maxBeams,
                          items: const [10, 20, 30, 40, 50]
                              .map((e) => DropdownMenuItem(value: e, child: Text('$e')))
                              .toList(),
                          onChanged: (v) {
                            if (v == null) return;
                            setState(() => maxBeams = v);
                            _saveInt('maxBeams', v);
                          },
                        ),
                      ]),
                      Row(mainAxisSize: MainAxisSize.min, children: [
                        const Text('Spawn ms'),
                        const SizedBox(width: 6),
                        DropdownButton<int>(
                          value: spawnMs,
                          items: const [200, 280, 350, 450, 600]
                              .map((e) => DropdownMenuItem(value: e, child: Text('$e')))
                              .toList(),
                          onChanged: (v) {
                            if (v == null) return;
                            setState(() => spawnMs = v);
                            _saveInt('spawnMs', v);
                          },
                        ),
                      ]),
                      Row(mainAxisSize: MainAxisSize.min, children: [
                        const Text('Speed'),
                        const SizedBox(width: 6),
                        DropdownButton<double>(
                          value: double.parse(speedScale.toStringAsFixed(1)),
                          items: const [0.5, 0.8, 1.0, 1.2, 1.5, 2.0]
                              .map((e) => DropdownMenuItem(value: e, child: Text(e.toString())))
                              .toList(),
                          onChanged: (v) {
                            if (v == null) return;
                            setState(() => speedScale = v);
                            _saveDouble('speedScale', v);
                          },
                        ),
                      ]),
                      Row(mainAxisSize: MainAxisSize.min, children: [
                        const Text('Perf'),
                        const SizedBox(width: 6),
                        DropdownButton<String>(
                          value: perfMode == PerformanceMode.low ? 'low' : 'normal',
                          items: const [
                            DropdownMenuItem(value: 'normal', child: Text('Normal')),
                            DropdownMenuItem(value: 'low', child: Text('Low')),
                          ],
                          onChanged: (v) {
                            if (v == null) return;
                            setState(() => perfMode = v == 'low' ? PerformanceMode.low : PerformanceMode.normal);
                            _saveString('perfMode', v);
                          },
                        ),
                      ]),
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