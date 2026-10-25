import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../config.dart';
import '../l10n/strings.dart';

/// Error shape from the API: { "error": { "code", "message", "details" } }.
class ApiException implements Exception {
  ApiException(this.status, this.code, this.message, [this.details]);
  final int status;
  final String code;
  final String message;
  final Object? details;

  factory ApiException.from(Object error) {
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map && data['error'] is Map) {
        final e = data['error'] as Map;
        return ApiException(error.response?.statusCode ?? 0, '${e['code']}', '${e['message']}', e['details']);
      }
      if (error.type == DioExceptionType.connectionError || error.type == DioExceptionType.connectionTimeout) {
        return ApiException(0, 'NETWORK', S.t('common.network'));
      }
      return ApiException(error.response?.statusCode ?? 0, 'HTTP_ERROR', S.t('common.error'));
    }
    if (error is ApiException) return error;
    return ApiException(0, 'UNKNOWN', S.t('common.error'));
  }

  @override
  String toString() => message;
}

/// Tokens: access token in memory; rotating refresh token in Android Keystore-backed secure storage.
class TokenStore {
  TokenStore([FlutterSecureStorage? storage]) : _storage = storage ?? const FlutterSecureStorage();
  final FlutterSecureStorage _storage;
  static const _refreshKey = 'refresh_token';
  String? accessToken;

  Future<String?> readRefresh() => _storage.read(key: _refreshKey);
  Future<void> save(String access, String? refresh) async {
    accessToken = access;
    if (refresh != null) await _storage.write(key: _refreshKey, value: refresh);
  }

  Future<void> clear() async {
    accessToken = null;
    await _storage.delete(key: _refreshKey);
  }
}

class ApiClient {
  ApiClient(this.tokens, {void Function()? onAuthLost}) : _onAuthLost = onAuthLost {
    dio = Dio(BaseOptions(
      baseUrl: '${AppConfig.apiBaseUrl}/api/v1',
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 30),
    ));
    dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) {
        final token = tokens.accessToken;
        if (token != null) options.headers['Authorization'] = 'Bearer $token';
        handler.next(options);
      },
      onError: (error, handler) async {
        final req = error.requestOptions;
        final is401 = error.response?.statusCode == 401;
        if (is401 && !req.path.startsWith('/auth/') && req.extra['retried'] != true) {
          if (await refresh()) {
            req.extra['retried'] = true;
            req.headers['Authorization'] = 'Bearer ${tokens.accessToken}';
            try {
              return handler.resolve(await dio.fetch(req));
            } on DioException catch (e) {
              return handler.next(e);
            }
          }
          _onAuthLost?.call();
        }
        handler.next(error);
      },
    ));
  }

  final TokenStore tokens;
  late final Dio dio;
  final void Function()? _onAuthLost;
  Future<bool>? _refreshing;

  /// Rotate the refresh token (single flight).
  Future<bool> refresh() {
    return _refreshing ??= () async {
      try {
        final token = await tokens.readRefresh();
        if (token == null) return false;
        final res = await dio.post<Map<String, dynamic>>('/auth/refresh', data: {'refresh_token': token});
        await tokens.save(res.data!['access_token'] as String, res.data!['refresh_token'] as String?);
        return true;
      } catch (_) {
        await tokens.clear();
        return false;
      } finally {
        _refreshing = null;
      }
    }();
  }

  Future<T> get<T>(String path, {Map<String, dynamic>? query}) async {
    try {
      final res = await dio.get<T>(path, queryParameters: query);
      return res.data as T;
    } catch (e) {
      throw ApiException.from(e);
    }
  }

  Future<T> post<T>(String path, Object? body) async {
    try {
      final res = await dio.post<T>(path, data: body);
      return res.data as T;
    } catch (e) {
      throw ApiException.from(e);
    }
  }

  Future<T> put<T>(String path, Object? body) async {
    try {
      final res = await dio.put<T>(path, data: body);
      return res.data as T;
    } catch (e) {
      throw ApiException.from(e);
    }
  }

  Future<void> download(String path, String savePath) async {
    try {
      await dio.download(path, savePath);
    } catch (e) {
      throw ApiException.from(e);
    }
  }
}
