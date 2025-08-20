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

  // New: set a global data allowance (0..1) to scale visualization intensity/throughput
  void setDataAllowance(double allowance01) {
    _attachable?.setDataAllowance(allowance01);
  }

  // Toggle automatic demo beam spawning at runtime
  void setAutoSpawnEnabled(bool enabled) {
    _attachable?.setAutoSpawnEnabled(enabled);
  }
}

abstract class _Attachable {
  void onDataSent(String deviceId, double dataSize, DeviceLocation location);
  void onDataReceived(String deviceId, double dataSize, DeviceLocation location);
  void updateDevicePosition(String deviceId, DeviceLocation location);
  void setDataAllowance(double allowance01);
  void setAutoSpawnEnabled(bool enabled);
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
