import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:sensors_plus/sensors_plus.dart';
import 'package:flutter/scheduler.dart';

import '../models/data_beam.dart';
import '../models/device_location.dart';
import '../services/iot_data_service.dart';
import 'data_transmission_controller.dart';
import 'data_visualization_painter.dart';

typedef OnDataEvent = void Function(IoTDataEvent event);

class DataTransmissionVisualization extends StatefulWidget {
  const DataTransmissionVisualization({
    super.key,
    this.onDataEvent,
    this.hubColor,
    this.maxConcurrentBeams = 30,
    this.enableDirectionalMapping = false,
    this.enableStarfield = true,
    this.intensityScale = 1.0,
    this.controller,
    this.beamSpawnInterval = const Duration(milliseconds: 300),
    this.globalSpeedScale = 1.0,
    this.starfieldSeed = 1337,
    this.particleCount = 6,
    this.reduceMotion = false,
    this.colorResolver,
  });

  final OnDataEvent? onDataEvent;
  final Color? hubColor;
  final int maxConcurrentBeams;
  final bool enableDirectionalMapping;
  final bool enableStarfield;
  final double intensityScale; // 0.5..2.0
  final DataTransmissionController? controller;
  final Duration beamSpawnInterval;
  final double globalSpeedScale; // Multiplier on beam speeds
  final int starfieldSeed;
  final int particleCount; // particles per beam
  final bool reduceMotion; // reduce energy and particle count
  final Color Function({required bool isOutgoing, String? deviceId})? colorResolver;

  @override
  State<DataTransmissionVisualization> createState() => _DataTransmissionVisualizationState();
}

