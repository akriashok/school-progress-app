import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'src/auth/auth.dart';
import 'src/l10n/strings.dart';
import 'src/screens/consent_screen.dart';
import 'src/screens/family_screens.dart';
import 'src/screens/login_screen.dart';
import 'src/screens/principal_screen.dart';
import 'src/screens/teacher_screens.dart';
import 'src/screens/profile_screen.dart';
import 'src/theme.dart';

void main() {
  runApp(const ProviderScope(child: VidyaTrackApp()));
}

class VidyaTrackApp extends StatelessWidget {
  const VidyaTrackApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: S.t('appName'),
      theme: buildTheme(Brightness.light),
      darkTheme: buildTheme(Brightness.dark),
      debugShowCheckedModeBanner: false,
      home: const RootScreen(),
    );
  }
}

/// Picks the home screen from the auth state and the signed-in role.
class RootScreen extends ConsumerWidget {
  const RootScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    return switch (auth) {
      AuthLoading() => const Scaffold(body: Center(child: CircularProgressIndicator())),
      SignedOut() => const LoginScreen(),
      SignedIn(:final me) when me.consentRequired => const ConsentScreen(),
      SignedIn(:final me) => switch (me.role) {
          'PARENT' => const ChildrenScreen(),
          'STUDENT' => StudentHomeScreen(studentId: me.studentId!, title: me.fullName),
          'PRINCIPAL' || 'SCHOOL_ADMIN' => const PrincipalScreen(),
          'TEACHER' => const TeacherHomeScreen(),
          _ => const UnsupportedRoleScreen(),
        },
    };
  }
}
