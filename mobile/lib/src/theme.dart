import 'package:flutter/material.dart';

const brandBlue = Color(0xFF1F4E79);

/// Large text and high contrast for parents who are new to apps (MVP_SPEC §9).
ThemeData buildTheme(Brightness brightness) {
  final scheme = ColorScheme.fromSeed(seedColor: brandBlue, brightness: brightness);
  final base = ThemeData(colorScheme: scheme, useMaterial3: true, brightness: brightness);
  return base.copyWith(
    // englishLike2021 supplies the font sizes that fontSizeFactor scales.
    textTheme: Typography.englishLike2021.merge(base.textTheme).apply(fontSizeFactor: 1.05),
    inputDecorationTheme: const InputDecorationTheme(border: OutlineInputBorder()),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52), textStyle: const TextStyle(fontSize: 17)),
    ),
    cardTheme: const CardThemeData(margin: EdgeInsets.zero),
  );
}
