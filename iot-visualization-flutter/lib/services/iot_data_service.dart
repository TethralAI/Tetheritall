import 'dart:async';

import '../models/device_location.dart';

typedef DataEventCallback = void Function(IoTDataEvent event);

class IoTDataEvent {
  IoTDataEvent.sent({
    required this.deviceId,
    required this.dataSize,
    required this.location,
  })  : isOutgoing = true,
        type = IoTDataEventType.sent;

  IoTDataEvent.received({
    required this.deviceId,
    required this.dataSize,
    required this.location,
  })  : isOutgoing = false,
        type = IoTDataEventType.received;

  final String deviceId;
  final double dataSize;
  final DeviceLocation location;
  final bool isOutgoing;
  final IoTDataEventType type;
}

enum IoTDataEventType { sent, received }

class IoTDataService {
  final _controller = StreamController<IoTDataEvent>.broadcast();

  Stream<IoTDataEvent> get events => _controller.stream;

  void onDataSent(String deviceId, double dataSize, DeviceLocation location) {
    _controller.add(IoTDataEvent.sent(deviceId: deviceId, dataSize: dataSize, location: location));
  }

  void onDataReceived(String deviceId, double dataSize, DeviceLocation location) {
    _controller.add(IoTDataEvent.received(deviceId: deviceId, dataSize: dataSize, location: location));
  }

  void dispose() {
    _controller.close();
  }
}
