# Language pack

Language: Ukrainian (`uk`). Pair language: English (`en`). Read with `references/ux_writing.md`; this pack wins where they differ, the brief wins over both. Write Ukrainian as Ukrainian, never through Russian; check every word against current Ukrainian orthography (2019).

## Register and address

- Default address is `ви`, lowercase inside a sentence: `Ви увійшли`, `Ваш код надіслано на {email}`; capital `Ви` only at the start of a sentence.
- `ти` only when the brief sets an informal voice; then hold it in every string: `Введи код`, `Твій профіль`.
- No `будь ласка` in buttons, titles, errors; keep it only where the brief's voice is formal and the user is asked to do effortful work: `Введіть код`.
- No `На жаль` as an opener: `Не вдалося зберегти`, not `На жаль, не вдалося зберегти`.
- No exclamation marks unless the brief allows them: `Готово`, not `Готово!`.

## Capitalisation

- Capital letter only at the start of the string and in proper names: `Змінити пароль`, never `Змінити Пароль`.
- English Title Case in the source is not carried over: `Payment Methods` → `Способи оплати`.
- Months and weekdays are lowercase: `9 жовтня`, `понеділок`.
- Brand and product names keep their own case and are not translated: `Увійти через Google`.
- No ALL CAPS in the string; uppercase buttons are a style: write `Продовжити`.

## Punctuation and typography

- Apostrophe `ʼ` (U+02BC) or `’` per the brief, never `'` or `"`: `пʼять`, `обʼєкт`; one choice for the whole file.
- Quotes `«»` for the outer level, `„“` inside: `Файл «{name}» видалено`.
- Dash `—` with spaces in a sentence: `Помилка — спробуйте ще раз`; en dash `–` without spaces for ranges: `9:00–18:00`.
- No period in buttons, tabs, titles, labels, toasts of one phrase: `Зміни збережено`.
- A period ends a full sentence in a description, error body or dialog body; two sentences — both end with a period.
- Ellipsis `…` (one character) for progress and an action that opens more input: `Завантаження…`.
- A non-breaking space between a number and its unit or currency: `10 МБ`, `250 ₴`.
- Comma before `що`, `щоб`, `якщо`, `коли` in a subordinate clause: `Увійдіть, щоб продовжити`.

## Numbers, dates, currency

- Thousands with a non-breaking space, decimals with a comma: `1 250,50`.
- Dates: `09.10.2026` numeric, `9 жовтня 2026` long, `9 жовт.` short only where the brief allows abbreviations of months.
- Times: 24-hour, colon: `18:30`; no `AM`/`PM`.
- Currency after the amount with a space: `250 ₴` or `250 грн` per the brief; a foreign currency: `12,50 $` or `12,50 USD` per the brief.
- Relative dates: `Сьогодні`, `Учора`, `2 дні тому`, `через 5 хв`.
- A literal number in the source is rewritten in Ukrainian format; a placeholder `{amount}` is never formatted by hand.

## Plural categories

- CLDR categories: `one`, `few`, `many`, `other`; `zero` only when the source or brief asks for a distinct zero text.
- `one` — 1, 21, 31, 101 (not 11): `one {# файл}`.
- `few` — 2–4, 22–24, 32–34 (not 12–14): `few {# файли}`.
- `many` — 0, 5–20, 25–30, 11–14: `many {# файлів}`.
- `other` — fractions: `other {# файлу}` (`1,5 файлу`).
- An English source with `one/other` expands to all four forms; each form carries the source's placeholders and `#` from `other`.
- The verb and adjective agree with the form: `one {Залишився # елемент}` `few {Залишилося # елементи}` `many {Залишилося # елементів}` `other {Залишилося # елемента}`.

## Gender-neutral phrasing

- Past-tense verbs and adjectives about the user carry gender; rebuild the sentence instead: `You're registered` → `Реєстрацію завершено`, not `Ви зареєстрований`.
- Impersonal `-но/-то` forms for results: `Пароль змінено`, `Файл надіслано`.
- A noun of the action instead of a gendered participle: `You're signed in` → `Вхід виконано`.
- About another person: name + verb in present or a neutral noun: `{name} додає вас` or `Запрошення від {name}`, not `{name} додав вас`.
- `ви` with a plural past tense is grammatical and neutral where a form is unavoidable: `Ви увійшли`.

## Button and CTA conventions

- Infinitive, not imperative, on buttons and menu items: `Зберегти`, `Скасувати`, `Видалити`, not `Збережіть`.
- Imperative `ви`-form in instructions and body text: `Введіть код із SMS`.
- Infinitive + object, no possessive: `Додати елемент`, `Надіслати повідомлення`, `Переглянути деталі`.
- One verb when the screen already names the object: on a message screen `Надіслати`.
- Standard verbs: `Увійти` / `Вийти` / `Зареєструватися`, `Зберегти`, `Скасувати`, `Видалити`, `Прибрати`, `Редагувати`, `Готово`, `Далі`, `Назад`, `Повторити`, `Продовжити`.
- Destructive confirmation repeats the verb: `Видалити 3 файли?` → `Видалити` / `Скасувати`.

## Calques from the pair language

- `Sign in to continue` → `Увійдіть, щоб продовжити`, not `Увійдіть для продовження`.
- `Changes saved` → `Зміни збережено`, not `Зміни були збережені`.
- `Something went wrong` → `Щось пішло не так` or `Сталася помилка`, not `Щось пішло неправильно`.
- `Try again` → `Спробуйте ще раз`, not `Спробуйте знову`.
- `Are you sure?` → name the fact: `Видалити файл?`, not `Ви впевнені?`.
- `Make sure that…` → `Перевірте, що…`, not `Переконайтеся в тому, що…`.
- `You have no messages` → `Повідомлень немає`, not `Ви не маєте повідомлень`.
- `Enable notifications` → `Увімкнути сповіщення`, not `Ввімкнути нотифікації`.
- `Take a photo` → `Зробити знімок`, not `Взяти фото`.
- `Apply` (filters) → `Застосувати`, not `Прийняти`.
- `In order to` → `щоб`, not `для того, щоб` in UI.
- `Be careful` → `Обережно`, not `Будьте обережні` on a label.
- `Click here` → name the action: `Відкрити налаштування`, not `Натисніть тут`.

## Common UI terms

- `Settings` → `Налаштування`; `Profile` → `Профіль`; `Notifications` → `Сповіщення`.
- `Search` → `Пошук`; `Filters` → `Фільтри`; `Reset` (filters) → `Скинути`.
- `Retry` → `Повторити` on a tight button, `Спробуйте ще раз` in a body.
- `Download` → `Завантажити`; `Upload` → `Завантажити` or `Вивантажити` per the brief — one choice for the project.
- `Account` → `Обліковий запис`; `Sign out` → `Вийти`; `Close` → `Закрити`.
- `Email` → `Електронна пошта` in labels, `email` only when the brief allows it; `Password` → `Пароль`; `Verification code` → `Код підтвердження`.

## Length ratio

- Expected uk/en length ratio: about 1.1–1.4 — Ukrainian is usually longer than the English source.
- Checker corridor (warning bounds) when the target is `uk`: `--ratio 0.7,1.5` — wider than the expected ratio, so `Notifications` → `Сповіщення` (0.77) passes.
- Strings under ~10 characters are not rated.
- Much longer than the corridor → on-screen check list; much shorter → re-read for lost meaning.
- The corridor is a starting value; refine it from the ratios of accepted strings in the project.
