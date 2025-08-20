import 'package:flutter/material.dart';
import 'package:iot_visualization/iot_visualization.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'settings_service.dart';
import 'settings_panel.dart';

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
  final SettingsService settingsService = SettingsService();
  VisualizationSettings settings = VisualizationSettings(
    allowance: 1.0,
    autoSpawn: true,
    enableStarfield: true,
    reduceMotion: false,
    showHud: true,
    targetFps: 60,
    presetTheme: VisualizationTheme.blue,
    particleCount: 6,
    maxBeams: 30,
    spawnMs: 280,
    speedScale: 1.0,
    perfMode: PerformanceMode.normal,
    hubColor: Colors.cyan,
  );
  DeviceLocation lampLoc = const DeviceLocation(x: 2, y: -1);
  DeviceLocation thermoLoc = const DeviceLocation(x: -1, y: 0.5);
  int activeBeams = 0;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    await settingsService.init();
    final loaded = settingsService.loadSettings();
    setState(() => settings = loaded);
    controller.setDataAllowance(settings.allowance);
    controller.setAutoSpawnEnabled(settings.autoSpawn);
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
              hubColor: settings.hubColor,
              maxConcurrentBeams: settings.maxBeams,
              enableDirectionalMapping: true,
              beamSpawnInterval: Duration(milliseconds: settings.spawnMs),
              particleCount: settings.particleCount,
              colorResolver: ({required bool isOutgoing, String? deviceId}) {
                if (deviceId == 'camera') return Colors.purpleAccent;
                return isOutgoing ? const Color(0xFF00E5FF) : const Color(0xFFFFA726);
              },
              autoSpawnEnabled: settings.autoSpawn,
              showHud: settings.showHud,
              enableStarfield: settings.enableStarfield,
              reduceMotion: settings.reduceMotion,
              targetFps: settings.targetFps,
              presetTheme: settings.presetTheme,
              globalSpeedScale: settings.speedScale,
              performanceMode: settings.perfMode,
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
                  SettingsPanel(
                    settings: settings,
                    onChanged: (newSettings) async {
                      setState(() => settings = newSettings);
                      // Apply key runtime-affecting settings immediately
                      controller.setDataAllowance(settings.allowance);
                      controller.setAutoSpawnEnabled(settings.autoSpawn);
                      await settingsService.saveSettings(settings);
                    },
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
                      // Reset is built into SettingsPanel; optionally keep extra controls here
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