# Validation protocol: style index to IQ

**Status: not started.** No part of this study has been run. Until every acceptance
threshold below is met for a language, `iq_validated` for that language stays `false`
in `mcp-server/config/validation.json`, IQ, percentile and mental age are withheld,
and every output is labelled experimental and unvalidated.

The IQ bands, component weights and scaling bounds were set by hand, with no source,
sample or citation, so the current mapping is circular: the table is the only thing
that defines IQ, and it cannot be wrong by construction. This protocol specifies the
data collection that would replace it. Results that require real data collection are
specified here, not fabricated.

## Claims under test

1. The style index predicts a standardised IQ score for an individual well enough to
   report an IQ point estimate with an empirically derived prediction interval.
2. The prediction is equally accurate and unbiased across the subgroups listed under
   *Subgroup analyses*.
3. The index is stable across writing prompts and sessions (reliability).

The text complexity band is **not** under test as a measure of education. Education is
recorded only to check representativeness and differential prediction.

## Criterion measures

| Language of writing | Primary criterion | Secondary criterion |
|---|---|---|
| English | WAIS-IV Full Scale IQ, administered and scored by a licensed psychologist | WAIS-IV Verbal Comprehension Index |
| Indonesian | WAIS-IV Full Scale IQ, Indonesian adaptation licensed from the publisher; if no licensed adaptation is available, the study does not start for Indonesian | WAIS-IV Verbal Comprehension Index (same adaptation) |

The criterion test is administered within 14 days of the writing task, by an examiner
blind to the style index. The criterion test is administered once per participant:
test-retest reliability applies to the writing task only, never to the criterion. Raven's Progressive Matrices may be added as an exploratory
non-verbal criterion but cannot substitute for the primary criterion.

## Writing task

- Three standardised prompts per participant (expository, argumentative, narrative),
  identical within a language, translated and back-translated between languages.
- Supervised, unaided: typed on a locked machine with spell-check, autocomplete,
  translation and AI tools disabled; 30 minutes per prompt; target length 350 words
  (minimum 250 alphabetic words, the `min_words` gate).
- Recorded provenance: `supervised_unaided`; text type: `formal_prose`.
- Texts are scored by the exact tool version under test; the git commit and
  `config/validation.json` version are stored with every score.

## Sample size

Per language, recruited by the stratified design in `docs/validation/norming-plan.md`:

| Set | N per language | Purpose |
|---|---|---|
| Calibration | 350 | Fit any re-weighting, band boundaries and the prediction interval |
| Held-out evaluation | 360 | All acceptance statistics; never used for fitting |
| Test-retest subsample | 100 (drawn from calibration) | Second session after 2 to 4 weeks with a different prompt |

The calibration, held-out and test-retest participants are a subset of the norm
sample defined in `docs/validation/norming-plan.md`, recruited under the same
stratified design; no one is recruited twice.

Sizing arithmetic. The held-out set must give every primary subgroup at least 60
participants. The primary subgroups are the six age bands, the language-background
strata (five for Indonesian, three for English), sex (two groups) and region
(Java and outside Java, each split urban and rural: four groups). Each partition
must cover the whole held-out set, and the largest partition is the six age bands:
6 × 60 = 360. The held-out size is therefore 360 per language; the other partitions
(5 × 60 = 300, 2 × 60 = 120, 4 × 60 = 240) fit inside it when quotas are crossed.
With N = 360 held out, a correlation of r = 0.40 has a 95% confidence interval
half-width of about 0.09 (Fisher z). Recruitment stops for a stratum once its quota
is filled.

Primary subgroups carry no exemption. A language stays `iq_validated = false` while
any primary subgroup has fewer than 60 held-out participants; under-filled strata
are reported, never imputed, and a small group does not escape the subgroup
thresholds by being small. Highest completed education and self-disclosed
disability are secondary subgroups: they are analysed and reported descriptively,
and any of them with fewer than 60 held-out participants is reported without a
pass or fail verdict.

