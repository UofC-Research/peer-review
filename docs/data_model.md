# Data Model

## raw_preprints
- `doi`: preprint DOI
- `server`: biorxiv or medrxiv
- `version`: numeric version identifier
- `title`: preprint title
- `abstract`: preprint abstract
- `category`: category field from the preprint server
- `published`: published DOI when available
- `date`: server-provided date for the version

## diff_features
- `doi`: preprint DOI
- `server`: source server
- `category`: category label
- `title_diff_ratio`: similarity between version 1 and latest title
- `abstract_diff_ratio`: similarity between version 1 and latest abstract
- `abstract_word_count_delta`: latest minus version 1 word count
- `pdf_diff_ratio`: similarity between preprint and published PDF text (optional)
- `published_doi_first`: published DOI from the first version (if present)
- `published_doi_latest`: published DOI from the latest version (if present)
- `date_first`: first version date
- `date_latest`: latest version date

## methodology_pair_scores

Table-ready record produced by `peer_elt.transform.methodology.PairScorecard`.
These fields implement the preregistered matched-pair scoring workflow from the
Study 1 planning document.

- `manuscript_id`: stable identifier for the matched preprint-published pair
- `preprint_document_format`: full-text format used for the preprint version
  when known (`pdf`, `html`, `xml`, or mixed/other values supplied upstream)
- `published_document_format`: full-text format used for the published version
  when known
- `preprint_raw_statistical_rigour`: sum of V1-V10 scores for the preprint
  version
- `published_raw_statistical_rigour`: sum of V1-V10 scores for the published
  version
- `PRES`: Peer-Review Effect Score, computed as
  `published_raw_statistical_rigour - preprint_raw_statistical_rigour`
- `preprint_needs_document_completeness_review`: true when one or more
  preprint indicators receives a score of 0
- `published_needs_document_completeness_review`: true when one or more
  published indicators receives a score of 0
- `V1_preprint` ... `V10_preprint`: preregistered indicator scores for the
  preprint version
- `V1_published` ... `V10_published`: preregistered indicator scores for the
  published version
- `V1_delta` ... `V10_delta`: indicator-level changes computed as
  `published - preprint`

## methodology_evidence_rows

Audit rows produced by `PairScorecard.evidence_rows()`. Each row records one
evidence snippet used to support a score.

- `manuscript_id`: stable identifier for the matched pair
- `version`: `preprint` or `published`
- `document_format`: full-text format used for that manuscript version when
  known
- `indicator`: preregistered indicator (`V1` through `V10`)
- `score`: assigned ordinal score (`0`, `1`, or `2`)
- `rationale`: scoring provenance or merge rationale
- `section`: canonical manuscript section where evidence was found
- `text`: extracted evidence snippet
- `pattern`: rule or model source that produced the evidence snippet
