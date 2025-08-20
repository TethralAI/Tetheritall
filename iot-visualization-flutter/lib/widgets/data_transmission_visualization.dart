import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:sensors_plus/sensors_plus.dart';
import 'package:flutter/scheduler.dart';
import 'package:visibility_detector/visibility_detector.dart';

import '../models/data_beam.dart';
import '../models/device_location.dart';
import '../services/iot_data_service.dart';
import 'data_transmission_controller.dart';
import 'data_visualization_painter.dart';
import 'types.dart';

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
    this.autoSpawnEnabled = true,
    this.targetFps = 60,
    this.hubGradient,
    this.presetTheme = VisualizationTheme.blue,
    this.semanticsLabel,
    this.particleSizeRange = const Size(1.6, 3.0),
    this.particleBlurRadius = 3.0,
    this.performanceMode = PerformanceMode.normal,
    this.manualYawRadians,
    this.beamStyleResolver,
    this.onStats,
    this.showHud = false,
    this.hudTextStyle,
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
  final bool autoSpawnEnabled;
  final int targetFps; // 60 / 30
  final Gradient? hubGradient;
  final VisualizationTheme presetTheme;
  final String? semanticsLabel;
  final Size particleSizeRange;
  final double particleBlurRadius;
  final PerformanceMode performanceMode;
  final double? manualYawRadians;
  final BeamStyle Function({required bool isOutgoing, String? deviceId})? beamStyleResolver;
  final void Function({required int activeBeams, required double allowance01, required double fps})? onStats;
  final bool showHud;
  final TextStyle? hudTextStyle;

  @override
  State<DataTransmissionVisualization> createState() => _DataTransmissionVisualizationState();
}

