import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:iot_visualization/iot_visualization.dart';

class SettingsService {
  SharedPreferences? _prefs;

  Future<void> init() async {
    _prefs ??= await SharedPreferences.getInstance();
  }

  double getDouble(String key, double fallback) => _prefs?.getDouble(key) ?? fallback;
  Future<void> setDouble(String key, double value) async => _prefs?.setDouble(key, value);

  bool getBool(String key, bool fallback) => _prefs?.getBool(key) ?? fallback;
  Future<void> setBool(String key, bool value) async => _prefs?.setBool(key, value);

  int getInt(String key, int fallback) => _prefs?.getInt(key) ?? fallback;
  Future<void> setInt(String key, int value) async => _prefs?.setInt(key, value);

  String getString(String key, String fallback) => _prefs?.getString(key) ?? fallback;
  Future<void> setString(String key, String value) async => _prefs?.setString(key, value);

  Color getColor(String key, Color fallback) {
    final value = _prefs?.getInt(key);
    return value == null ? fallback : Color(value);
  }

  Future<void> setColor(String key, Color value) async => _prefs?.setInt(key, value.value);

  Future<void> clearAll() async => _prefs?.clear();

  VisualizationSettings loadSettings() {
    return VisualizationSettings(
      allowance: getDouble('allowance', 1.0),
      autoSpawn: getBool('autoSpawn', true),
      enableStarfield: getBool('enableStarfield', true),
      reduceMotion: getBool('reduceMotion', false),
      showHud: getBool('showHud', true),
      targetFps: getInt('targetFps', 60),
      presetTheme: _themeFromString(getString('presetTheme', 'blue')),
      particleCount: getInt('particleCount', 6),
      maxBeams: getInt('maxBeams', 30),
      spawnMs: getInt('spawnMs', 280),
      speedScale: getDouble('speedScale', 1.0),
      perfMode: getString('perfMode', 'normal') == 'low' ? PerformanceMode.low : PerformanceMode.normal,
      hubColor: getColor('hubColor', Colors.cyan),
    );
  }

  Future<void> saveSettings(VisualizationSettings s) async {
    await setDouble('allowance', s.allowance);
    await setBool('autoSpawn', s.autoSpawn);
    await setBool('enableStarfield', s.enableStarfield);
    await setBool('reduceMotion', s.reduceMotion);
    await setBool('showHud', s.showHud);
    await setInt('targetFps', s.targetFps);
    await setString('presetTheme', _themeToString(s.presetTheme));
    await setInt('particleCount', s.particleCount);
    await setInt('maxBeams', s.maxBeams);
    await setInt('spawnMs', s.spawnMs);
    await setDouble('speedScale', s.speedScale);
    await setString('perfMode', s.perfMode == PerformanceMode.low ? 'low' : 'normal');
    await setColor('hubColor', s.hubColor);
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
}

class VisualizationSettings {
  VisualizationSettings({
    required this.allowance,
    required this.autoSpawn,
    required this.enableStarfield,
    required this.reduceMotion,
    required this.showHud,
    required this.targetFps,
    required this.presetTheme,
    required this.particleCount,
    required this.maxBeams,
    required this.spawnMs,
    required this.speedScale,
    required this.perfMode,
    required this.hubColor,
  });

  double allowance;
  bool autoSpawn;
  bool enableStarfield;
  bool reduceMotion;
  bool showHud;
  int targetFps;
  VisualizationTheme presetTheme;
  int particleCount;
  int maxBeams;
  int spawnMs;
  double speedScale;
  PerformanceMode perfMode;
  Color hubColor;
}


