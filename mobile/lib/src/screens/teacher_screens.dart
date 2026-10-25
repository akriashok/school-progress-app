import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../api/models.dart';
import '../auth/auth.dart';
import '../l10n/strings.dart';
import '../widgets/common.dart';
import 'principal_screen.dart' show examsProvider;

final assignmentsProvider = FutureProvider.autoDispose<List<Assignment>>((ref) async {
  final data = await ref.read(apiProvider).get<List<dynamic>>('/teacher/my-assignments');
  return data.map((e) => Assignment.fromJson(e as Map<String, dynamic>)).toList();
});

class TeacherHomeScreen extends ConsumerWidget {
  const TeacherHomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final list = ref.watch(assignmentsProvider);
    return Scaffold(
      appBar: AppBar(title: Text(S.t('teacher.title')), actions: profileAction(context)),
      body: AsyncBody(
        value: list,
        onRetry: () => ref.invalidate(assignmentsProvider),
        builder: (items) => items.isEmpty
            ? EmptyMessage(S.t('teacher.none'))
            : ListView.separated(
                padding: const EdgeInsets.all(16),
                itemCount: items.length,
                separatorBuilder: (_, __) => const SizedBox(height: 10),
                itemBuilder: (context, i) {
                  final a = items[i];
                  return Card(
                    child: ListTile(
                      title: Text('${a.sectionName} · ${a.subjectName}'),
                      subtitle: Text(S.t('teacher.students', {'n': a.studentCount})),
                      trailing: const Icon(Icons.edit_note),
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute<void>(builder: (_) => TeacherMarksScreen(assignment: a)),
                      ),
                    ),
                  );
                },
              ),
      ),
    );
  }
}

/// Simple marks entry for one section + subject: a list with one field per student.
class TeacherMarksScreen extends ConsumerStatefulWidget {
  const TeacherMarksScreen({super.key, required this.assignment});
  final Assignment assignment;

  @override
  ConsumerState<TeacherMarksScreen> createState() => _TeacherMarksScreenState();
}

class _TeacherMarksScreenState extends ConsumerState<TeacherMarksScreen> {
  String? _examId;
  String? _examSubjectId;
  MarksGridData? _grid;
  final Map<String, TextEditingController> _controllers = {};
  bool _loading = false;
  bool _autoLoadScheduled = false;
  bool _saving = false;
  String? _message;

  @override
  void dispose() {
    for (final c in _controllers.values) {
      c.dispose();
    }
    super.dispose();
  }

  ApiClient get _api => ref.read(apiProvider);

