import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../api/models.dart';

sealed class AuthState {
  const AuthState();
}

class AuthLoading extends AuthState {
  const AuthLoading();
}

class SignedOut extends AuthState {
  const SignedOut();
}

class SignedIn extends AuthState {
  const SignedIn(this.me);
  final Me me;
}

final tokenStoreProvider = Provider<TokenStore>((ref) => TokenStore());

final apiProvider = Provider<ApiClient>((ref) {
  return ApiClient(ref.watch(tokenStoreProvider), onAuthLost: () {
    ref.read(authProvider.notifier).signedOut();
  });
});

class OtpResult {
  OtpResult(this.ticket, this.roles);
  final String ticket;
  final List<RoleOption> roles;
}

class AuthController extends Notifier<AuthState> {
  ApiClient get _api => ref.read(apiProvider);
  TokenStore get _tokens => ref.read(tokenStoreProvider);

  @override
  AuthState build() {
    Future.microtask(restore);
    return const AuthLoading();
  }

  /// Restore a session from the stored refresh token (app stays logged in).
  Future<void> restore() async {
    if (await _api.refresh()) {
      try {
        await reloadMe();
        return;
      } catch (_) {}
    }
    state = const SignedOut();
  }

  Future<void> reloadMe() async {
    final me = Me.fromJson(await _api.get<Map<String, dynamic>>('/me'));
    state = SignedIn(me);
  }

  Future<void> requestOtp(String phone) => _api.post<Map<String, dynamic>>('/auth/otp/request', {'phone': phone});

  Future<OtpResult> verifyOtp(String phone, String otp) async {
    final res = await _api.post<Map<String, dynamic>>('/auth/otp/verify', {'phone': phone, 'otp': otp});
    final roles = (res['roles'] as List).map((e) => RoleOption.fromJson(e as Map<String, dynamic>)).toList();
    return OtpResult(res['ticket'] as String, roles);
  }

  Future<void> chooseRole(String ticket, String roleId) async {
    final res = await _api.post<Map<String, dynamic>>('/auth/session', {'ticket': ticket, 'role_id': roleId});
    await _start(res);
  }

  Future<void> studentLogin(String schoolCode, String admissionNo, String pin) async {
    final res = await _api.post<Map<String, dynamic>>(
      '/auth/student/login',
      {'school_code': schoolCode, 'admission_no': admissionNo, 'pin': pin},
    );
    await _start(res);
  }

  Future<void> switchRole(String roleId) async {
    final res = await _api.post<Map<String, dynamic>>('/auth/switch', {'role_id': roleId});
    await _start(res);
  }

  Future<void> _start(Map<String, dynamic> tokens) async {
    await _tokens.save(tokens['access_token'] as String, tokens['refresh_token'] as String?);
    await reloadMe();
  }

  Future<void> logout() async {
    final refresh = await _tokens.readRefresh();
    try {
      await _api.post<Map<String, dynamic>>('/auth/logout', {'refresh_token': refresh});
    } catch (_) {}
    await _tokens.clear();
    state = const SignedOut();
  }

  void signedOut() {
    _tokens.accessToken = null;
    state = const SignedOut();
  }
}

final authProvider = NotifierProvider<AuthController, AuthState>(AuthController.new);
