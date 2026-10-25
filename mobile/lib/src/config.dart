/// Build-time configuration. Pass with `--dart-define=API_BASE_URL=https://api.example.in`.
/// The default points the Android emulator at a backend running on the host.
class AppConfig {
  static const apiBaseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: 'http://10.0.2.2:8000');
}
