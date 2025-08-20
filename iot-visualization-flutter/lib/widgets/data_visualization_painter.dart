import 'dart:math';
import 'dart:ui';

import 'package:flutter/material.dart';

import '../models/data_beam.dart';

class DataVisualizationPainter extends CustomPainter {
  DataVisualizationPainter({
    required this.beams,
    required this.pulseValue,
    required this.hubGradient,
    required this.starSeed,
    required this.showStarfield,
    required this.deviceParticlesPhase,
    required this.particleCount,
    required this.reduceMotion,
    required this.particleSizeRange,
    required this.particleBlurRadius,
    required this.starCount,
    required this.globalGlowScale,
  });

  final List<DataBeam> beams;
  final double pulseValue; // 0..1
  final Gradient hubGradient;
  final int starSeed;
  final bool showStarfield;
  final double deviceParticlesPhase; // 0..1 to animate particles
  final int particleCount;
  final bool reduceMotion;
  final Size particleSizeRange;
  final double particleBlurRadius;
  final int starCount;
  final double globalGlowScale;

  @override
  void paint(Canvas canvas, Size size) {
    // Dark space background
    _paintBackground(canvas, size);
    final center = Offset(size.width / 2, size.height / 2);
    final radius = min(size.width, size.height) * 0.12 * lerpDouble(0.95, 1.08, pulseValue)!;

    if (showStarfield) {
      _paintStarfield(canvas, size);
    }

    _paintHub(canvas, center, radius);
    _paintBeams(canvas, center, radius, size);
  }

  void _paintBackground(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final bgPaint = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [Color(0xFF0B132B), Color(0xFF0A0F1F)],
      ).createShader(rect);
    canvas.drawRect(rect, bgPaint);
  }

  Picture? _cachedStars;
  Size? _cachedSize;

  void _paintStarfield(Canvas canvas, Size size) {
    if (_cachedStars != null && _cachedSize == size) {
      canvas.drawPicture(_cachedStars!);
      return;
    }
    final recorder = PictureRecorder();
    final starCanvas = Canvas(recorder);
    final rand = Random(starSeed);
    final starCount = this.starCount;
    final paint = Paint()..color = Colors.white.withOpacity(0.7);
    for (var i = 0; i < starCount; i++) {
      final x = rand.nextDouble() * size.width;
      final y = rand.nextDouble() * size.height;
      final r = rand.nextDouble() * 1.2 + 0.2;
      paint.color = Colors.white.withOpacity(0.4 + rand.nextDouble() * 0.4);
      starCanvas.drawCircle(Offset(x, y), r, paint);
    }
    _cachedStars = recorder.endRecording();
    _cachedSize = size;
    canvas.drawPicture(_cachedStars!);
  }

  void _paintHub(Canvas canvas, Offset center, double radius) {
    final rect = Rect.fromCircle(center: center, radius: radius);
    final fillPaint = Paint()
      ..shader = hubGradient.createShader(rect)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 18);
    canvas.drawCircle(center, radius, fillPaint);

    final haloPaint = Paint()
      ..color = Colors.white.withOpacity(0.15)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 28);
    canvas.drawCircle(center, radius * 1.6, haloPaint);
  }

  void _paintBeams(Canvas canvas, Offset center, double hubRadius, Size size) {
    final maxRadius = sqrt(size.width * size.width + size.height * size.height) / 2;
    for (final beam in beams) {
      final widthBase = lerpDouble(1.5, 3.5, beam.intensity)! * beam.widthScale;
      final huePaint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round
        ..strokeWidth = widthBase
        ..color = beam.color.withOpacity(lerpDouble(0.35, 0.9, beam.intensity)!);

      final angle = beam.angleRadians;
      final dir = Offset(cos(angle), sin(angle));

      final start = center + dir * hubRadius;
      final end = center + dir * maxRadius;
      final total = end - start;
      final clampedProgress = beam.progress.clamp(0.0, 1.0);

      Offset segStart;
      Offset segEnd;
      if (beam.isOutgoing) {
        segStart = start;
        segEnd = start + total * clampedProgress;
      } else {
        segStart = end - total * clampedProgress;
        segEnd = start;
      }

      final path = Path()
        ..moveTo(segStart.dx, segStart.dy)
        ..lineTo(segEnd.dx, segEnd.dy);

      // Draw gradient-like core by overdrawing multiple times with varying alpha
      for (int i = 0; i < 3; i++) {
        final t = i / 2.0;
        final glow = beam.glowIntensity * globalGlowScale;
        final alpha = (0.22 - t * 0.08) * beam.intensity * glow;
        final pw = huePaint.strokeWidth * (1.0 + t * 0.7 * glow);
        final p = Paint()
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round
          ..strokeWidth = pw
          ..color = beam.color.withOpacity(alpha.clamp(0.0, 1.0));
        canvas.drawPath(path, p);
      }

      // Particles traveling along the beam, constrained by head position
      final count = reduceMotion ? max(2, (particleCount / 2).floor()) : particleCount;
      for (int i = 0; i < count; i++) {
        final base = (i / particleCount + deviceParticlesPhase) % 1.0;
        final along = beam.isOutgoing ? base : (1 - base);
        if (along > clampedProgress) continue; // do not render beyond head
        final particlePos = Offset.lerp(start, end, along)!;
        final fade = beam.isOutgoing ? (1 - along) : along;
        final particlePaint = Paint()
          ..color = beam.color.withOpacity(0.25 + 0.5 * fade)
          ..maskFilter = MaskFilter.blur(BlurStyle.normal, particleBlurRadius);
        final radiusMin = particleSizeRange.width;
        final radiusMax = particleSizeRange.height;
        final radius = radiusMin + (radiusMax - radiusMin) * fade;
        canvas.drawCircle(particlePos, radius, particlePaint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant DataVisualizationPainter oldDelegate) {
    return oldDelegate.beams != beams ||
        oldDelegate.pulseValue != pulseValue ||
        oldDelegate.hubGradient != hubGradient ||
        oldDelegate.starSeed != starSeed ||
        oldDelegate.showStarfield != showStarfield ||
        oldDelegate.deviceParticlesPhase != deviceParticlesPhase ||
        oldDelegate.particleCount != particleCount ||
        oldDelegate.reduceMotion != reduceMotion;
  }
}
