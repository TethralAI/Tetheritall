import 'dart:ui';

class DataBeam {
  DataBeam({
    required this.angleRadians,
    required this.isOutgoing,
    required this.intensity,
    required this.speed,
    required this.color,
    double? initialProgress,
    this.deviceId,
  }) : progress = initialProgress ?? 0.0;

  final double angleRadians; // 0 rad points to +X; increases counter-clockwise
  final bool isOutgoing;
  final double intensity; // 0..1 visual thickness/alpha multiplier
  final double speed; // logical speed factor, progress per second
  final Color color;
  final String? deviceId;

  double progress; // 0..1 position of head along beam

  bool get isComplete => progress >= 1.0;
}
