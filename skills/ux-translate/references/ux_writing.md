# UX writing rules

Read by the translator before the first draft and by the reviewer for every finding. These rules
hold for any target language; the language pack (`references/lang/<code>.md`) adds the language's
own conventions and wins where they differ. Keep meaning, action and consequence of the source;
rewrite the wording for the target language's mobile UI; add nothing the source and its context
do not say.

## By element class

- **Button / CTA** — a verb naming the result, no article, no period: `Скасувати замовлення` → `Cancel order`, not `Cancel the order.`
- **Button / CTA** — the label names the action, not a generic answer: `Delete file`, not `OK`.
- **Title** — a short noun phrase or the task, no verb echoing the button below: `Notifications`, not `Manage your notifications settings`.
- **Description** — one fact or consequence the title does not already say: `Files stay on this device until you sync`, not `This screen shows your files`.
- **Error** — what failed and what to do next, in plain words: `Couldn’t send the message. Check your connection`, not `Error occurred`.
- **Error** — no blame, no system jargon: `That code has expired`, not `Invalid input: token expired (401)`.
- **Empty state** — what will appear here and how to get it: `No saved items yet. Tap ♡ to save one`, not `List is empty`.
- **Permission request** — why the app needs it, in the user's benefit, before the system dialog: `Allow notifications to know when a reply arrives`, not `The app requires notification permission`.
- **Toast / snackbar** — the result only, past or state form: `Зміни успішно збережено` → `Changes saved`.
- **Confirmation dialog** — the question names the irreversible fact; buttons repeat the action: `Delete 3 files?` + `Delete` / `Cancel`, not `Are you sure?` + `Yes` / `No`.
- **Accessibility label** — what the control is or does, not how it looks: `Close`, not `X icon`; `Search`, not `Magnifier button`.
- **Push notification** — meaningful without the app open; who or what + what happened: `New message from {name}`, not `You have an update`.

## Translation anti-patterns

- **Politeness filler** — drop "please", "kindly" and their equivalents unless the brief asks for them: `Будь ласка, увійдіть, щоб продовжити` → `Sign in to continue`.
- **"Successfully"** — the result itself says it worked: `File successfully uploaded` → `File uploaded`.
- **Nominalisation** — a verb instead of an action noun: `Perform verification of the email` → `Verify email`.
- **Repeated screen context** — do not restate what the title or screen already shows: on a profile screen `Edit profile information` → `Edit`.
- **Source word order** — rebuild the sentence for the target language: `У вас залишилося 2 елементи` → `2 items left`, not `You have 2 items remaining`.
- **Literal idiom** — translate the meaning, not the image: `Все пропало` → `Something went wrong`, not `Everything is lost`.
- **Passive bureaucratic voice** — say who acts: `Request has been received by the system` → `We got your request`.
- **Invented content** — no extra reassurance, emoji or exclamation the source lacks: `Saved` stays `Saved`, not `Saved! 🎉`.

## Length budget

- **`tight`** (button, tab, chip, screen title, inline label, text with `maxLines`, ellipsis or fixed width) — no longer than `limit`: `Зберегти зміни` (14) → `Save changes` (12).
- **`limit`** — the brief's explicit limit, otherwise the source length; `limit_hard: true` only when the brief says the limit is hard: a 12-character tab with `limit_hard` fails the check at 13.
- **`loose`** (description, error body, dialog body, empty-state text) — no length limit; still no filler: `Couldn’t load the list. Pull down to retry`.
- **Shortening order** — apply in this order until it fits, stop as soon as it fits:
  1. drop politeness: `Please enter your code` → `Enter your code`;
  2. drop repeated screen context: `Save profile changes` → `Save changes`;
  3. verb instead of nominalisation: `Start the download` → `Download`;
  4. shorter synonym with the same meaning: `Purchase` → `Buy`, `Modify` → `Edit`;
  5. drop an article or a possessive the target language allows: `Open your settings` → `Open settings`.
- **Never shorten by** an abbreviation, a cut word or a lost consequence: `Settings`, not `Sett.`; `Delete account` stays two words, not `Delete`.
- **Never shorten a button** into a bare noun that reads as another action: `До архіву` (opens the archive) → `View archive`, not `Archive` (reads as "archive this"); over the limit, keep the verb and report "decide: text or layout".
- **Still too long** — keep the full meaning, mark it in the report as "decide: text or layout": `Підтвердити адресу електронної пошти` (36) on a 20-character button.
- **Ratio corridor** — the language pack gives the expected target/source length ratio; strings under ~10 characters are not rated: much longer → on-screen check list; much shorter → re-read for lost meaning.

## Risk classes

- **`payment`** — charges, refunds, payouts, prices, balance, failed payment: the money action stays named: `Не вдалося здійснити оплату {amount}` → `Payment of {amount} failed`, not `Couldn’t process {amount}`.
- **`security`** — sign-in, password, codes, sessions, account or data deletion: the consequence stays explicit: `All your data will be deleted. This can’t be undone`.
- **`legal`** — consent, terms, privacy, age, regulatory notices: terms from the brief only, no shortening for brevity: `I agree to the Terms of Use and Privacy Policy` keeps both document names.
- **Handling** — draft it, set `risk` to the class (`payment`, `security`, `legal`; else `none`), and list it under "needs a human" in the report: `{"key": "payFailed", "risk": "payment", ...}`.
- **Risk beats length** — on a `tight` risk string never drop the money, the irreversibility or the legal term to fit; report it instead: `Pay {amount}` over a limit stays, "decide: text or layout".
- **Accepted translation** — never overwritten without the user naming the key, risk class or not.

## Ambiguity

- **Unclear meaning** — a skip with a reason, never a guess: `{"key": "order", "skip": true, "reason": "noun or verb: no call site found"}`.
- **Placeholders** — byte-identical, same count; reorder freely: `{count} of {total}` → `{count} з {total}`, never `{n} з {total}`.
- **Plurals** — rebuild into the target language's CLDR categories, keep the argument name and `#`: `one {# file} other {# files}` → `one {# файл} few {# файли} many {# файлів} other {# файлу}`.

## Self-check per string

- **Meaning** — would a user act the same way on the source and on the draft? `Cancel order` ≠ `Close order`.
- **Action** — does a button still say what happens on tap? `Continue` hides a payment; `Pay {amount}` does not.
- **Naturalness** — would a native writer put this on a phone screen, unprompted? `Changes saved`, not `Changes have been successfully saved`.
- **Length** — within `limit` for `tight`, ratio within the corridor or a reason why: `Save` (4) for `Зберегти` (8) passes, short strings are not rated.
- **Term** — every brief term rendered as the brief says, no do-not-use word: `item` if the brief says `item`, never a synonym chosen for variety.
