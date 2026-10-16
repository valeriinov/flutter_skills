# AGENTS.md

## Naming Conventions

- Locale keys: camelCase, ending in the role of the UI element (`Title`, `Button`, `Descr`, `Error`, `Toast`): `spacesTitle`, `bookDeskButton`, `phoneFormatError`.

## Localization

- Brief: `docs/brief.md`; approval queue: `docs/approval-queue.md` beside it.
- UI strings go through ux-translate:
  - adding a key → Add key;
  - editing a translation → Translate or Review;
  - editing the text of an existing key → Add key with the named key.
- before a PR — ux-translate, Pending check; its warnings go into the PR description.
