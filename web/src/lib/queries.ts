import { api, unwrap, type Schemas } from "./api";

export type Year = Schemas["AcademicYearOut"];
export type SchoolClass = Schemas["ClassOut"];
export type Subject = Schemas["SubjectOut"];
export type Section = Schemas["SectionOut"];
export type Teacher = Schemas["TeacherOut"];
export type Exam = Schemas["ExamOut"];
export type ExamSubject = Schemas["ExamSubjectOut"];

export const getYears = () => unwrap(api.GET("/api/v1/academic-years"));
export const getClasses = () => unwrap(api.GET("/api/v1/classes"));
export const getSubjects = () => unwrap(api.GET("/api/v1/subjects"));
export const getSections = (academicYearId?: string) =>
  unwrap(api.GET("/api/v1/sections", { params: { query: { academic_year_id: academicYearId } } }));
export const getAllTeachers = () =>
  unwrap(api.GET("/api/v1/teachers", { params: { query: { page: 1, page_size: 500 } } })).then((p) => p.items);
export const getExams = (academicYearId?: string) =>
  unwrap(api.GET("/api/v1/exams", { params: { query: { academic_year_id: academicYearId } } }));
export const getExamSubjects = (examId: string) =>
  unwrap(api.GET("/api/v1/exams/{exam_id}/subjects", { params: { path: { exam_id: examId } } }));

export function currentYear(years: Year[] | undefined): Year | undefined {
  return years?.find((y) => y.is_current) ?? years?.[0];
}
