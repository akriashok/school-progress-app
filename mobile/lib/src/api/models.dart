// Plain models for the API responses the app uses (see the backend OpenAPI spec).

double? _num(Object? v) => v == null ? null : double.tryParse(v.toString());

class RoleOption {
  RoleOption.fromJson(Map<String, dynamic> j)
      : roleId = j['role_id'] as String,
        role = j['role'] as String,
        schoolName = j['school_name'] as String?;
  final String roleId;
  final String role;
  final String? schoolName;
}

class Me {
  Me.fromJson(Map<String, dynamic> j)
      : fullName = j['full_name'] as String,
        role = j['role'] as String,
        roleId = j['role_id'] as String,
        schoolName = j['school_name'] as String?,
        studentId = j['student_id'] as String?,
        consentRequired = j['consent_required'] as bool,
        otherRoles = (j['other_roles'] as List).map((e) => RoleOption.fromJson(e as Map<String, dynamic>)).toList();
  final String fullName;
  final String role;
  final String roleId;
  final String? schoolName;
  final String? studentId;
  final bool consentRequired;
  final List<RoleOption> otherRoles;
}

class Child {
  Child.fromJson(Map<String, dynamic> j)
      : studentId = j['student_id'] as String,
        fullName = j['full_name'] as String,
        sectionName = j['section_name'] as String?;
  final String studentId;
  final String fullName;
  final String? sectionName;
}

class ExamResult {
  ExamResult.fromJson(Map<String, dynamic> j)
      : examId = j['exam_id'] as String,
        examName = j['exam_name'] as String,
        totalObtained = _num(j['total_obtained']) ?? 0,
        totalMax = _num(j['total_max']) ?? 0,
        percentage = _num(j['percentage']),
        grade = j['grade'] as String?,
        passed = j['passed'] as bool,
        rank = j['rank'] as int?,
        sectionSize = j['section_size'] as int? ?? 0,
        studentName = j['student_name'] as String?,
        subjects = ((j['subjects'] as List?) ?? const [])
            .map((e) => SubjectResult.fromJson(e as Map<String, dynamic>))
            .toList();
  final String examId;
  final String examName;
  final double totalObtained;
  final double totalMax;
  final double? percentage;
  final String? grade;
  final bool passed;
  final int? rank;
  final int sectionSize;
  final String? studentName;
  final List<SubjectResult> subjects;
}

class SubjectResult {
  SubjectResult.fromJson(Map<String, dynamic> j)
      : subjectName = j['subject_name'] as String,
        maxMarks = _num(j['max_marks']) ?? 0,
        status = j['status'] as String,
        marks = _num(j['marks']),
        grade = j['grade'] as String?,
        passed = j['passed'] as bool?;
  final String subjectName;
  final double maxMarks;
  final String status;
  final double? marks;
  final String? grade;
  final bool? passed;
}

class ProgressPoint {
  ProgressPoint.fromJson(Map<String, dynamic> j)
      : examName = j['exam_name'] as String,
        percentage = _num(j['percentage']);
  final String examName;
  final double? percentage;
}

class DashboardSummary {
  DashboardSummary.fromJson(Map<String, dynamic> j)
      : examName = j['exam_name'] as String,
        students = j['students'] as int,
        withResults = j['students_with_results'] as int,
        average = _num(j['average_percent']),
        passRate = _num(j['pass_percent']),
        published = j['sections_published'] as int,
        sectionsTotal = j['sections_total'] as int;
  final String examName;
  final int students;
  final int withResults;
  final double? average;
  final double? passRate;
  final int published;
  final int sectionsTotal;
}

class AttentionStudent {
  AttentionStudent.fromJson(Map<String, dynamic> j)
      : fullName = j['full_name'] as String,
        sectionName = j['section_name'] as String,
        percentage = _num(j['percentage']),
        reasons = (j['reasons'] as List).cast<String>();
  final String fullName;
  final String sectionName;
  final double? percentage;
  final List<String> reasons;
}

class Exam {
  Exam.fromJson(Map<String, dynamic> j)
      : id = j['id'] as String,
        name = j['name'] as String,
        startDate = j['start_date'] as String?;
  final String id;
  final String name;
  final String? startDate;
}

class Assignment {
  Assignment.fromJson(Map<String, dynamic> j)
      : sectionId = j['section_id'] as String,
        sectionName = j['section_name'] as String,
        classId = j['class_id'] as String,
        subjectId = j['subject_id'] as String,
        subjectName = j['subject_name'] as String,
        academicYearId = j['academic_year_id'] as String,
        studentCount = j['student_count'] as int;
  final String sectionId;
  final String sectionName;
  final String classId;
  final String subjectId;
  final String subjectName;
  final String academicYearId;
  final int studentCount;
}

class MarkRow {
  MarkRow.fromJson(Map<String, dynamic> j)
      : studentId = j['student_id'] as String,
        fullName = j['full_name'] as String,
        rollNo = j['roll_no'] as String?,
        status = j['status'] as String?,
        marks = _num(j['marks']);
  final String studentId;
  final String fullName;
  final String? rollNo;
  final String? status;
  final double? marks;

  String get display {
    if (status == 'ABSENT') return 'AB';
    if (status == 'EXEMPT') return 'EX';
    if (marks == null) return '';
    return marks! == marks!.roundToDouble() ? marks!.toInt().toString() : marks!.toString();
  }
}

class MarksGridData {
  MarksGridData.fromJson(Map<String, dynamic> j)
      : title = '${j['exam_name']} · ${j['subject_name']} · ${j['section_name']}',
        maxMarks = _num(j['max_marks']) ?? 0,
        canEdit = j['can_edit'] as bool,
        rows = (j['rows'] as List).map((e) => MarkRow.fromJson(e as Map<String, dynamic>)).toList();
  final String title;
  final double maxMarks;
  final bool canEdit;
  final List<MarkRow> rows;
}

String fmtPct(double? v) {
  if (v == null) return '–';
  final s = v.toStringAsFixed(2).replaceAll(RegExp(r'\.?0+$'), '');
  return '$s%';
}

String fmtNum(double? v) {
  if (v == null) return '–';
  return v == v.roundToDouble() ? v.toInt().toString() : v.toStringAsFixed(2).replaceAll(RegExp(r'0+$'), '');
}
