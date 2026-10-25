import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vidyatrack/main.dart';
import 'package:vidyatrack/src/api/models.dart';
import 'package:vidyatrack/src/auth/auth.dart';
import 'package:vidyatrack/src/l10n/strings.dart';

/// Auth controller that skips the network and starts signed out.
class _SignedOutAuth extends AuthController {
  @override
  AuthState build() => const SignedOut();
}

void main() {
  group('formatting', () {
    test('percent and numbers', () {
      expect(fmtPct(81.67), '81.67%');
      expect(fmtPct(40), '40%');
      expect(fmtPct(null), '–');
      expect(fmtNum(88), '88');
      expect(fmtNum(47.5), '47.5');
    });

    test('mark row display for AB / EX', () {
      MarkRow row(String? status, Object? marks) => MarkRow.fromJson({
            'student_id': 's',
            'full_name': 'A',
            'roll_no': '1',
            'status': status,
            'marks': marks,
          });
      expect(row('ABSENT', null).display, 'AB');
      expect(row('EXEMPT', null).display, 'EX');
      expect(row('PRESENT', '78.50').display, '78.5');
      expect(row(null, null).display, '');
    });

    test('strings interpolate', () {
      expect(S.t('home.rank', {'rank': 2, 'size': 30}), 'Rank 2 of 30');
    });
  });

  testWidgets('signed-out users see the login screen and can switch to student login', (tester) async {
    await tester.pumpWidget(ProviderScope(
      overrides: [authProvider.overrideWith(_SignedOutAuth.new)],
      child: const VidyaTrackApp(),
    ));
    await tester.pumpAndSettle();
    expect(find.text(S.t('login.sendOtp')), findsOneWidget);
    await tester.tap(find.text(S.t('login.student')));
    await tester.pumpAndSettle();
    expect(find.text(S.t('login.schoolCode')), findsOneWidget);
    expect(find.byType(TextField), findsNWidgets(3));
  });
}
