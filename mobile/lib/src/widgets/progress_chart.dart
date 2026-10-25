import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../api/models.dart';

/// Percentage across exams this year: one series, single hue, 0–100 axis, tap tooltip.
class ProgressChart extends StatelessWidget {
  const ProgressChart({super.key, required this.points});
  final List<ProgressPoint> points;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final spots = <FlSpot>[
      for (var i = 0; i < points.length; i++)
        if (points[i].percentage != null) FlSpot(i.toDouble(), points[i].percentage!),
    ];
    final muted = scheme.onSurfaceVariant;
    return SizedBox(
      height: 200,
      child: LineChart(
        LineChartData(
          minY: 0,
          maxY: 100,
          minX: -0.3,
          maxX: points.length - 0.7,
          gridData: FlGridData(
            drawVerticalLine: false,
            horizontalInterval: 25,
            getDrawingHorizontalLine: (_) => FlLine(color: scheme.outlineVariant, strokeWidth: 1),
          ),
          borderData: FlBorderData(show: false),
          titlesData: FlTitlesData(
            topTitles: const AxisTitles(),
            rightTitles: const AxisTitles(),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                interval: 25,
                reservedSize: 32,
                getTitlesWidget: (v, _) => Text(v.toInt().toString(), style: TextStyle(color: muted, fontSize: 11)),
              ),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                interval: 1,
                reservedSize: 28,
                getTitlesWidget: (v, _) {
                  final i = v.round();
                  if (i < 0 || i >= points.length || (v - i).abs() > 0.01) return const SizedBox.shrink();
                  return Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text(points[i].examName, style: TextStyle(color: muted, fontSize: 11)),
                  );
                },
              ),
            ),
          ),
          lineTouchData: LineTouchData(
            touchTooltipData: LineTouchTooltipData(
              getTooltipColor: (_) => scheme.inverseSurface,
              getTooltipItems: (items) => [
                for (final s in items)
                  LineTooltipItem(
                    '${points[s.x.round()].examName}\n${fmtPct(s.y)}',
                    TextStyle(color: scheme.onInverseSurface, fontWeight: FontWeight.w600),
                  ),
              ],
            ),
          ),
          lineBarsData: [
            LineChartBarData(
              spots: spots,
              color: scheme.primary,
              barWidth: 2.5,
              dotData: FlDotData(
                getDotPainter: (spot, percent, bar, index) => FlDotCirclePainter(
                  radius: 4.5,
                  color: scheme.primary,
                  strokeWidth: 2,
                  strokeColor: scheme.surface,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
