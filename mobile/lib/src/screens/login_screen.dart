import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../auth/auth.dart';
import '../l10n/strings.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

enum _Step { phone, otp, role, student }

class _LoginScreenState extends ConsumerState<LoginScreen> {
  _Step _step = _Step.phone;
  final _phone = TextEditingController();
  final _otp = TextEditingController();
  final _school = TextEditingController();
  final _admission = TextEditingController();
  final _pin = TextEditingController();
  OtpResult? _otpResult;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    for (final c in [_phone, _otp, _school, _admission, _pin]) {
      c.dispose();
    }
    super.dispose();
  }

  AuthController get _auth => ref.read(authProvider.notifier);

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
    } catch (e) {
      if (mounted) setState(() => _error = ApiException.from(e).message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _sendOtp() => _run(() async {
        await _auth.requestOtp(_phone.text.trim());
        setState(() => _step = _Step.otp);
      });

  Future<void> _verify() => _run(() async {
        final result = await _auth.verifyOtp(_phone.text.trim(), _otp.text.trim());
        if (result.roles.isEmpty) {
          setState(() => _error = S.t('login.noRoles'));
        } else if (result.roles.length == 1) {
          await _auth.chooseRole(result.ticket, result.roles.first.roleId);
        } else {
          setState(() {
            _otpResult = result;
            _step = _Step.role;
          });
        }
      });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Icon(Icons.school_outlined, size: 56, color: theme.colorScheme.primary),
                  const SizedBox(height: 8),
                  Text(S.t('appName'),
                      textAlign: TextAlign.center,
                      style: theme.textTheme.headlineMedium?.copyWith(
                        color: theme.colorScheme.primary,
                        fontWeight: FontWeight.w700,
                      )),
                  const SizedBox(height: 32),
                  if (_error != null) ...[
                    Text(_error!, style: TextStyle(color: theme.colorScheme.error)),
                    const SizedBox(height: 12),
                  ],
                  ..._stepBody(theme),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  List<Widget> _stepBody(ThemeData theme) {
    switch (_step) {
      case _Step.phone:
        return [
          TextField(
            controller: _phone,
            keyboardType: TextInputType.phone,
            autofillHints: const [AutofillHints.telephoneNumber],
            style: const TextStyle(fontSize: 20),
            decoration: InputDecoration(labelText: S.t('login.phone'), helperText: S.t('login.phoneHint')),
          ),
          const SizedBox(height: 16),
          FilledButton(onPressed: _busy ? null : _sendOtp, child: Text(S.t('login.sendOtp'))),
          const SizedBox(height: 16),
          TextButton(onPressed: () => setState(() => _step = _Step.student), child: Text(S.t('login.student'))),
        ];
      case _Step.otp:
        return [
          Text(S.t('login.otpSent', {'phone': _phone.text})),
          const SizedBox(height: 12),
          TextField(
            controller: _otp,
            keyboardType: TextInputType.number,
            autofillHints: const [AutofillHints.oneTimeCode],
            maxLength: 6,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 28, letterSpacing: 12),
            decoration: InputDecoration(labelText: S.t('login.otp'), counterText: ''),
          ),
          const SizedBox(height: 16),
          FilledButton(onPressed: _busy ? null : _verify, child: Text(S.t('login.verify'))),
          TextButton(onPressed: () => setState(() => _step = _Step.phone), child: Text(S.t('login.changeNumber'))),
        ];
      case _Step.role:
        return [
          Text(S.t('login.pickRole'), style: theme.textTheme.titleLarge),
          const SizedBox(height: 12),
          for (final r in _otpResult!.roles)
            Card(
              child: ListTile(
                title: Text(S.t('role.${r.role}')),
                subtitle: r.schoolName == null ? null : Text(r.schoolName!),
                trailing: const Icon(Icons.chevron_right),
                onTap: _busy ? null : () => _run(() => _auth.chooseRole(_otpResult!.ticket, r.roleId)),
              ),
            ),
        ];
      case _Step.student:
        return [
          Text(S.t('login.student'), style: theme.textTheme.titleLarge),
          const SizedBox(height: 12),
          TextField(
            controller: _school,
            textCapitalization: TextCapitalization.characters,
            decoration: InputDecoration(labelText: S.t('login.schoolCode')),
          ),
          const SizedBox(height: 12),
          TextField(controller: _admission, decoration: InputDecoration(labelText: S.t('login.admissionNo'))),
          const SizedBox(height: 12),
          TextField(
            controller: _pin,
            obscureText: true,
            keyboardType: TextInputType.number,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            decoration: InputDecoration(labelText: S.t('login.pin')),
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _busy
                ? null
                : () => _run(() => _auth.studentLogin(_school.text.trim(), _admission.text.trim(), _pin.text.trim())),
            child: Text(S.t('login.submit')),
          ),
          TextButton(onPressed: () => setState(() => _step = _Step.phone), child: Text(S.t('login.parent'))),
        ];
    }
  }
}
