# Agent brief: German structured PII detection in DataFog Core

## Objective and scope

Implement all seven locale-gated German entity types listed below in
`datafog-core`, with identical
behavior across Rust, Python, Node.js, and browser/WASM bindings. Make it usable
through text scanning, structured scanning, and existing transformation APIs.
All detection logic belongs in `crates/core`; bindings remain thin.

This brief proposes concrete policy choices for implementation. In particular,
it specifies format/context-based PII detection rather than official identifier
or bank-account validation. Passport and residence-permit patterns are explicitly
legacy-compatible heuristics, not exhaustive national document-number coverage.
It does not authorize unrelated detector changes or a global locale redesign.
Do not implement this work in the legacy Python detector.

## Existing behavior and compatibility context

- Python 4.8.1 has `DE_IBAN` and six other locale-gated German labels.
- Its IBAN pattern is case-insensitive, accepts compact or optionally grouped
  values, and does not validate a checksum.
- Core currently accepts `ScanConfig.locale`, but `scan_with_config` ignores it.
- Core scanning returns ordered findings and can retain overlapping candidates;
  transformation selection resolves overlaps separately. Preserve that contract.
- Core already supplies byte/code-point offsets, binding-specific UTF-16 ranges,
  structured field paths, transformations, and detector provenance. Reuse these.

