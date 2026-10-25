import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/auth.dart';
import '../l10n/strings.dart';
import '../widgets/common.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    if (auth is! SignedIn) return const SizedBox.shrink();
    final me = auth.me;
    return Scaffold(
      appBar: AppBar(title: Text(S.t('profile.title'))),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        ListTile(
          leading: const CircleAvatar(child: Icon(Icons.person)),
          title: Text(me.fullName, style: Theme.of(context).textTheme.titleLarge),
          subtitle: Text([S.t('role.${me.role}'), if (me.schoolName != null) me.schoolName!].join(' · ')),
        ),
        const Divider(),
        for (final r in me.otherRoles)
          ListTile(
            leading: const Icon(Icons.swap_horiz),
            title: Text('${S.t('profile.switch')} ${S.t('role.${r.role}')}'),
            subtitle: r.schoolName == null ? null : Text(r.schoolName!),
            onTap: () async {
              try {
                await ref.read(authProvider.notifier).switchRole(r.roleId);
                if (context.mounted) Navigator.of(context).popUntil((route) => route.isFirst);
              } catch (e) {
                if (context.mounted) showError(context, e);
              }
            },
          ),
        const SizedBox(height: 24),
        OutlinedButton.icon(
          icon: const Icon(Icons.logout),
          label: Text(S.t('profile.logout')),
          onPressed: () async {
            await ref.read(authProvider.notifier).logout();
            if (context.mounted) Navigator.of(context).popUntil((route) => route.isFirst);
          },
        ),
      ]),
    );
  }
}

class UnsupportedRoleScreen extends ConsumerWidget {
  const UnsupportedRoleScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
        appBar: AppBar(title: Text(S.t('appName')), actions: profileAction(context)),
        body: EmptyMessage('${S.t('unsupported.title')}\n\n${S.t('unsupported.body')}'),
      );
}
