import '../models/device_location.dart';

class DataTransmissionController {
  _Attachable? _attachable;

  void _attach(_Attachable attachable) {
    _attachable = attachable;
  }

  void _detach(_Attachable attachable) {
    if (_attachable == attachable) {
      _attachable = null;
    }
  }

  void onDataSent(String deviceId, double dataSize, DeviceLocation location) {
    _attachable?.onDataSent(deviceId, dataSize, location);
  }

  void onDataReceived(String deviceId, double dataSize, DeviceLocation location) {
    _attachable?.onDataReceived(deviceId, dataSize, location);
  }

  void updateDevicePosition(String deviceId, DeviceLocation location) {
    _attachable?.updateDevicePosition(deviceId, location);
  }
}

abstract class _Attachable {
  void onDataSent(String deviceId, double dataSize, DeviceLocation location);
  void onDataReceived(String deviceId, double dataSize, DeviceLocation location);
  void updateDevicePosition(String deviceId, DeviceLocation location);
}
import '../models/device_location.dart';

class DataTransmissionController {
  _Attachable? _attachable;

  void _attach(_Attachable attachable) {
    _attachable = attachable;
  }

  void _detach(_Attachable attachable) {
    if (_attachable == attachable) {
      _attachable = null;
    }
  }

  void onDataSent(String deviceId, double dataSize, DeviceLocation location) {
    _attachable?.onDataSent(deviceId, dataSize, location);
  }

  void onDataReceived(String deviceId, double dataSize, DeviceLocation location) {
    _attachable?.onDataReceived(deviceId, dataSize, location);
  }

  void updateDevicePosition(String deviceId, DeviceLocation location) {
    _attachable?.updateDevicePosition(deviceId, location);
  }
}

abstract class _Attachable {
  void onDataSent(String deviceId, double dataSize, DeviceLocation location);
  void onDataReceived(String deviceId, double dataSize, DeviceLocation location);
  void updateDevicePosition(String deviceId, DeviceLocation location);
}
