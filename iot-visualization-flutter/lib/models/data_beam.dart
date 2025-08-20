import 'dart:ui';

class DataBeam {
  DataBeam({
    required double angleRadians,
    required this.isOutgoing,
    required this.intensity,
    required this.speed,
    required this.color,
    this.widthScale = 1.0,
    this.glowIntensity = 1.0,
    double? initialProgress,
    this.deviceId,
  })  : progress = initialProgress ?? 0.0,
        angleRadians = angleRadians,
        targetAngleRadians = angleRadians;

  double angleRadians; // mutable to allow live direction tracking
  double targetAngleRadians; // smoothed target for easing
  double angleVelocityRadiansPerSec = 0.0;
  final bool isOutgoing;
  final double intensity; // 0..1 visual thickness/alpha multiplier
  final double speed; // logical speed factor, progress per second
  final Color color;
  final double widthScale; // multiplies stroke width visually
  final double glowIntensity; // multiplies glow alpha/blur
  final String? deviceId;

  double progress; // 0..1 position of head along beam

  bool get isComplete => progress >= 1.0;
}