The German structure is 22 characters when normalized: `DE`, two check digits,
an eight-digit bank code, and a ten-digit account component. See the
[Deutsche Bundesbank's IBAN explanation](https://www.bundesbank.de/en/tasks/payment-systems/services/sepa/content/content-831778?index=1).

## R1. Entity identity and findings

Add these exact canonical labels and detector names:

| Entity label                 | Detector name                             |
| ---------------------------- | ----------------------------------------- |
| `DE_IBAN`                    | `datafog-core/de-iban`                    |
| `DE_VAT_ID`                  | `datafog-core/de-vat-id`                  |
| `DE_TAX_ID`                  | `datafog-core/de-tax-id`                  |
| `DE_SOCIAL_SECURITY_NUMBER`  | `datafog-core/de-social-security-number`  |
| `DE_POSTAL_CODE`             | `datafog-core/de-postal-code`             |
| `DE_PASSPORT_NUMBER`         | `datafog-core/de-passport-number`         |
| `DE_RESIDENCE_PERMIT_NUMBER` | `datafog-core/de-residence-permit-number` |

For every new detector:

- Use the current crate version for `detector_version`, as existing detectors do.
- Leave confidence absent (`None`/`null`); do not invent a numeric probability.
- `matched_text` must be the exact source substring, including original casing
  and internal separators. Never return a normalized substitute.
- Emit one finding per occurrence, with the existing ordering/deduplication rules.

## R2. Activation and locale compatibility

- Enable all seven detectors when `locale`, trimmed and compared case-insensitively,
  is `de`, `de-DE`, or `de_DE`.
- Omitted locale does not enable any `DE_*` detector. Existing base detectors still run.
- Other already accepted nonempty locale values retain existing behavior and
  do not activate German detection. Do not begin rejecting `en-US` or other
  values as a side effect of this feature.
- Preserve existing malformed-config and empty-locale errors.
- Normalize for routing without changing the public stored locale value unless
  existing API tests demonstrate that such normalization is already expected.
- Use the same routing for plain scans and structured string-value scans.
- Keep Core's current config shape: `{"locale": "de"}`. Do not introduce Python's
  plural `locales`, a new engine selector, or scan-time entity selection here.
- Transformation entity selection does not activate a detector. A caller wanting
  to scan and transform only German IBANs supplies both the German scan locale
  and `transform.entities: ["DE_IBAN"]`.

## R3. German IBAN lexical forms

Use the following logical grammar, with ASCII digits only:

```text
[Dd][Ee][0-9]{2}(SEP?[0-9]{4}){4}SEP?[0-9]{2}
SEP := one U+0020 SPACE, U+0009 TAB, U+00A0 NO-BREAK SPACE,
       or U+202F NARROW NO-BREAK SPACE
```

- Accept compact, fully grouped, and partially grouped values. Each separator
  is optional independently, but only at the group boundaries in the grammar.
- Do not require a context keyword such as `IBAN` or `Bankverbindung`.
- Do not include context labels, surrounding punctuation, or outer whitespace
  in the match.
- Reject separators after `DE` but before the two check digits, multiple adjacent
  separators, arbitrary grouping, hyphens, periods, and embedded newlines.
- Reject non-ASCII digits, other country prefixes, and wrong normalized length.
- Reject a candidate if its immediately preceding or following character is an
  ASCII letter or digit. Start/end of input and punctuation are valid boundaries.
  This preserves the legacy ASCII boundary convention; do not add Unicode-word
  boundary behavior implicitly.
- Do not extract a valid-length prefix from a longer contiguous alphanumeric
  identifier. Inspect the source boundary, not only the regex capture.
- Any normalization used internally must not change returned text or offsets.

These separator and ASCII-digit rules deliberately narrow Python's broad `\s`
and Unicode `\d` acceptance. Document these as explicit migration differences:
newline-spanning and other Unicode-whitespace/digit matches are not promised.
Do not describe this feature as exact regex parity with Python 4.8.1.

## R4. Identifier validation policy

- Detect every candidate satisfying R3, including checksum-invalid candidates.
- Do not perform bank-directory lookup, account existence checks, network calls,
  or model downloads.
- Do not silently require MOD-97 validity; this would drop PII-like values that
  Python currently detects, including transcription errors.
- Explain in documentation that detection identifies sensitive-looking text and
  does not establish that an account is valid or exists.
- A strict validation mode or separate validation API is outside this PR.
- Apply the same format-detection policy to the other six entities: no VAT/tax
  checksum requirements, pension date validation, postal directory lookup, or
  document issuance validation. Context and lexical rules below are mandatory.

## R5. Offset and structured-data requirements

- UTF-8 byte ranges and Unicode code-point ranges must both address the exact
  original substring, with zero-based, end-exclusive offsets.
- Node and WASM UTF-16 ranges must work with JavaScript string slicing.
- Test emoji, combining marks, and CJK text before every entity type; ASCII-only fixtures
  are insufficient to verify these units.
- In structured scans, preserve the existing JSON Pointer path and string-local
  offset contract. Test two fields and an array element.
- Never concatenate separate fields to create a candidate. Required context must
  occur in the same string value, not in a sibling field or JSON property name.

## R6. Transformation integration

- `scan_and_transform` must honor the scan locale and produce `[DE_IBAN]` for
  the existing Core redaction strategy. Do not introduce numbered placeholders.
- `transform` must accept explicit `DE_IBAN` findings without rescanning or
  requiring a locale; the locale controls detection only.
- Ensure the new label works with entity selection, per-entity overrides, exact
  and full-match regex allowlists, and existing strategy/provider validation.
- Verify redaction, masking, and removal end to end; exercise provider-backed
  strategies with existing test providers on supported runtimes. Do not broaden
  WASM support for provider-backed strategies.
- Preserve source/output ranges and the rule that transformation records omit
  original matched PII.
- Do not globally suppress generic PHONE/SSN/etc. scan findings inside IBANs.
  With default transformation selection, existing overlap handling must prefer
  the containing IBAN span and produce one replacement for it. Add a regression
  fixture if an overlapping base detector is present.
- For IBAN-only transformation tests, set `entities: ["DE_IBAN"]` so the expected
  output does not depend on unrelated detector findings. Exact allowlisting uses
  the source value, not an automatically normalized IBAN.
- Apply all preceding transformation requirements to every new label, using
  `[DE_VAT_ID]`, `[DE_TAX_ID]`, etc. as their redaction placeholders.
- Context text must survive replacements for tax, social-insurance, passport,
  and residence-permit findings. Postal-code matches intentionally include their
  prefix, so their replacement removes that prefix as well.
- Add overlap cases for VAT versus generic SSN, tax ID versus generic PHONE, and
  German-prefixed postal code versus generic ZIP_CODE. Scanning may return both;
  transformation must use the existing selection/overlap rules. For equal-span
  built-in findings with absent confidence, the current lexical tie-break should
  prefer `DE_TAX_ID` over `PHONE`. Test this; do not introduce a blanket new
  priority rule that changes unrelated or caller-supplied findings.

## R7. Required IBAN acceptance examples

The expected count below refers to `DE_IBAN` only. Existing detectors may still
return other entity types, especially with no German locale or malformed input.

| Input / configuration                                   | Expected DE_IBAN behavior                   |
| ------------------------------------------------------- | ------------------------------------------- |
| `DE44500105175407324931`, locale `de`                   | One exact match                             |
| `DE44 5001 0517 5407 3249 31`, locale `de`              | One match including internal spaces         |
| `de44 5001 0517 5407 3249 31`, locale `DE-de`           | One match preserving lowercase text         |
| `DE44 50010517 54073249 31`, locale `de_DE`             | One partially grouped match                 |
| Grouped value using each supported SEP                  | One match for each variant                  |
| `(DE44500105175407324931).`, locale `de`                | Match excludes punctuation                  |
| Same IBAN twice, locale `de`                            | Two findings at different source ranges     |
| Valid-shaped IBAN preceded by emoji/CJK/combining text  | Correct byte, code-point, and UTF-16 ranges |
| `DE45500105175407324931`, locale `de`                   | One match despite altered checksum digits   |
| A valid input without locale or with `en-US`            | No DE_IBAN finding                          |
| `DE4450010517540732493`, locale `de`                    | No DE_IBAN: too short                       |
| `DE445001051754073249310`, locale `de`                  | No DE_IBAN: too long, no prefix match       |
| `XDE44500105175407324931` or valid IBAN followed by `X` | No DE_IBAN: embedded identifier             |
| `DE44-5001-0517-5407-3249-31`                           | No DE_IBAN                                  |
| `DE44  5001 0517 5407 3249 31`                          | No DE_IBAN: double separator                |
| `DE44\n5001 0517 5407 3249 31`                          | No DE_IBAN: newline is not SEP              |
| `DE 44 5001 0517 5407 3249 31`                          | No DE_IBAN: misplaced separator             |
| Same shape using Arabic-Indic/fullwidth digits          | No DE_IBAN                                  |
| Non-German prefix with the same trailing digit count    | No DE_IBAN                                  |

Also test empty input, repeated near-matches, long digit runs, multiple adjacent
IBANs separated by punctuation, malformed config, and structured transformation.

## R8. Conformance, performance, and delivery

- Put positive/negative expectations in shared fixtures consumed by Rust and all
  applicable bindings. Existing plain fixture runners call scan without config;
  extend them to accept optional fixture scan config with unchanged defaults,
  or introduce a focused locale fixture suite used by every binding.
- Run existing fixture suites unchanged. Do not rewrite old expected detections
  to accommodate unrelated changes.
- Keep matching bounded and linear in input size; compile patterns once and
  avoid per-candidate whole-input copying. No new dependency without a concrete
  need that existing Rust facilities cannot reasonably meet.
- Compare no-locale scanning and German scanning on short, mixed, long, and
  adversarial synthetic texts. Investigate a reproducible greater-than-10%
  regression in existing no-locale workloads before merging.
- Run `cargo fmt --all --check`,
  `cargo clippy --workspace --all-targets --all-features -- -D warnings`, and
  `cargo test --workspace --all-features`.
- Run installed Python/Node binding tests and browser/WASM package tests, not
  merely Rust unit tests. Verify config forwarding and offset conversions.
- Update README, entity/configuration references, binding type declarations if
  needed, and migration documentation. State the checksum and separator policy.
- Deliver a focused PR with test results, performance observations, and known
  migration differences. Do not publish packages without release authorization.
- Python 4.9 integration requires a subsequently published compatible Core wheel;
  a source-only Core change is not sufficient to update the Python extra pin.

## R9. Shared lexical and context rules for the other six entities

Use these definitions in R10-R15:

```text
D := one ASCII digit [0-9]
L := one ASCII letter [A-Za-z]
H := one of the four horizontal separators defined as SEP in R3
GAP := H* [:#-]? H*
```

- All literal prefixes and context labels match ASCII case-insensitively, with
  original casing preserved in findings. Do not use Unicode case folding that
  expands the accepted alphabet.
- Apply R3's immediate ASCII-alphanumeric boundary checks to every value span.
  Consequently a label ending in a letter needs whitespace or punctuation before
  a value; `IdNr.12345678901` is allowed, `IdNr12345678901` is not.
- For context-required types, accept only `CONTEXT GAP VALUE`, with no intervening
  prose or newline. A context label must not begin inside an ASCII word/number.
  Include neither context nor GAP in the returned finding.
- A bare identifier or an unrelated preceding label must not activate a
  context-required detector. German locale alone does not supply missing context.
- Do not search an entire document or previous line for context, nor use one
  context marker to activate an arbitrary list of later identifiers.
- A structured key such as `tax_id` is not textual context for these detectors;
  schema-driven detection is a separate feature.
- H may repeat in GAP and where explicitly written H+, but value-group separators
  written H? allow at most one character. No newline, vertical whitespace,
  Unicode digit, extra letter/digit, or punctuation substitution is accepted.
- These restrictions deliberately narrow legacy Python's Unicode `\d`, broad
  `\s`, and context-substring matching. Record the differences in migration docs
  and fixtures rather than changing the frozen 4.8.1 expectations.

## R10. German VAT identifier: DE_VAT_ID

```text
VALUE := DE (H | -)? D{9}
CONTEXT := not required
```

- Return the complete DE prefix, optional separator, and nine digits.
- Do not group the nine digits internally or accept multiple prefix separators.
- Examples with German locale:

| Input                                              | Expected matched text, or no DE_VAT_ID |
| -------------------------------------------------- | -------------------------------------- |
| `USt-IdNr DE123456789 ist gesetzt.`                | `DE123456789`                          |
| `USt-IdNr DE 123456789 ist gesetzt.`               | `DE 123456789`                         |
| `de-123456789`                                     | `de-123456789`                         |
| `(DE123456789)`                                    | `DE123456789`                          |
| `DE12345678` / `DE1234567890` / `DE123456789A`     | None                                   |
| `XDE123456789` / `DE--123456789` / `DE  123456789` | None                                   |
| `DE123 456 789` / `AT123456789`                    | None                                   |

## R11. German tax identifier: DE_TAX_ID

```text
VALUE := D{11} | D{2} H? D{3} H? D{3} H? D{3}
CONTEXT := Steuer(H|-)?ID | Steueridentifikationsnummer |
           Identifikationsnummer | IdNr[.]? | Tax(H|-)?ID
```

- Return only the value, preserving optional internal separators.
- This is the legacy eleven-digit personal tax-ID detector; do not add tax-office
  Steuernummer, slash-separated identifiers, or business identifiers to this label.

| Input                                                    | Expected matched text, or no DE_TAX_ID |
| -------------------------------------------------------- | -------------------------------------- |
| `Steuer-ID 12345678901 liegt vor.`                       | `12345678901`                          |
| `Steueridentifikationsnummer: 12 345 678 901`            | `12 345 678 901`                       |
| `IdNr.12345678901`                                       | `12345678901`                          |
| `tax id # 12345678901`                                   | `12345678901`                          |
| `Invoice 12345678901` / bare `12345678901`               | None                                   |
| `Steuer-ID 1234567890` / `Steuer-ID 123456789012`        | None                                   |
| `Steuer-ID A12345678901` / `Steuer-ID 12345678901Z`      | None                                   |
| `Steuer-ID 123 456 789 01` / `Steuer-ID 12  345 678 901` | None                                   |
| `NotSteuer-ID 12345678901` / `Steuer-ID\n12345678901`    | None                                   |

## R12. German social-insurance identifier: DE_SOCIAL_SECURITY_NUMBER

```text
VALUE := D{2} H? D{6} H? L H? D{3}
CONTEXT := Rentenversicherungsnummer | Sozialversicherungsnummer | RVNR | SVNR
```

- Return only the value, preserving grouping and letter case.
- This is the legacy pension/social-insurance pattern. Do not use it to identify
  health-insurance numbers, generic US SSNs, or arbitrary alphanumeric IDs.

| Input                                               | Expected matched text, or no DE_SOCIAL_SECURITY_NUMBER |
| --------------------------------------------------- | ------------------------------------------------------ |
| `Rentenversicherungsnummer 65150804A123 liegt vor.` | `65150804A123`                                         |
| `SVNR: 65 150804 A123`                              | `65 150804 A123`                                       |
| `rvnr # 65 150804 a 123`                            | `65 150804 a 123`                                      |
| `Build 65150804A123 failed.` / bare `65150804A123`  | None                                                   |
| `RVNR 65150804A12` / `RVNR 65150804A1234`           | None                                                   |
| `RVNR 651508041123` / `RVNR 65150804AA123`          | None                                                   |
| `RVNR 65-150804-A123` / `RVNR\n65150804A123`        | None                                                   |

## R13. German-prefixed postal code: DE_POSTAL_CODE

```text
VALUE := (PLZ (H | : | -)? | DE (H | -) | D (H | -)) D{5}
CONTEXT := not required beyond the prefix included in VALUE
```

- Return the prefix, optional/required separator, and five digits together.
  This deliberately preserves Python's span semantics, even though other types
  exclude context. Do not silently shorten the match to the digits.
- A bare five-digit value does not become DE_POSTAL_CODE merely because locale
  is German. Existing generic ZIP_CODE detection may still apply.
- Do not add city inference, a postal database, or validity checks.

| Input                                     | Expected matched text, or no DE_POSTAL_CODE |
| ----------------------------------------- | ------------------------------------------- |
| `PLZ10115 Berlin.` / `PLZ:10115 Berlin.`  | `PLZ10115` / `PLZ:10115`                    |
| `PLZ 10115` / `PLZ-10115`                 | Complete corresponding value                |
| `DE-10115 Berlin.` / `D 10115 Berlin.`    | `DE-10115` / `D 10115`                      |
| `de 10115`                                | `de 10115`                                  |
| `10115 Berlin` / `DE10115` / `D10115`     | None                                        |
| `PLZ1011` / `PLZ101150` / `PLZ10115A`     | None                                        |
| `SKU D12345` / `Release DE12345`          | None                                        |
| `PLZ: 10115` / `DE--10115` / `PLZ  10115` | None                                        |

`PLZ: 10115` is a useful possible future enhancement, but the legacy pattern
allows only one prefix separator. Keep its rejection explicit in this scope;
expanding it requires a separately documented detection change.

## R14. Passport-context identifier: DE_PASSPORT_NUMBER

```text
VALUE := L D{8}
CONTEXT := Passnummer | Reisepass(nummer)? | Passport(H+ No[.]? | H+ Number)?
```

The accepted labels include `Reisepass`, `Reisepassnummer`,
`Passport`, `Passport No.`, and `Passport Number`.

- Return only the value. This is the inherited one-letter/eight-digit heuristic;
  it does not claim to cover all actual German passport-number formats.
- Do not add Personalausweis detection or broader alphanumeric document formats
  under this label without separately sourced requirements and fixtures.

| Input                                              | Expected matched text, or no DE_PASSPORT_NUMBER |
| -------------------------------------------------- | ----------------------------------------------- |
| `Passnummer C12345678 wurde geprueft.`             | `C12345678`                                     |
| `Reisepassnummer: c12345678`                       | `c12345678`                                     |
| `Passport No. # A12345678`                         | `A12345678`                                     |
| `Ticket A12345678 was shipped.` / bare `C12345678` | None                                            |
| `Passnummer C1234567` / `Passnummer C123456789`    | None                                            |
| `Passnummer CC1234567` / `Passnummer 123456789`    | None                                            |
| `Passnummer C12A45678` / `Passnummer\nC12345678`   | None                                            |

## R15. Residence-permit-context identifier: DE_RESIDENCE_PERMIT_NUMBER

```text
VALUE := AT D{7}
CONTEXT := Aufenthaltstitel | Aufenthaltserlaubnis | Residence H+ Permit | eAT
```

- Return only the AT-prefixed value; no separator after AT is allowed.
- This is the inherited AT-plus-seven-digits heuristic, not a statement of
  exhaustive or authoritative residence-permit numbering rules.

| Input                                             | Expected matched text, or no DE_RESIDENCE_PERMIT_NUMBER |
| ------------------------------------------------- | ------------------------------------------------------- |
| `Aufenthaltstitel AT1234567 gueltig.`             | `AT1234567`                                             |
| `Aufenthaltserlaubnis: at1234567`                 | `at1234567`                                             |
| `Residence Permit # AT1234567` / `eAT-AT1234567`  | `AT1234567`                                             |
| `Order AT1234567 is internal.` / bare `AT1234567` | None                                                    |
| `eAT AT123456` / `eAT AT12345678`                 | None                                                    |
| `eAT AT 1234567` / `eAT DE1234567`                | None                                                    |
| `eAT AT1234567X` / `eAT\nAT1234567`               | None                                                    |

## R16. Completion matrix and Python migration boundary

For each of the seven labels, require shared fixtures proving:

1. German locale aliases activate it; omitted/non-German locale does not.
2. All listed accepted forms and context aliases work; wrong lengths, unrelated
   context, embedded ASCII identifiers and forbidden separators do not.
3. Matched text and byte/code-point/UTF-16 ranges preserve original input.
4. Repeated occurrences and structured values retain separate locations.
5. Selection, allowlists, overrides and supported transformations work, with
   context retained or removed exactly as specified for the entity.
6. At least one synthetic input contains all seven types, with expected ordered
   German findings and an end-to-end transformation result across bindings.
7. The seven-type suite passes against installed packages, with no network or
   models required at inference time and no regression to existing fixtures.

Every rejection assertion concerns the target German label, not necessarily an
empty overall scan. Generic detectors may legitimately identify the same input.

Use the published Python 4.8.1 contract and `tests/test_de_pii_regex.py` as
comparison evidence. Keep their source fixtures unchanged. Record intentional
whitespace, digit-alphabet and context-boundary differences in a separate matrix.

Python enables German detectors through explicit entity selection even without
a locale. Core currently selects entities only for transformations. Keep that
Core API distinction: the Python adapter may route explicit German entity
requests to locale `de` then filter, but must separately test legacy overlap and
selection semantics. Do not add a new scan selector casually within this work.

Implementation may be split into focused PRs: locale routing plus IBAN/VAT;
contextual tax/social-insurance detectors; postal/document heuristics; then
cross-binding conformance and documentation. All seven must meet this brief
before claiming coverage of the legacy German entity set or unblocking general
German locale requests in the 4.9 adapter. Partial delivery must stay explicit.

Out of scope: identifiers beyond these seven, exhaustive official format
validation, checksum-gated detection, language inference, schema-key inference,
and changes to existing generic detectors or Core's global overlap policy.
