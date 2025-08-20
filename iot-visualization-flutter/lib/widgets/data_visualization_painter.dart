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
  Image? _cachedImage;

  void _paintStarfield(Canvas canvas, Size size) {
    if (_cachedImage != null && _cachedSize == size) {
      final dst = Offset.zero & size;
      paintImage(canvas: canvas, rect: dst, image: _cachedImage!, fit: BoxFit.cover, filterQuality: FilterQuality.low);
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
    final picture = recorder.endRecording();
    picture.toImage(size.width.ceil(), size.height.ceil()).then((img) {
      _cachedImage = img;
      _cachedSize = size;
    });
    canvas.drawPicture(picture);
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
    final beamPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..blendMode = BlendMode.plus;
    final glowPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..blendMode = BlendMode.plus;
    for (final beam in beams) {
      final widthBase = lerpDouble(1.5, 3.5, beam.intensity)! * beam.widthScale;
      final alpha = lerpDouble(0.35, 0.9, beam.intensity)!;
      beamPaint
        ..strokeWidth = widthBase
        ..color = beam.color.withOpacity(alpha);
      glowPaint
        ..strokeWidth = widthBase * (1.0 + 0.6 * beam.glowIntensity * globalGlowScale)
        ..color = beam.color.withOpacity(0.18 * beam.intensity * beam.glowIntensity * globalGlowScale);

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

      // Draw beam core and outer glow using additive blending
      canvas.drawLine(segStart, segEnd, glowPaint);
      canvas.drawLine(segStart, segEnd, beamPaint);

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
