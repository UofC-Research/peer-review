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
