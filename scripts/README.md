# Publication charts and topic classification

Run `python3 scripts/generate_publication_graphs.py --as-of 2026-10-18` from the bibliography directory. The two older script names are compatibility wrappers for this same generator. Without `--as-of`, the date defaults to the execution date. `YYYY-MM` remains supported and means the first day of that month.

The outputs count bibliography entries, not deduplicated research works. Existing repeated keys/titles remain separate entries. Entries with a publication year later than the snapshot year are excluded from both charts and CSVs; the bibliography itself is unchanged. The snapshot date labels the dataset, not a publication-date filter within that year: included symposium contributions may be scheduled later in the year.

## Topic rules

- Only titles, keywords and abstracts provide topic evidence. Venue, publisher and author names never score.
- OpenSky, ADS-B, ADS-C and Mode S are reported as `source_mentions`, not topic scores. These tags indicate mentions, not verified data use.
- Punctuation and hyphens are normalized; matching uses word boundaries, avoiding substring matches such as `rf` inside `surface`.
- Longer phrases reserve their matching spans before shorter phrases. Each phrase scores once, regardless of repeated occurrences.
- Surveillance Infrastructure & Data Quality requires an explicit aviation-surveillance context as well as a matching infrastructure/quality phrase. A source name alone cannot assign that category.
- Application topics with a score of at least 5 take precedence over Machine Learning & Data Methods. Methods remain visible in the audit columns. No topic evidence yields Other. Category order breaks exact ties deterministically.
- Every entry receives one category so totals reconcile. Weights and thresholds are heuristic, not probabilities or validated confidence estimates. The same rules apply to every year.

The taxonomy separates Aircraft Performance & Environmental Impact (including noise) from Machine Learning & Data Methods. Societal & Public-Service Applications includes epidemiology, economic effects, disruptions and emergency aviation. Navigation & Signal Processing includes radar/localisation methods. Data Tools & Visualisation covers reusable data infrastructure and display tools.

## Audit columns and limitations

`publication_field_assignments.csv` includes the selected category, matching phrases, strongest alternative, score margin, all topic scores, method terms and source mentions. A negative margin can occur when the explicit application-over-method policy selects a lower-scoring application. `needs_review` is true for Other, a winning score below 5, or a margin of at most 2. These flags are triage aids, not an exhaustive error detector. Sparse, non-English and interdisciplinary titles are particularly difficult.

Snapshot 18 October 2026: 989 included entries; 407 flagged for review, including 229 Other. The revised surveillance category contains 7 entries in 2025 and 6 in 2026. Its definition differs from the previous broad category, so compare years only within the newly regenerated series. This is not a manually verified topical census or evidence of a change in research activity. Programme additions and bibliography coverage also affect the trends.

Charts have a zero baseline, distinct line/marker styles, and accompanying CSV data. Both chart labels and the category-chart footer state that these are bibliography entries with inferred topics. No bibliographic entry was removed or edited by this classification update.

Regression checks: `python3 -m unittest discover -s tests`. Tests cover venue independence, source-only abstention, application-versus-method classification, non-aviation surveillance, phrase overlap/repetition, substring false positives and date labels.
