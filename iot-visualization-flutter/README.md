# IoT Visualization (Flutter)

Reusable Flutter widget for visualizing real-time IoT data transmissions with animated beams and a starry background.

## Setup

Add this package directory to your Flutter workspace or copy `lib/` into your app.

Update your `pubspec.yaml`:

```
dependencies:
  flutter:
    sdk: flutter
  sensors_plus: ^3.0.0
```

## Usage

```dart
import 'package:iot_visualization/iot_visualization.dart';

final controller = DataTransmissionController();

Widget build(BuildContext context) {
  return SizedBox.expand(
    child: DataTransmissionVisualization(
      controller: controller,
      hubColor: Colors.cyan,
      maxConcurrentBeams: 30,
      enableDirectionalMapping: true,
      // Production controls
      beamSpawnInterval: Duration(milliseconds: 250),
      globalSpeedScale: 1.0,
      starfieldSeed: 1337,
      particleCount: 6,
      reduceMotion: false,
      autoSpawnEnabled: true, // turn off in production if you only use real data
      targetFps: 60,
      presetTheme: VisualizationTheme.blue,
      semanticsLabel: 'IoT data visualization',
      particleSizeRange: Size(1.6, 3.0),
      particleBlurRadius: 3.0,
      colorResolver: ({required bool isOutgoing, String? deviceId}) {
        // Customize colors per device/type
        if (deviceId == 'camera') return Colors.purpleAccent;
        return isOutgoing ? const Color(0xFF00E5FF) : const Color(0xFFFFA726);
      },
      beamStyleResolver: ({required bool isOutgoing, String? deviceId}) {
        if (deviceId == 'router') {
          return BeamStyle(color: Colors.lightGreenAccent, widthScale: 1.3, glowIntensity: 1.2);
        }
        return BeamStyle(color: isOutgoing ? const Color(0xFF00E5FF) : const Color(0xFFFFA726));
      },
    ),
  );
}

// Trigger events (e.g., in response to actual IoT traffic)
controller.onDataSent('lamp-1', 2.5, const DeviceLocation(x: 2, y: -1));
controller.onDataReceived('thermo', 1.0, const DeviceLocation(x: -1, y: 0.5));
```

## Features
- Starry space background with dark gradient
- Pulsing glowing hub
- Incoming (amber) and outgoing (cyan) animated beams with particles
- Directional mapping using device sensors (accelerometer) when enabled
- FloatingActionButton to simulate a data burst
- Semantics labels for accessibility

## Notes
- Aims for 60fps with 20–50 beams via efficient `CustomPainter`
- Toggle starfield with `enableStarfield`
- Control visual intensity via `intensityScale`
- Auto-spawn beams: `autoSpawnEnabled` (disable for production)
- FPS control: `targetFps`
- Themes: `presetTheme` or supply `hubGradient`
- Particle controls: `particleSizeRange`, `particleBlurRadius`, `particleCount`
- Orientation: accelerometer + magnetometer fusion, `manualYawRadians` override