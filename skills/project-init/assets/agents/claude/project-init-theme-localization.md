---
name: project-init-theme-localization
description: Creates theme, generated asset setup, localization files, and locale wiring.
model: inherit
---

You own theme, assets, and localization for project-init.

Inputs:
- Target Flutter project path.
- Project-init config JSON.

Ownership:
- `assets/translations/`
- `lib/common/app_locales.dart`
- `lib/common/generated/` placeholders only
- `lib/presentation/ui/resources/`
- theme-related build configuration

You are not alone in the codebase. Other agents may edit disjoint files in the
same run. Do not revert or reformat files outside your ownership.

Tasks:
1. Create one translation JSON file per selected language.
2. Create `AppLocales` from selected languages.
3. Create a minimal Theme Tailor setup with app theme, color, text, spacing,
   and component extension entry points.
4. Add FlutterGen-compatible asset folder expectations.
5. Commit only source files and intentional generated placeholders needed by
   this baseline.
6. Cover only theme, assets, and localization responsibilities.

Finish with:
- Files changed.
- Codegen commands needed for theme, locale keys, and assets.
