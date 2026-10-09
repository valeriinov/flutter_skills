# Localization brief

## Product
A coworking app: guests book desks in spaces run by hosts.

## Languages and files
| language | code | file | role |
|---|---|---|---|
| Ukrainian | uk | `uk.json` | source |
| English | en | `en.json` | target, seeded with the source |

## Voice and register
- uk «ви», lower-case; en "you", sentence case, contractions, US spelling.
- Source: `docs/voice-guide.md`.

## Terms
| term (source UI word) | en | do not translate | meaning in this product | source variants to flag | source |
|---|---|---|---|---|---|
| адміністратор | host | | person who runs a space | менеджер | voice guide |
| бронювання | booking | | a guest's hold on a desk | резерв | voice guide |
| простір | space | | a coworking location | | voice guide |

## Do not use
| word | use instead | source |
|---|---|---|
| en: manager, admin | host | decision |
| en: reservation | booking | decision |

## Intentionally identical
| key | why |
|---|---|

## Gap rule
A missing key, an empty value, or a value equal to the source.

## String context source
- Code: `lib/`, keys named in comments of each screen.
- Screenshots: none.

## Length limits
| element or key | limit (characters) | hard | source |
|---|---|---|---|

## Text component catalogue
| component | ui (tight/loose) | maxLines | note |
|---|---|---|---|
| `FixedWidthButton` | tight | 1 | 96 px, ellipsis |
| `TextField` errorText | loose | 2 | |

## Risk keys
| key or prefix | risk class | why |
|---|---|---|
| `deleteAccountTitle` | security | account deletion |

## Batch plan
| batch | key prefix | strings | risk |
|---|---|---|---|
| all | — | 17 | security |

## Decisions
| decision | language | date |
|---|---|---|

## Open questions
- None.
