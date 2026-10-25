import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/auth.dart';
import '../l10n/strings.dart';
import '../widgets/common.dart';

final consentProvider = FutureProvider.autoDispose<Map<String, dynamic>>(
  (ref) => ref.read(apiProvider).get<Map<String, dynamic>>('/consent/current'),
);

class ConsentScreen extends ConsumerStatefulWidget {
  const ConsentScreen({super.key});

  @override
  ConsumerState<ConsentScreen> createState() => _ConsentScreenState();
}

class _ConsentScreenState extends ConsumerState<ConsentScreen> {
  bool _busy = false;

  Future<void> _accept(int version) async {
    setState(() => _busy = true);
    try {
      await ref.read(apiProvider).post<Map<String, dynamic>>('/consent/accept', {'version': version});
      await ref.read(authProvider.notifier).reloadMe();
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final consent = ref.watch(consentProvider);
    return Scaffold(
      appBar: AppBar(title: Text(S.t('consent.title'))),
      body: AsyncBody(
        value: consent,
        onRetry: () => ref.invalidate(consentProvider),
        builder: (c) => Column(children: [
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Text(c['body'] as String, style: Theme.of(context).textTheme.bodyLarge?.copyWith(height: 1.5)),
            ),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(children: [
                FilledButton(
                  onPressed: _busy ? null : () => _accept(c['version'] as int),
                  child: Text(S.t('consent.accept')),
                ),
                TextButton(
                  onPressed: () => ref.read(authProvider.notifier).logout(),
                  child: Text(S.t('profile.logout')),
                ),
              ]),
            ),
          ),
        ]),
      ),
    );
  }
}