class _DataTransmissionVisualizationState extends State<DataTransmissionVisualization>
    with SingleTickerProviderStateMixin
    implements _Attachable {
  late final AnimationController _pulseController;
  late final Animation<double> _pulseAnimation;

  final List<DataBeam> _beams = <DataBeam>[];
  final Random _rand = Random();
  Timer? _beamTimer;
  Ticker? _ticker;
  StreamSubscription? _accelSub;

  // Orientation state
  double _deviceYaw = 0.0; // radians, from sensors

  // External data service hook
  IoTDataService? _iotService;

  // Phase for particle animation
  double _phase = 0.0;
  int? _lastTickMs;

  @override
  void initState() {
    super.initState();

    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );
    _pulseAnimation = CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut);
    _pulseController.repeat(reverse: true);

    // Beam generation timer
    _beamTimer = Timer.periodic(widget.beamSpawnInterval, (_) => _maybeSpawnBeam());

    // Smooth ticker for updates
    _ticker = createTicker((elapsed) {
      final dt = _lastTickMs == null
          ? 0.0
          : (elapsed.inMicroseconds - _lastTickMs!) / 1e6;
      _lastTickMs = elapsed.inMicroseconds;
      final double step = dt.clamp(0.0, 0.05);
      _advanceBeams(step);
      _phase = (_phase + step / 2.0) % 1.0;
      if (mounted) setState(() {});
    })..start();

    if (widget.enableDirectionalMapping) {
      _accelSub = accelerometerEvents.listen((AccelerometerEvent event) {
        // Simple mapping: compute yaw-like angle from X/Y components
        _deviceYaw = atan2(event.y, event.x);
      });
    }

    widget.controller?._attach(this);
  }

  @override
  void didUpdateWidget(covariant DataTransmissionVisualization oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.enableDirectionalMapping != widget.enableDirectionalMapping) {
      _accelSub?.cancel();
      _accelSub = null;
      if (widget.enableDirectionalMapping) {
        _accelSub = accelerometerEvents.listen((AccelerometerEvent event) {
          _deviceYaw = atan2(event.y, event.x);
        });
      }
    }

    if (oldWidget.controller != widget.controller) {
      oldWidget.controller?._detach(this);
      widget.controller?._attach(this);
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _beamTimer?.cancel();
    _ticker?.dispose();
    _accelSub?.cancel();
    _iotService?.dispose();
    widget.controller?._detach(this);
    super.dispose();
  }

  // Public integration points
  void onDataSent(String deviceId, double dataSize, DeviceLocation location) {
    _spawnBeam(isOutgoing: true, deviceId: deviceId, dataSize: dataSize, location: location);
  }

  void onDataReceived(String deviceId, double dataSize, DeviceLocation location) {
    _spawnBeam(isOutgoing: false, deviceId: deviceId, dataSize: dataSize, location: location);
  }

  void updateDevicePosition(String deviceId, DeviceLocation location) {
    // Reserved for phase 2 mapping of specific device directions
  }

  void _maybeSpawnBeam() {
    if (_beams.length >= widget.maxConcurrentBeams) return;
    final isOutgoing = _rand.nextBool();
    _spawnBeam(isOutgoing: isOutgoing);
  }

  void _spawnBeam({
    required bool isOutgoing,
    String? deviceId,
    double dataSize = 1.0,
    DeviceLocation? location,
  }) {
    final double baseIntensity = (dataSize.clamp(0.1, 10.0) / 10.0) * widget.intensityScale;
    final double intensity = baseIntensity.clamp(0.15, 1.0);

    double angle = _rand.nextDouble() * pi * 2;
    if (widget.enableDirectionalMapping && location != null) {
      // Map to device angle relative to phone yaw
      final DeviceLocation origin = const DeviceLocation(x: 0, y: 0);
      final double worldAngle = origin.angleTo(location);
      angle = worldAngle - _deviceYaw;
    }

    final defaultOutgoing = const Color(0xFF00E5FF); // cyan
    final defaultIncoming = const Color(0xFFFFA726); // amber
    final fallback = isOutgoing ? defaultOutgoing : defaultIncoming;
    final beamColor = widget.colorResolver?.call(isOutgoing: isOutgoing, deviceId: deviceId) ?? fallback;

    final beam = DataBeam(
      angleRadians: angle,
      isOutgoing: isOutgoing,
      intensity: intensity,
      // Aim for ~2s traverse: 0.5 progress/sec => 2s. Slight variance for realism.
      speed: 0.45 + _rand.nextDouble() * 0.15,
      color: beamColor,
      deviceId: deviceId,
    );

    _beams.add(beam);
  }

  void _advanceBeams(double dtSeconds) {
    for (final beam in _beams) {
      beam.progress += beam.speed * widget.globalSpeedScale * dtSeconds;
    }
    _beams.removeWhere((b) => b.isComplete);
  }

  void _manualBurst() {
    for (int i = 0; i < 8; i++) {
      _spawnBeam(isOutgoing: i.isEven);
    }
  }

  @override
  Widget build(BuildContext context) {
    final Color base = widget.hubColor ?? Colors.cyan;
    final Gradient hubGradient = RadialGradient(
      colors: [
        base.withOpacity(0.95),
        base.withOpacity(0.65),
        base.withOpacity(0.1),
      ],
      stops: const [0.0, 0.6, 1.0],
    );

    final semanticsText = 'Real-time data visualization with ${_beams.length} active beams.';
    return Stack(
      children: [
        Semantics(
          label: semanticsText,
          container: true,
          child: RepaintBoundary(
            child: SizedBox.expand(
              child: CustomPaint(
                painter: DataVisualizationPainter(
                  beams: List.unmodifiable(_beams),
                  pulseValue: _pulseAnimation.value,
                  hubGradient: hubGradient,
                  starSeed: widget.starfieldSeed,
                  showStarfield: widget.enableStarfield,
                  deviceParticlesPhase: _phase,
                  particleCount: widget.particleCount,
                  reduceMotion: widget.reduceMotion,
                ),
              ),
            ),
          ),
        ),
        Positioned(
          right: 16,
          bottom: 16,
          child: Semantics(
            label: 'Trigger data burst',
            button: true,
            child: FloatingActionButton(
              onPressed: _manualBurst,
              tooltip: 'Simulate data burst',
              child: const Icon(Icons.bolt),
            ),
          ),
        ),
      ],
    );
  }
}
