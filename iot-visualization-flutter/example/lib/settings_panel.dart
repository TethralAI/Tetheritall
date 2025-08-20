import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'settings_service.dart';

typedef OnSettingsChanged = void Function(VisualizationSettings settings);

class SettingsPanel extends StatelessWidget {
  const SettingsPanel({super.key, required this.settings, required this.onChanged});

  final VisualizationSettings settings;
  final OnSettingsChanged onChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('Data allowance: ${(settings.allowance * 100).round()}%', textAlign: TextAlign.center),
        Slider(
          value: settings.allowance,
          onChanged: (v) => onChanged(_copy(settings)..allowance = v),
        ),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Switch(
              value: settings.autoSpawn,
              onChanged: (v) => onChanged(_copy(settings)..autoSpawn = v),
            ),
            const SizedBox(width: 8),
            const Text('Auto-spawn'),
          ],
        ),
        const SizedBox(height: 4),
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 12,
          runSpacing: 8,
          children: [
            _switchRow('HUD', settings.showHud, (v) => onChanged(_copy(settings)..showHud = v)),
            _switchRow('Starfield', settings.enableStarfield, (v) => onChanged(_copy(settings)..enableStarfield = v)),
            _switchRow('Reduce motion', settings.reduceMotion, (v) => onChanged(_copy(settings)..reduceMotion = v)),
            _dropdownRow<int>('FPS', settings.targetFps, [30, 60],
                (v) => onChanged(_copy(settings)..targetFps = v)),
            _dropdownRow<String>('Theme', _themeToString(settings.presetTheme), const ['blue', 'green', 'purple', 'orange'],
                (v) => onChanged(_copy(settings)..presetTheme = _themeFromString(v))),
            _dropdownRow<int>('Particles', settings.particleCount, const [2, 4, 6, 8, 10],
                (v) => onChanged(_copy(settings)..particleCount = v)),
            _dropdownRow<int>('Max beams', settings.maxBeams, const [10, 20, 30, 40, 50],
                (v) => onChanged(_copy(settings)..maxBeams = v)),
            _dropdownRow<int>('Spawn ms', settings.spawnMs, const [200, 280, 350, 450, 600],
                (v) => onChanged(_copy(settings)..spawnMs = v)),
            _dropdownRow<double>('Speed', double.parse(settings.speedScale.toStringAsFixed(1)),
                const [0.5, 0.8, 1.0, 1.2, 1.5, 2.0], (v) => onChanged(_copy(settings)..speedScale = v)),
            _dropdownRow<String>('Perf', settings.perfMode == PerformanceMode.low ? 'low' : 'normal', const ['normal', 'low'],
                (v) => onChanged(_copy(settings)..perfMode = v == 'low' ? PerformanceMode.low : PerformanceMode.normal)),
            Row(mainAxisSize: MainAxisSize.min, children: [
              const Text('Hub color'),
              const SizedBox(width: 6),
              ElevatedButton(
                onPressed: () async {
                  final picked = await _pickColor(context);
                  if (picked != null) onChanged(_copy(settings)..hubColor = picked);
                },
                child: const Text('Select'),
              ),
              const SizedBox(width: 8),
              Container(width: 24, height: 24, decoration: BoxDecoration(color: settings.hubColor, shape: BoxShape.circle)),
            ]),
          ],
        ),
        const SizedBox(height: 8),
        Center(
          child: ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent),
            onPressed: () async {
              final prefs = await SharedPreferences.getInstance();
              await prefs.clear();
              onChanged(VisualizationSettings(
                allowance: 1.0,
                autoSpawn: true,
                enableStarfield: true,
                reduceMotion: false,
                showHud: true,
                targetFps: 60,
                presetTheme: VisualizationTheme.blue,
                particleCount: 6,
                maxBeams: 30,
                spawnMs: 280,
                speedScale: 1.0,
                perfMode: PerformanceMode.normal,
                hubColor: Colors.cyan,
              ));
            },
            child: const Text('Reset defaults'),
          ),
        ),
      ],
    );
  }

  Widget _switchRow(String label, bool value, ValueChanged<bool> onChanged) {
    return Row(mainAxisSize: MainAxisSize.min, children: [
      Text(label),
      Switch(value: value, onChanged: onChanged),
    ]);
  }

  Widget _dropdownRow<T>(String label, T value, List<T> items, ValueChanged<T> onChanged) {
    return Row(mainAxisSize: MainAxisSize.min, children: [
      Text(label),
      const SizedBox(width: 6),
      DropdownButton<T>(
        value: value,
        items: items.map((e) => DropdownMenuItem<T>(value: e, child: Text('$e'))).toList(),
        onChanged: (v) {
          if (v != null) onChanged(v);
        },
      ),
    ]);
  }

  VisualizationSettings _copy(VisualizationSettings s) => VisualizationSettings(
        allowance: s.allowance,
        autoSpawn: s.autoSpawn,
        enableStarfield: s.enableStarfield,
        reduceMotion: s.reduceMotion,
        showHud: s.showHud,
        targetFps: s.targetFps,
        presetTheme: s.presetTheme,
        particleCount: s.particleCount,
        maxBeams: s.maxBeams,
        spawnMs: s.spawnMs,
        speedScale: s.speedScale,
        perfMode: s.perfMode,
        hubColor: s.hubColor,
      );

  Future<Color?> _pickColor(BuildContext context) async {
    final colors = <Color>[Colors.cyan, Colors.blue, Colors.greenAccent, Colors.purpleAccent, Colors.orangeAccent, Colors.redAccent];
    return showDialog<Color?>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Pick hub color'),
        content: Wrap(
          spacing: 8,
          runSpacing: 8,
          children: colors
              .map((c) => GestureDetector(
                    onTap: () => Navigator.of(ctx).pop(c),
                    child: Container(width: 28, height: 28, decoration: BoxDecoration(color: c, shape: BoxShape.circle)),
                  ))
              .toList(),
        ),
      ),
    );
  }

  VisualizationTheme _themeFromString(String name) {
    switch (name) {
      case 'green':
        return VisualizationTheme.green;
      case 'purple':
        return VisualizationTheme.purple;
      case 'orange':
        return VisualizationTheme.orange;
      case 'blue':
      default:
        return VisualizationTheme.blue;
    }
  }

  String _themeToString(VisualizationTheme theme) {
    switch (theme) {
      case VisualizationTheme.green:
        return 'green';
      case VisualizationTheme.purple:
        return 'purple';
      case VisualizationTheme.orange:
        return 'orange';
      case VisualizationTheme.blue:
      default:
        return 'blue';
    }
  }
}

