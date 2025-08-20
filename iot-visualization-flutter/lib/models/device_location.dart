import 'dart:math';

class DeviceLocation {
  const DeviceLocation({required this.x, required this.y, this.floor = 0});

  final double x; // meters in local room coordinates
  final double y; // meters in local room coordinates
  final int floor;

  double angleTo(DeviceLocation other) {
    return atan2(other.y - y, other.x - x);
  }
}