class _DataTransmissionVisualizationState extends State<DataTransmissionVisualization>
    with SingleTickerProviderStateMixin, WidgetsBindingObserver
    implements _Attachable {
  late final AnimationController _pulseController;
  late final Animation<double> _pulseAnimation;

  final List<DataBeam> _beams = <DataBeam>[];
  final Random _rand = Random();
  Timer? _beamTimer;
  Ticker? _ticker;
  StreamSubscription? _accelSub;
  StreamSubscription? _magSub;

  // Orientation state
  double _deviceYaw = 0.0; // radians, from sensors

  // External data service hook
  IoTDataService? _iotService;

  // Phase for particle animation
  double _phase = 0.0;
  int? _lastTickMs;
  double _smoothedYaw = 0.0;
  double _targetFrameIntervalMs = 1000 / 60;
  bool _isVisible = true;
  final Map<String, DeviceLocation> _devicePositions = <String, DeviceLocation>{};
  double _dataAllowance01 = 1.0; // 0..1 user-adjusted allowance
  bool _autoSpawnEnabledOverride;
  double _fpsEma = 0.0;

  @override
  void initState() {
    super.initState();
    _autoSpawnEnabledOverride = widget.autoSpawnEnabled;
    WidgetsBinding.instance.addObserver(this);

    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );
    _pulseAnimation = CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut);
    _pulseController.repeat(reverse: true);

    // Beam generation timer
    if (_shouldAutoSpawn) {
      _beamTimer = Timer.periodic(_effectiveSpawnInterval, (_) => _maybeSpawnBeam());
    }

    // Smooth ticker for updates
    _ticker = createTicker((elapsed) {
      final dt = _lastTickMs == null
          ? 0.0
          : (elapsed.inMicroseconds - _lastTickMs!) / 1e6;
      _lastTickMs = elapsed.inMicroseconds;
      final double step = dt.clamp(0.0, 0.05);
      if (step > 0) {
        final instFps = 1.0 / step;
        _fpsEma = _fpsEma == 0.0 ? instFps : (_fpsEma * 0.9 + instFps * 0.1);
      }
      _advanceBeams(step);
      _phase = (_phase + step / 2.0) % 1.0;
      if (mounted) setState(() {});
    })..start();

    if (widget.enableDirectionalMapping) {
      _accelSub = accelerometerEvents.listen((AccelerometerEvent event) {
        final raw = widget.manualYawRadians ?? atan2(event.y, event.x);
        _deviceYaw = _smoothAngle(_deviceYaw, raw, 0.12);
      });
      _magSub = magnetometerEvents.listen((MagnetometerEvent event) {
        // Nudge yaw toward magnetometer heading for coarse compass fusion
        final magYaw = atan2(event.y, event.x);
        _deviceYaw = _smoothAngle(_deviceYaw, magYaw, 0.06);
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
          final raw = widget.manualYawRadians ?? atan2(event.y, event.x);
          _deviceYaw = _smoothAngle(_deviceYaw, raw, 0.12);
        });
        _magSub = magnetometerEvents.listen((MagnetometerEvent event) {
          final magYaw = atan2(event.y, event.x);
          _deviceYaw = _smoothAngle(_deviceYaw, magYaw, 0.06);
        });
      }
    }

    if (oldWidget.controller != widget.controller) {
      oldWidget.controller?._detach(this);
      widget.controller?._attach(this);
    }

    if (oldWidget.beamSpawnInterval != widget.beamSpawnInterval ||
        oldWidget.reduceMotion != widget.reduceMotion ||
        oldWidget.autoSpawnEnabled != widget.autoSpawnEnabled) {
      _restartBeamTimerIfNeeded();
    }

    if (oldWidget.targetFps != widget.targetFps) {
      _targetFrameIntervalMs = 1000 / widget.targetFps.clamp(15, 120);
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _pulseController.dispose();
    _beamTimer?.cancel();
    _ticker?.dispose();
    _accelSub?.cancel();
    _magSub?.cancel();
    _iotService?.dispose();
    widget.controller?._detach(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final isActive = state == AppLifecycleState.resumed;
    if (isActive) {
      if (!(_ticker?.isActive ?? false)) {
        _ticker?.start();
      }
      _restartBeamTimerIfNeeded();
    } else {
      _ticker?.stop();
      _beamTimer?.cancel();
      _beamTimer = null;
    }
  }

  void _onVisibilityChanged(VisibilityInfo info) {
    final nowVisible = info.visibleFraction > 0.0;
    if (nowVisible == _isVisible) return;
    _isVisible = nowVisible;
    if (_isVisible) {
      if (!(_ticker?.isActive ?? false)) {
        _ticker?.start();
      }
      _restartBeamTimerIfNeeded();
    } else {
      _ticker?.stop();
      _beamTimer?.cancel();
      _beamTimer = null;
    }
  }

  // Public integration points
  void onDataSent(String deviceId, double dataSize, DeviceLocation location) {
    _spawnBeam(isOutgoing: true, deviceId: deviceId, dataSize: dataSize, location: location);
  }

  void onDataReceived(String deviceId, double dataSize, DeviceLocation location) {
    _spawnBeam(isOutgoing: false, deviceId: deviceId, dataSize: dataSize, location: location);
  }

  void updateDevicePosition(String deviceId, DeviceLocation location) {
    _devicePositions[deviceId] = location;
    // Update active beams for this device to aim toward latest position
    if (widget.enableDirectionalMapping) {
      for (final beam in _beams) {
        if (beam.deviceId == deviceId) {
          final origin = const DeviceLocation(x: 0, y: 0);
          final worldAngle = origin.angleTo(location);
          beam.angleRadians = worldAngle - _deviceYaw;
        }
      }
    }
  }

  @override
  void setDataAllowance(double allowance01) {
    _dataAllowance01 = allowance01.clamp(0.0, 1.0);
    _restartBeamTimerIfNeeded();
  }

  @override
  void setAutoSpawnEnabled(bool enabled) {
    _autoSpawnEnabledOverride = enabled;
    _restartBeamTimerIfNeeded();
  }

  void _maybeSpawnBeam() {
    final allowedMax = max(1, (widget.maxConcurrentBeams * (_dataAllowance01 * 0.9 + 0.1)).floor());
    if (_beams.length >= allowedMax) return;
    final isOutgoing = _rand.nextBool();
    _spawnBeam(isOutgoing: isOutgoing);
  }

  void _spawnBeam({
    required bool isOutgoing,
    String? deviceId,
    double dataSize = 1.0,
    DeviceLocation? location,
  }) {
    final double baseIntensity = (dataSize.clamp(0.1, 10.0) / 10.0) * widget.intensityScale * (_dataAllowance01 * 0.9 + 0.1);
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
    final fallbackColor = isOutgoing ? defaultOutgoing : defaultIncoming;

    Color resolvedColor = widget.colorResolver?.call(isOutgoing: isOutgoing, deviceId: deviceId) ?? fallbackColor;
    double widthScale = 1.0;
    double glowIntensity = 1.0;
    if (widget.beamStyleResolver != null) {
      final style = widget.beamStyleResolver!(isOutgoing: isOutgoing, deviceId: deviceId);
      resolvedColor = style.color;
      widthScale = style.widthScale;
      glowIntensity = style.glowIntensity;
    }

    final beam = DataBeam(
      angleRadians: angle,
      isOutgoing: isOutgoing,
      intensity: intensity,
      // Aim for ~2s traverse: 0.5 progress/sec => 2s. Slight variance for realism.
      speed: 0.45 + _rand.nextDouble() * 0.15,
      color: resolvedColor,
      widthScale: widthScale,
      glowIntensity: glowIntensity,
      deviceId: deviceId,
    );

    _beams.add(beam);
  }

  void _advanceBeams(double dtSeconds) {
    // Frame throttle
    if (_lastTickMs != null) {
      final ms = dtSeconds * 1000.0;
      if (ms < _targetFrameIntervalMs * 0.7) {
        // If we are ahead of budget, skip heavy work
          // No-op; retaining simple flow for now
      }
    }

    for (final beam in _beams) {
      beam.progress += beam.speed * widget.globalSpeedScale * dtSeconds;
    }
    _beams.removeWhere((b) => b.isComplete);

    // Stats callback
    widget.onStats?.call(activeBeams: _beams.length, allowance01: _dataAllowance01, fps: _fpsEma);
  }

  double _smoothAngle(double old, double next, double alpha) {
    const double twoPi = pi * 2;
    double delta = (next - old) % twoPi;
    if (delta > pi) delta -= twoPi;
    return (old + alpha * delta) % twoPi;
  }

  // Performance-mode helpers
  int _effectiveStarCount() {
    switch (widget.performanceMode) {
      case PerformanceMode.low:
        return 80; // reduced from default ~140
      case PerformanceMode.normal:
        return 140;
    }
  }

  double _effectiveGlowScale() {
    switch (widget.performanceMode) {
      case PerformanceMode.low:
        return 0.7;
      case PerformanceMode.normal:
        return 1.0;
    }
  }

  bool get _shouldAutoSpawn => _autoSpawnEnabledOverride;

  Duration get _effectiveSpawnInterval {
    final multiplier = widget.reduceMotion ? 1.8 : 1.0;
    return Duration(milliseconds: (widget.beamSpawnInterval.inMilliseconds * multiplier).round());
  }

  void _restartBeamTimerIfNeeded() {
    _beamTimer?.cancel();
    _beamTimer = null;
    if (_shouldAutoSpawn) {
      _beamTimer = Timer.periodic(_effectiveSpawnInterval, (_) => _maybeSpawnBeam());
    }
  }

  void _manualBurst() {
    for (int i = 0; i < 8; i++) {
      _spawnBeam(isOutgoing: i.isEven);
    }
  }

  @override
  Widget build(BuildContext context) {
    final mq = MediaQuery.maybeOf(context);
    final platformReduce = mq?.disableAnimations ?? false;
    final effectiveReduceMotion = widget.reduceMotion || platformReduce;
    final Gradient hubGradient = widget.hubGradient ?? _themeToGradient(widget.presetTheme, widget.hubColor);

    final semanticsText = widget.semanticsLabel ?? 'Real-time data visualization with ${_beams.length} active beams.';
    return VisibilityDetector(
      key: const ValueKey('iot-visualization-visibility'),
      onVisibilityChanged: _onVisibilityChanged,
      child: Stack(
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
                    reduceMotion: effectiveReduceMotion,
                    particleSizeRange: widget.particleSizeRange,
                    particleBlurRadius: widget.particleBlurRadius,
                    starCount: _effectiveStarCount(),
                    globalGlowScale: _effectiveGlowScale(),
                  ),
                ),
              ),
            ),
          ),
          if (widget.showHud)
            Positioned(
              left: 12,
              top: 12,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.35),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.white.withOpacity(0.15)),
                ),
                child: DefaultTextStyle(
                  style: widget.hudTextStyle ?? const TextStyle(fontSize: 12, color: Colors.white70),
                  child: Text('FPS: ${_fpsEma.toStringAsFixed(0)}  Beams: ${_beams.length}  Allow: ${( _dataAllowance01 * 100).round()}%'),
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
      ),
    );
  }

  Gradient _themeToGradient(VisualizationTheme theme, Color? baseColor) {
    final Color base;
    switch (theme) {
      case VisualizationTheme.blue:
        base = baseColor ?? Colors.cyan;
        break;
      case VisualizationTheme.green:
        base = baseColor ?? Colors.greenAccent;
        break;
      case VisualizationTheme.purple:
        base = baseColor ?? Colors.purpleAccent;
        break;
      case VisualizationTheme.orange:
        base = baseColor ?? Colors.orangeAccent;
        break;
    }
    return RadialGradient(
      colors: [
        base.withOpacity(0.95),
        base.withOpacity(0.65),
        base.withOpacity(0.1),
      ],
      stops: const [0.0, 0.6, 1.0],
    );
  }
}