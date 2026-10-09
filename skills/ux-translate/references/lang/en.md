# Language pack

Language: English (`en`). Pair language: Ukrainian (`uk`). Read with `references/ux_writing.md`; this pack wins where they differ, the brief wins over both. Default variant is US English; en-GB spelling (`favourite`, `cancelled`) only when the brief says so.

## Register and address

- Address the user as `you`; the app speaks as `we` only when the brief allows it: `We sent a code to {email}`.
- Contractions are the default in UI: `Couldn’t save`, `You’re offline`, `Don’t show again`.
- No contractions in legal text and where the brief's voice is formal: `You do not have access`.
- Calm and direct: no exclamation marks, no `Oops`, no `Whoops`: `Something went wrong`, not `Oops! Something went wrong!`.
- No `please` in buttons, titles or errors; keep it only in a request that costs the user effort, if the brief allows: `Enter your code`.

## Capitalisation

- Sentence case everywhere in UI — titles, buttons, tabs, menu items: `Change password`, not `Change Password`.
- Proper names and brief terms keep their own case: `Sign in with Google`.
- No ALL CAPS in the string; uppercase buttons are a style, not text: write `Continue`, not `CONTINUE`.
- After a colon in a label, lowercase unless a proper name follows: `Status: active`.

## Punctuation and typography

- No period in buttons, tabs, titles, labels, toasts of one phrase: `Changes saved`.
- A period ends a full sentence in a description, error body or dialog body: `Check your connection and try again.`
- Two sentences in one string — both end with a period: `Couldn’t load the list. Pull down to retry.`
- Curly quotes `“ ”` and apostrophe `’` in UI text: `Can’t find “{name}”`; straight quotes only when the brief says the font lacks curly ones.
- Ellipsis `…` (one character) for an action that opens more input, and for progress: `Uploading…`, `Save as…`.
- En dash `–` for ranges, no spaces: `9:00–18:00`; em dash `—` without spaces for a break in a sentence.
- Oxford comma per the brief; default US style uses it: `Photos, videos, and files`.
- A non-breaking space between a number and its unit: `10 MB`.

## Numbers, dates, currency

- Thousands with a comma, decimals with a point: `1,250.50`.
- Dates in US English: `Oct 9, 2026` short, `October 9, 2026` long; numeric `10/09/2026` only when the brief asks.
- Times: 12-hour with `AM`/`PM` in en-US: `6:30 PM`; 24-hour only when the brief says so.
- Currency symbol before the amount, no space: `$12.50`; a currency code with a space: `UAH 250`.
- Relative dates: `Today`, `Yesterday`, `2 days ago`, `in 5 min`.
- A literal number in the source is rewritten in target format; a placeholder `{amount}` is never formatted by hand.

## Plural categories

- CLDR categories: `one`, `other`; `zero` only when the source or brief asks for a distinct zero text.
- `one` covers exactly 1: `one {# file}` `other {# files}`.
- `other` covers 0, 2+ and fractions: `0 files`, `1.5 files`.
- A Ukrainian source with `one/few/many/other` collapses to `one/other`: drop `few` and `many`, keep the argument name.
- A plural noun without a number reads naturally: `one {Delete file?}` `other {Delete # files?}`.

## Gender-neutral phrasing

- Use `they` for a person of unknown gender: `{name} added you. Reply to them`.
- Role nouns without gender: `chairperson`, `staff`, `user`; never `he/she`.
- Address the reader directly instead of a third person: `You’re signed in`, not `The user is signed in`.
- Ukrainian gender agreement in the source (`Він/Вона`, `зареєстрований/зареєстрована`) collapses to one English form: `You’re registered`.

## Button and CTA conventions

- Imperative verb + object, no article: `Add item`, `Send message`, `View details`.
- One verb when the screen already names the object: on a message screen `Send`, not `Send message`.
- Standard verbs: `Sign in` / `Sign out` / `Sign up` (not `Log in` unless the brief says so), `Save`, `Cancel`, `Delete`, `Remove`, `Edit`, `Done`, `Next`, `Back`, `Retry`, `Continue`.
- `Delete` destroys; `Remove` takes out of a list and keeps the thing: `Remove from list`.
- A dialog about cancelling something never pairs `Cancel` with `Cancel`: `Cancel subscription?` → `Cancel subscription` / `Keep`.
- Destructive confirmation repeats the verb: `Delete 3 files?` → `Delete` / `Cancel`.

## Calques from the pair language

- `Будь ласка, увійдіть у свій обліковий запис, щоб продовжити` → `Sign in to continue`, not `Please log in to your account in order to continue`.
- `Переглянути детальну інформацію` → `View details`, not `View detailed information`.
- `Зміни успішно збережено` → `Changes saved`, not `Changes have been successfully saved`.
- `Скасувати замовлення` → `Cancel order`, not `Cancel the order`.
- `У вас залишилося 2 елементи` → `2 items left`, not `You have 2 items remaining`.
- `Не вдалося завантажити дані` → `Couldn’t load data`, not `It was not possible to load data`.
- `Виникла помилка` → `Something went wrong`, not `An error has arisen`.
- `Здійснити оплату` → `Pay`, not `Carry out the payment`.
- `Введіть, будь ласка, коректний email` → `Enter a valid email`, not `Please enter a correct email`.
- `Ви впевнені, що хочете вийти?` → `Sign out?`, not `Are you sure you want to exit?`.
- `Дані відсутні` → `No data yet`, not `Data is absent`.
- `Надати доступ` → `Allow access`, not `Grant access` unless the brief uses it.
- `На жаль, …` → drop it: `На жаль, сталася помилка` → `Something went wrong`.

## Common UI terms

- `Налаштування` → `Settings`; `Профіль` → `Profile`; `Сповіщення` → `Notifications`.
- `Пошук` → `Search`; `Фільтри` → `Filters`; `Скинути` (filters) → `Reset`, `Clear all` for many.
- `Повторити спробу` → `Try again` in a body, `Retry` on a tight button.
- `Завантажити` is ambiguous: `Download` (to device) or `Upload` (to server) — decide from context or skip with a reason.
- `Обліковий запис` → `Account`; `Вийти` (account) → `Sign out`, (screen) → `Close` or `Back`.
- `Електронна пошта` → `Email`; `Пароль` → `Password`; `Код підтвердження` → `Verification code`.

## Length ratio

- Expected en/uk length ratio: about 0.7–0.9 — English is usually shorter than the Ukrainian source.
- Checker corridor (warning bounds) when the target is `en`: `--ratio 0.3,1.4` — wider than the expected ratio, so a calque cut such as `Електронна пошта` → `Email` (0.31) passes.
- Strings under ~10 characters are not rated.
- Much longer than the corridor → on-screen check list; much shorter → re-read for lost meaning.
- The corridor is a starting value; refine it from the ratios of accepted strings in the project.
