# Expected findings

Lines refer to the `fixed/` tree. The original defect — `lib/price_converter.dart:14` in
`before/` divides by the rate instead of multiplying — is fixed by the change and is not a
finding.

| file:line | essence |
|---|---|
| `lib/price_converter.dart:13` | `RateUnavailableException` from `_rates.rate` is not caught: `convert` throws instead of returning null when no rate is known, so the null branch in `CheckoutSummary.totalLabel` is unreachable and the exception escapes it |

Matching follows `skills/implement-plan/evals/reviewer-recall.md` § Matching: the same file, a line
within ±10 or the symbol `convert`, and the same essence — the exception path of `convert` is
unhandled. The case passes when this finding is reported.
