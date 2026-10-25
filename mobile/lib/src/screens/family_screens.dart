import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

import '../api/models.dart';
import '../auth/auth.dart';
import '../l10n/strings.dart';
import '../widgets/common.dart';
import '../widgets/progress_chart.dart';

final childrenProvider = FutureProvider.autoDispose<List<Child>>((ref) async {
  final data = await ref.read(apiProvider).get<List<dynamic>>('/children');
  return data.map((e) => Child.fromJson(e as Map<String, dynamic>)).toList();
});

final resultsProvider = FutureProvider.autoDispose.family<List<ExamResult>, String>((ref, studentId) async {
  final data = await ref.read(apiProvider).get<List<dynamic>>('/students/$studentId/results');
  return data.map((e) => ExamResult.fromJson(e as Map<String, dynamic>)).toList();
});

final progressProvider = FutureProvider.autoDispose.family<List<ProgressPoint>, String>((ref, studentId) async {
  final data = await ref.read(apiProvider).get<Map<String, dynamic>>('/students/$studentId/progress');
  return (data['overall'] as List).map((e) => ProgressPoint.fromJson(e as Map<String, dynamic>)).toList();
});

final examDetailProvider = FutureProvider.autoDispose.family<ExamResult, (String, String)>((ref, ids) async {
  final data = await ref.read(apiProvider).get<Map<String, dynamic>>('/students/${ids.$1}/results/${ids.$2}');
  return ExamResult.fromJson(data);
});

/// Parents with several children pick one; with exactly one child we go straight to it.
class ChildrenScreen extends ConsumerWidget {
  const ChildrenScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final children = ref.watch(childrenProvider);
    final single = children.valueOrNull?.length == 1 ? children.value!.first : null;
    if (single != null) return StudentHomeScreen(studentId: single.studentId, title: single.fullName);
    return Scaffold(
      appBar: AppBar(title: Text(S.t('children.title')), actions: profileAction(context)),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(childrenProvider.future),
        child: AsyncBody(
          value: children,
          onRetry: () => ref.invalidate(childrenProvider),
          builder: (list) => list.isEmpty
              ? EmptyMessage(S.t('children.none'))
              : ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: list.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (context, i) {
                    final c = list[i];
                    return Card(
                      child: ListTile(
                        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                        leading: CircleAvatar(child: Text(c.fullName.characters.first)),
                        title: Text(c.fullName, style: Theme.of(context).textTheme.titleMedium),
                        subtitle: c.sectionName == null ? null : Text(c.sectionName!),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
                          builder: (_) => StudentHomeScreen(studentId: c.studentId, title: c.fullName, pushed: true),
                        )),
                      ),
                    );
                  },
                ),
        ),
      ),
    );
  }
}

class StudentHomeScreen extends ConsumerWidget {
  const StudentHomeScreen({super.key, required this.studentId, required this.title, this.pushed = false});
  final String studentId;
  final String title;
  final bool pushed;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final results = ref.watch(resultsProvider(studentId));
    final progress = ref.watch(progressProvider(studentId));
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(title), actions: pushed ? null : profileAction(context)),
      body: RefreshIndicator(
        onRefresh: () {
          ref.invalidate(progressProvider(studentId));
          return ref.refresh(resultsProvider(studentId).future);
        },
        child: AsyncBody(
          value: results,
          onRetry: () => ref.invalidate(resultsProvider(studentId)),
          builder: (rows) {
            if (rows.isEmpty) return ListView(children: [EmptyMessage(S.t('home.noResults'))]);
            final latest = rows.first;
            final points = progress.valueOrNull ?? const <ProgressPoint>[];
            return ListView(padding: const EdgeInsets.all(16), children: [
              _ResultCard(result: latest, onOpen: () => _openExam(context, latest)),
              const SizedBox(height: 16),
              if (points.length > 1) ...[
                Card(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(12, 16, 20, 12),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Padding(
                        padding: const EdgeInsets.only(left: 8, bottom: 12),
                        child: Text(S.t('home.progress'), style: theme.textTheme.titleMedium),
                      ),
                      ProgressChart(points: points),
                    ]),
                  ),
                ),
                const SizedBox(height: 16),
              ],
              Text(S.t('home.exams'), style: theme.textTheme.titleMedium),
              const SizedBox(height: 8),
              Card(
                child: Column(children: [
                  for (final r in rows)
                    ListTile(
                      title: Text(r.examName),
                      subtitle: Text('${fmtNum(r.totalObtained)} / ${fmtNum(r.totalMax)}'),
                      trailing: Text(
                        '${fmtPct(r.percentage)}  ${r.grade ?? ''}',
                        style: theme.textTheme.titleMedium,
                      ),
                      onTap: () => _openExam(context, r),
                    ),
                ]),
              ),
            ]);
          },
        ),
      ),
    );
  }

  void _openExam(BuildContext context, ExamResult r) {
    Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => ExamDetailScreen(studentId: studentId, examId: r.examId, examName: r.examName),
    ));
  }
}

