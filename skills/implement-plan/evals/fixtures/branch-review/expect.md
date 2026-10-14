# Expected findings

Lines refer to the `stage-2/` tree.

| file:line | essence |
|---|---|
| `lib/stock_report.dart:15` | reorder condition inverted: lists items above the reorder level instead of those at or below it |
| `lib/restock_service.dart:13` | `save` is not awaited: `restock` completes before the item is stored and a save error is lost |
| `lib/sale_service.dart:16` | `save` is not awaited: `sell` returns `true` before the item is stored and a save error is lost |
| `lib/stock_import.dart:11` | `save` is not awaited in the loop: `importAll` returns the count before any item is stored and a save error is lost |
