import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

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
}