class _ResultCard extends StatelessWidget {
  const _ResultCard({required this.result, required this.onOpen});
  final ExamResult result;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final r = result;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(S.t('home.latest').toUpperCase(),
              style: theme.textTheme.labelSmall?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
          Text(r.examName, style: theme.textTheme.titleLarge),
          const SizedBox(height: 12),
          Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
            Text(fmtPct(r.percentage), style: theme.textTheme.displaySmall?.copyWith(fontWeight: FontWeight.w700)),
            const SizedBox(width: 20),
            Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(r.grade ?? '–', style: theme.textTheme.headlineSmall),
              Text(S.t('home.grade'), style: theme.textTheme.bodySmall),
            ]),
          ]),
          const SizedBox(height: 4),
          Text('${fmtNum(r.totalObtained)} / ${fmtNum(r.totalMax)}'),
          if (r.rank != null) Text(S.t('home.rank', {'rank': r.rank!, 'size': r.sectionSize})),
          const SizedBox(height: 8),
          Chip(
            avatar: Icon(r.passed ? Icons.check_circle : Icons.info_outline, size: 18),
            label: Text(r.passed ? S.t('home.passed') : S.t('home.needsImprovement')),
          ),
          const SizedBox(height: 12),
          FilledButton(onPressed: onOpen, child: Text(S.t('home.bySubject'))),
        ]),
      ),
    );
  }
}

class ExamDetailScreen extends ConsumerStatefulWidget {
  const ExamDetailScreen({super.key, required this.studentId, required this.examId, required this.examName});
  final String studentId;
  final String examId;
  final String examName;

  @override
  ConsumerState<ExamDetailScreen> createState() => _ExamDetailScreenState();
}

class _ExamDetailScreenState extends ConsumerState<ExamDetailScreen> {
  bool _downloading = false;

  Future<void> _downloadReportCard() async {
    setState(() => _downloading = true);
    try {
      final dir = await getTemporaryDirectory();
      final path = '${dir.path}${Platform.pathSeparator}report-card-${widget.examId}.pdf';
      await ref.read(apiProvider).download('/students/${widget.studentId}/report-cards/${widget.examId}.pdf', path);
      await OpenFilex.open(path, type: 'application/pdf');
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _downloading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final detail = ref.watch(examDetailProvider((widget.studentId, widget.examId)));
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(widget.examName)),
      body: AsyncBody(
        value: detail,
        onRetry: () => ref.invalidate(examDetailProvider((widget.studentId, widget.examId))),
        builder: (d) => ListView(padding: const EdgeInsets.all(16), children: [
          Card(
            child: Column(children: [
              for (final s in d.subjects)
                ListTile(
                  title: Text(s.subjectName),
                  subtitle: s.grade == null ? null : Text('${S.t('home.grade')} ${s.grade}'),
                  trailing: Text(
                    s.status == 'ABSENT'
                        ? S.t('exam.absent')
                        : s.status == 'EXEMPT'
                            ? S.t('exam.exempt')
                            : '${fmtNum(s.marks)} / ${fmtNum(s.maxMarks)}',
                    style: theme.textTheme.titleMedium?.copyWith(
                      color: s.passed == false ? theme.colorScheme.error : null,
                    ),
                  ),
                ),
              const Divider(height: 1),
              ListTile(
                title: Text(S.t('exam.total'), style: const TextStyle(fontWeight: FontWeight.w700)),
                subtitle: Text('${fmtPct(d.percentage)} · ${d.grade ?? '–'}'),
                trailing: Text('${fmtNum(d.totalObtained)} / ${fmtNum(d.totalMax)}', style: theme.textTheme.titleMedium),
              ),
            ]),
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _downloading ? null : _downloadReportCard,
            icon: _downloading
                ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.picture_as_pdf_outlined),
            label: Text(S.t('exam.reportCard')),
          ),
        ]),
      ),
    );
  }
}
