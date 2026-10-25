import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/models.dart';
import '../auth/auth.dart';
import '../l10n/strings.dart';
import '../widgets/common.dart';

final examsProvider = FutureProvider.autoDispose.family<List<Exam>, String?>((ref, yearId) async {
  final data = await ref.read(apiProvider).get<List<dynamic>>(
        '/exams',
        query: {if (yearId != null) 'academic_year_id': yearId},
      );
  return data.map((e) => Exam.fromJson(e as Map<String, dynamic>)).toList();
});

class _Dashboard {
  _Dashboard(this.summary, this.attention);
  final DashboardSummary summary;
  final List<AttentionStudent> attention;
}

final dashboardProvider = FutureProvider.autoDispose.family<_Dashboard, String>((ref, examId) async {
  final api = ref.read(apiProvider);
  final results = await Future.wait([
    api.get<Map<String, dynamic>>('/dashboard/summary', query: {'exam_id': examId}),
    api.get<List<dynamic>>('/dashboard/attention', query: {'exam_id': examId}),
  ]);
  return _Dashboard(
    DashboardSummary.fromJson(results[0] as Map<String, dynamic>),
    (results[1] as List).map((e) => AttentionStudent.fromJson(e as Map<String, dynamic>)).toList(),
  );
});

/// Read-only summary for the principal: headline numbers + students needing attention.
class PrincipalScreen extends ConsumerStatefulWidget {
  const PrincipalScreen({super.key});

  @override
  ConsumerState<PrincipalScreen> createState() => _PrincipalScreenState();
}

class _PrincipalScreenState extends ConsumerState<PrincipalScreen> {
  String? _examId;

  @override
  Widget build(BuildContext context) {
    final exams = ref.watch(examsProvider(null));
    return Scaffold(
      appBar: AppBar(title: Text(S.t('principal.title')), actions: profileAction(context)),
      body: AsyncBody(
        value: exams,
        onRetry: () => ref.invalidate(examsProvider(null)),
        builder: (list) {
          if (list.isEmpty) return EmptyMessage(S.t('principal.noData'));
          final today = DateTime.now().toIso8601String().substring(0, 10);
          final started = list.where((e) => e.startDate == null || e.startDate!.compareTo(today) <= 0).toList();
          final examId = _examId ?? (started.isNotEmpty ? started.last.id : list.first.id);
          return ListView(padding: const EdgeInsets.all(16), children: [
            DropdownButtonFormField<String>(
              initialValue: examId,
              decoration: InputDecoration(labelText: S.t('marks.exam')),
              items: [for (final e in list) DropdownMenuItem(value: e.id, child: Text(e.name))],
              onChanged: (v) => setState(() => _examId = v),
            ),
            const SizedBox(height: 16),
            _DashboardBody(examId: examId),
          ]);
        },
      ),
    );
  }
}

class _DashboardBody extends ConsumerWidget {
  const _DashboardBody({required this.examId});
  final String examId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dash = ref.watch(dashboardProvider(examId));
    final theme = Theme.of(context);
    return AsyncBody(
      value: dash,
      onRetry: () => ref.invalidate(dashboardProvider(examId)),
      builder: (d) {
        final s = d.summary;
        if (s.withResults == 0) return EmptyMessage(S.t('principal.noData'));
        Widget stat(String label, String value) => Expanded(
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(label, style: theme.textTheme.labelMedium),
                    const SizedBox(height: 4),
                    Text(value, style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700)),
                  ]),
                ),
              ),
            );
        return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            stat(S.t('principal.students'), '${s.withResults}'),
            const SizedBox(width: 8),
            stat(S.t('principal.average'), fmtPct(s.average)),
          ]),
          const SizedBox(height: 8),
          Row(children: [
            stat(S.t('principal.passRate'), fmtPct(s.passRate)),
            const SizedBox(width: 8),
            stat(S.t('principal.published'), '${s.published} / ${s.sectionsTotal}'),
          ]),
          const SizedBox(height: 20),
          Text('${S.t('principal.attention')} (${d.attention.length})', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          if (d.attention.isEmpty)
            EmptyMessage(S.t('principal.noAttention'))
          else
            Card(
              child: Column(children: [
                for (final a in d.attention)
                  ListTile(
                    title: Text(a.fullName),
                    subtitle: Text('${a.sectionName} · ${a.reasons.join(' · ')}'),
                    trailing: Text(fmtPct(a.percentage), style: theme.textTheme.titleMedium),
                  ),
              ]),
            ),
        ]);
      },
    );
  }
}