  Future<void> _loadExam(String examId) async {
    setState(() {
      _examId = examId;
      _loading = true;
      _grid = null;
      _message = null;
    });
    try {
      final subjects = await _api.get<List<dynamic>>('/exams/$examId/subjects');
      final match = subjects.cast<Map<String, dynamic>>().where(
            (s) => s['class_id'] == widget.assignment.classId && s['subject_id'] == widget.assignment.subjectId,
          );
      if (match.isEmpty) {
        setState(() => _message = S.t('marks.noSubject'));
        return;
      }
      _examSubjectId = match.first['id'] as String;
      final data = await _api.get<Map<String, dynamic>>(
        '/marks',
        query: {'exam_subject_id': _examSubjectId, 'section_id': widget.assignment.sectionId},
      );
      final grid = MarksGridData.fromJson(data);
      for (final r in grid.rows) {
        (_controllers[r.studentId] ??= TextEditingController()).text = r.display;
      }
      setState(() => _grid = grid);
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  /// Returns the API entry for a cell, null for blank, or throws FormatException.
  Map<String, Object?>? _entry(String studentId, String raw, double max) {
    final v = raw.trim().toUpperCase();
    if (v.isEmpty) return null;
    if (v == 'AB' || v == 'A') return {'student_id': studentId, 'status': 'ABSENT', 'marks': null};
    if (v == 'EX') return {'student_id': studentId, 'status': 'EXEMPT', 'marks': null};
    final n = double.tryParse(v);
    if (n == null || n < 0 || n > max || !RegExp(r'^\d+(\.\d{1,2})?$').hasMatch(v)) {
      throw FormatException(S.t('marks.invalid', {'max': fmtNum(max)}));
    }
    return {'student_id': studentId, 'status': 'PRESENT', 'marks': v};
  }

  Future<void> _save() async {
    final grid = _grid!;
    final entries = <Map<String, Object?>>[];
    try {
      for (final r in grid.rows) {
        final text = _controllers[r.studentId]!.text;
        if (text.trim() == r.display) continue;
        final e = _entry(r.studentId, text, grid.maxMarks);
        if (e != null) entries.add(e);
      }
    } on FormatException catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
      return;
    }
    if (entries.isEmpty) return;
    setState(() => _saving = true);
    try {
      final res = await _api.put<Map<String, dynamic>>('/marks/bulk', {
        'exam_subject_id': _examSubjectId,
        'section_id': widget.assignment.sectionId,
        'entries': entries,
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(S.t('marks.saved', {'created': res['created'] as int, 'updated': res['updated'] as int})),
      ));
      await _loadExam(_examId!);
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final a = widget.assignment;
    final exams = ref.watch(examsProvider(a.academicYearId));
    final grid = _grid;
    return Scaffold(
      appBar: AppBar(title: Text('${a.sectionName} · ${a.subjectName}')),
      body: AsyncBody(
        value: exams,
        onRetry: () => ref.invalidate(examsProvider(a.academicYearId)),
        builder: (list) {
          if (_examId == null && list.isNotEmpty && !_autoLoadScheduled) {
            _autoLoadScheduled = true;
            final today = DateTime.now().toIso8601String().substring(0, 10);
            final started = list.where((e) => e.startDate == null || e.startDate!.compareTo(today) <= 0).toList();
            final first = started.isNotEmpty ? started.last.id : list.first.id;
            WidgetsBinding.instance.addPostFrameCallback((_) => _loadExam(first));
          }
          return Column(children: [
            Padding(
              padding: const EdgeInsets.all(16),
              child: DropdownButtonFormField<String>(
                initialValue: _examId,
                decoration: InputDecoration(labelText: S.t('marks.exam')),
                items: [for (final e in list) DropdownMenuItem(value: e.id, child: Text(e.name))],
                onChanged: (v) => v == null ? null : _loadExam(v),
              ),
            ),
            if (_loading) const LinearProgressIndicator(),
            if (_message != null) Expanded(child: EmptyMessage(_message!)),
            if (grid != null) ...[
              if (!grid.canEdit)
                MaterialBanner(content: Text(S.t('marks.locked')), actions: const [SizedBox.shrink()]),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Text('${grid.title} · ${S.t('marks.hint')}', style: Theme.of(context).textTheme.bodySmall),
              ),
              Expanded(
                child: ListView.builder(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
                  itemCount: grid.rows.length,
                  itemBuilder: (context, i) {
                    final r = grid.rows[i];
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(children: [
                        SizedBox(width: 36, child: Text(r.rollNo ?? '', style: Theme.of(context).textTheme.bodySmall)),
                        Expanded(child: Text(r.fullName)),
                        SizedBox(
                          width: 96,
                          child: TextField(
                            controller: _controllers[r.studentId],
                            enabled: grid.canEdit,
                            textAlign: TextAlign.end,
                            keyboardType: TextInputType.text,
                            textInputAction: i == grid.rows.length - 1 ? TextInputAction.done : TextInputAction.next,
                            decoration: InputDecoration(
                              isDense: true,
                              hintText: '/ ${fmtNum(grid.maxMarks)}',
                            ),
                          ),
                        ),
                      ]),
                    );
                  },
                ),
              ),
            ],
          ]);
        },
      ),
      floatingActionButton: grid != null && grid.canEdit
          ? FloatingActionButton.extended(
              onPressed: _saving ? null : _save,
              icon: const Icon(Icons.save),
              label: Text(S.t('marks.save')),
            )
          : null,
    );
  }
}
