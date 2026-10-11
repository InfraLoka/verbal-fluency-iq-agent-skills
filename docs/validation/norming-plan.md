# Norming plan: reference population and norm groups

**Status: not started.** No norm sample exists. Until it does, the tool reports no
normed or age-adjusted score, never assumes an age, and every output carries
`language_norm_unvalidated: true`.

Verbal style changes with age, schooling era, dialect and disability, none of which
enter the current mapping, and the former default age of 30 was not a validated
population median. This plan defines who the scores would be compared against and how.

## Reference population

Separate reference populations per language of writing; scores are never pooled or
compared across languages.

| Language of writing | Reference population |
|---|---|
| Indonesian | Adults aged 17 to 64 resident in Indonesia who write in Indonesian for study or work |
| English | Adults aged 17 to 64 resident in Indonesia who write in English for study or work, plus a separate English-L1 comparison group |

The intended use case (screening in Indonesia) defines the population. A score is
interpretable only for a writer who belongs to the reference population of the
language they wrote in.

## Age bands

| Band | Ages |
|---|---|
| A1 | 17 to 19 |
| A2 | 20 to 24 |
| A3 | 25 to 34 |
| A4 | 35 to 44 |
| A5 | 45 to 54 |
| A6 | 55 to 64 |

Writers under 17 or over 64 are out of scope. Age is a required input for any normed
output; it is never defaulted.

## Language-background strata

| Language of writing | Strata |
|---|---|
| Indonesian | (L1) Indonesian as first home language; (R1) Javanese first; (R2) Sundanese first; (R3) other regional language first; (M) bilingual from birth |
| English | (E1) English as first language; (E2) English as second or later language with Indonesian L1; (E3) English as second or later language with a regional-language L1 |

Language background is a required input for any normed output, recorded as one of the
codes above.

## Additional stratification variables

Recorded for representativeness and subgroup analyses only; never reported as outputs
and never used to adjust an individual's score:

- sex;
- highest completed education (SD/SMP, SMA/SMK, D1 to D3, S1, S2/S3);
- region (Java vs outside Java; urban vs rural);
- self-disclosed dyslexia or other writing-related disability.

## Sample size

- Minimum 50 participants per age band × language-background cell.
- Indonesian: 6 age bands × 5 strata = 30 cells, minimum 1,500 participants.
- English: 6 age bands × 3 strata = 18 cells, minimum 900 participants.
- Quotas within cells follow Statistics Indonesia (BPS) 2020 census margins for sex,
  region and education; post-stratification weights correct residual imbalance.
- The validation study sample (`docs/validation/validation-protocol.md`) may be drawn
  from the norm sample but is analysed separately.

## Data collection

Identical to the writing task in the validation protocol: three standardised prompts,
supervised and unaided, `provenance = supervised_unaided`, `text_type = formal_prose`,
minimum 250 alphabetic words per text, with informed consent under UU PDP.

## Norm computation

- Continuous (regression-based) norming of the style index on age within each
  language-background stratum (for example GAMLSS with age as a smooth term), so
  that adjacent age bands do not create artificial jumps; raw cell percentiles are
  reported alongside as a check.
- Output on the normed scale: within-group percentile and z-score, labelled with the
  language, age band and language-background stratum they refer to.
- Only within-group scores are reported. No score is compared across languages or
  strata.

## Acceptance criteria for the norms

- Every cell reaches its minimum of 50.
- Bootstrap 90% confidence interval of each cell's median style index is within ±3
  index points.
- Norms are rebuilt after any scoring change (golden-score diff) and at least every
  five years.

## How the code will use the norms

- Norms will live in versioned per-language files under `mcp-server/config/norms/`.
- A normed output requires both `chronological_age` and `language_background`; if
  either is missing, the normed fields are withheld with a reason, never imputed.
- Until the norms exist, `config/validation.json` keeps every language unvalidated and
  no normed field is produced.
