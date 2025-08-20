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