Validation does not cover the secondary subgroups (education level and disability,
including dyslexia). Results for writers in those groups remain unvalidated even
after a language passes, and the tool
must not be used to screen people in those groups until each has its own quota-sized validation (at least 60 held-out
participants) that meets the same thresholds.

## Analyses

All statistics are computed on the held-out set, per language, with 95% confidence
intervals (bootstrap, 2,000 resamples):

- Pearson r and Spearman rho between style index and the primary criterion.
- Standard error of estimate, SEE = SD_criterion × sqrt(1 − r²), and the resulting
  95% prediction interval (±1.96 × SEE). This replaces the uncalibrated heuristic range.
- Calibration slope and intercept of criterion on predicted IQ.
- Test-retest reliability: ICC(2,1) between sessions; alternate-prompt reliability
  across the three prompts.
- Classification accuracy at every cut-off a user might apply (IQ < 85, > 115, > 130):
  sensitivity, specificity, PPV and NPV at base rates of 5%, 16% and 50%.
- Length dependence: partial correlation of the index with the criterion controlling
  for mean sentence length and mean word length (see
  `docs/validation/effective-weights.md`).

## Subgroup analyses

Differential prediction (Cleary model: criterion regressed on index, group and
index × group) and per-group r, SEE and mean residual for:

- language of writing (English vs Indonesian; never pooled);
- sex;
- age band (as defined in the norming plan);
- highest completed education (secondary);
- first language / language background (Indonesian L1, regional-language L1 such as
  Javanese or Sundanese, English L1 for English texts);
- region (Java vs outside Java; urban vs rural);
- self-disclosed dyslexia or other writing-related disability (secondary).

Adverse impact ratio (selection rate of each group divided by the highest group's
rate) is reported at every cut-off listed under *Analyses*.

## Acceptance thresholds

All must hold on the held-out set for a language before `iq_validated` may be set to
`true` for it:

| Statistic | Threshold |
|---|---|
| r with primary criterion | r ≥ 0.50 and lower 95% CI bound ≥ 0.40 |
| Standard error of estimate | SEE ≤ 12 IQ points |
| Calibration slope | between 0.90 and 1.10 |
| Test-retest reliability | ICC(2,1) ≥ 0.80 |
| Subgroup accuracy | r ≥ 0.40 in every primary subgroup, each with at least 60 held-out participants; otherwise the language is not validated |
| Differential prediction | no index × group interaction significant at α = 0.01 (Holm-corrected) and no subgroup with absolute mean residual > 3 IQ points |
| Adverse impact | ratio ≥ 0.80 at every reported cut-off |

If any threshold fails, the result is published as a failed validation and the flag
stays `false`. Thresholds are not relaxed after unblinding.

## Governance

- Pre-registration of hypotheses, thresholds and analysis code before data collection.
- Ethics approval and written informed consent that states the purpose, retention and
  the participant's rights under Indonesia's Personal Data Protection Law (UU PDP,
  Law No. 27 of 2022).
- An independent psychometrician signs off the analysis report.
- Results are stored as `docs/validation/results/<lang>-<yyyy-mm-dd>.md`; the commit
  that sets `iq_validated: true` links to that report.
- Any change to scoring code or configuration after validation (visible as a
  golden-score diff) invalidates the result for the affected language until the
  held-out analysis is re-run. Validation expires after three years.
- The shipped code enforces a minimum ±25-point range. Replacing it with ±1.96 × SEE
  is a separate, reviewed code change made only after this protocol passes.

## Until validation passes

The tool reports a writing-style index of lexical-syntactic complexity and a neutral
style band. It is not an intelligence measure, and its outputs must not be used for
decisions about individuals.

Passing validation for a language does not extend to writers in the secondary
subgroups (education level, disability including dyslexia): the tool
must not be used to screen them until each group has its own quota-sized validation meeting the
same thresholds.
