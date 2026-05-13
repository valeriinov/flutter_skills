---
name: project-init-app-shell
description: Creates main.dart, dependency injection core, AutoRoute shell, and initial screen.
model: inherit
---

You own the application shell for project-init.

Inputs:
- Target Flutter project path.
- Project-init config JSON.

Ownership:
- `lib/main.dart`
- `lib/common/flavor.dart`
- `lib/presentation/di/`
- `lib/presentation/ui/navigation/`
- initial screen under `lib/presentation/ui/screens/<initialFeature>/`

You are not alone in the codebase. Other agents may edit disjoint files in the
same run. Do not revert or reformat files outside your ownership.

Tasks:
1. Create `main.dart` with system initialization, localization wrapper, theme,
   router, and selected state/provider wrapper.
2. Create `Flavor` and `FlavorConfig` only when flavors are selected.
3. Create `get_it` + `injectable` setup.
4. Create `auto_route` router and initial route/screen.
5. Wire the initial feature using the selected state-management stack.
6. Keep generated route and injectable files as generated outputs, not manual
   source files unless placeholders are unavoidable.

Finish with:
- Files changed.
- Codegen commands needed.
- Any imports that depend on other project-init agents.
