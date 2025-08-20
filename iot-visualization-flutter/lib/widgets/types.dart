import 'package:flutter/material.dart';

enum VisualizationTheme { blue, green, purple, orange }

enum PerformanceMode { normal, low }

class BeamStyle {
  const BeamStyle({
    required this.color,
    this.widthScale = 1.0,
    this.glowIntensity = 1.0,
  });

  final Color color;
  final double widthScale; // multiply base stroke width
  final double glowIntensity; // multiply blur/alpha for glow
}
