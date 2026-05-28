#' Deterministic Study 1 descriptive analysis helpers
#'
#' These functions consume fixed `methodology_pair_scores` records produced by
#' the Python scoring layer. They do not estimate causal effects, run hypothesis
#' tests, or modify scoring rules.
#'
#' @name study1_analysis
NULL

#' Return preregistered indicator names
#'
#' @return Character vector containing `V1` through `V10`.
#' @export
indicator_names <- function() {
  paste0("V", 1:10)
}

#' Return required pair-score columns
#'
#' @return Character vector of columns required by the analysis layer.
#' @export
required_pair_score_columns <- function() {
  c(
    "manuscript_id",
    "preprint_raw_statistical_rigour",
    "published_raw_statistical_rigour",
    "PRES",
    paste0(indicator_names(), "_delta")
  )
}

#' Validate fixed methodology pair-score records
#'
#' @param pair_scores A data frame containing `methodology_pair_scores` records.
#'
#' @return Invisibly returns `pair_scores` when validation succeeds.
#' @throws Error when `pair_scores` is not a data frame or required columns are
#'   missing.
#' @export
validate_pair_scores <- function(pair_scores) {
  if (!is.data.frame(pair_scores)) {
    stop("pair_scores must be a data.frame", call. = FALSE)
  }

  missing <- setdiff(required_pair_score_columns(), names(pair_scores))
  if (length(missing) > 0) {
    stop(
      paste("missing required columns:", paste(missing, collapse = ", ")),
      call. = FALSE
    )
  }

  invisible(pair_scores)
}

#' Read fixed methodology pair-score records from CSV
#'
#' @param path Path to a CSV file containing `methodology_pair_scores` records.
#'
#' @return Validated pair-score data frame.
#' @export
read_pair_scores <- function(path) {
  pair_scores <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  validate_pair_scores(pair_scores)
  pair_scores
}

#' Summarize Peer-Review Effect Scores
#'
#' @param pair_scores A validated or validatable pair-score data frame.
#'
#' @return A one-row data frame with descriptive PRES counts and summaries.
#' @export
summarize_pres <- function(pair_scores) {
  validate_pair_scores(pair_scores)
  pres <- pair_scores$PRES

  data.frame(
    n_pairs = length(pres),
    mean_pres = mean(pres),
    median_pres = median(pres),
    min_pres = min(pres),
    max_pres = max(pres),
    n_declined = sum(pres < 0),
    n_no_change = sum(pres == 0),
    n_improved = sum(pres > 0),
    stringsAsFactors = FALSE
  )
}

#' Summarize indicator-level changes
#'
#' @param pair_scores A validated or validatable pair-score data frame.
#'
#' @return Data frame with one row per indicator and descriptive delta counts.
#' @export
summarize_indicator_deltas <- function(pair_scores) {
  validate_pair_scores(pair_scores)

  rows <- lapply(indicator_names(), function(indicator) {
    column <- paste0(indicator, "_delta")
    delta <- pair_scores[[column]]
    data.frame(
      indicator = indicator,
      n_pairs = length(delta),
      mean_delta = mean(delta),
      median_delta = median(delta),
      min_delta = min(delta),
      max_delta = max(delta),
      n_declined = sum(delta < 0),
      n_no_change = sum(delta == 0),
      n_improved = sum(delta > 0),
      stringsAsFactors = FALSE
    )
  })

  do.call(rbind, rows)
}

#' Summarize raw statistical rigour scores by manuscript version
#'
#' @param pair_scores A validated or validatable pair-score data frame.
#'
#' @return Data frame with one row for preprints and one row for published
#'   articles.
#' @export
summarize_raw_scores <- function(pair_scores) {
  validate_pair_scores(pair_scores)

  versions <- c("preprint", "published")
  columns <- c(
    "preprint_raw_statistical_rigour",
    "published_raw_statistical_rigour"
  )

  rows <- lapply(seq_along(versions), function(idx) {
    scores <- pair_scores[[columns[[idx]]]]
    data.frame(
      version = versions[[idx]],
      n_pairs = length(scores),
      mean_raw_score = mean(scores),
      median_raw_score = median(scores),
      min_raw_score = min(scores),
      max_raw_score = max(scores),
      stringsAsFactors = FALSE
    )
  })

  do.call(rbind, rows)
}

#' Build all Study 1 descriptive summaries
#'
#' @param pair_scores A validated or validatable pair-score data frame.
#'
#' @return Named list with `pres`, `indicator_deltas`, and `raw_scores` data
#'   frames.
#' @export
build_study1_summary <- function(pair_scores) {
  validate_pair_scores(pair_scores)

  list(
    pres = summarize_pres(pair_scores),
    indicator_deltas = summarize_indicator_deltas(pair_scores),
    raw_scores = summarize_raw_scores(pair_scores)
  )
}

#' Write Study 1 summary tables to CSV
#'
#' @param summary Named summary list from [build_study1_summary()].
#' @param output_dir Directory where CSV files should be written.
#'
#' @return Named list of output paths for the written CSV files.
#' @export
write_study1_summary <- function(summary, output_dir) {
  if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE)
  }

  paths <- list(
    pres = file.path(output_dir, "pres_summary.csv"),
    indicator_deltas = file.path(output_dir, "indicator_delta_summary.csv"),
    raw_scores = file.path(output_dir, "raw_score_summary.csv")
  )

  write.csv(summary$pres, paths$pres, row.names = FALSE)
  write.csv(summary$indicator_deltas, paths$indicator_deltas, row.names = FALSE)
  write.csv(summary$raw_scores, paths$raw_scores, row.names = FALSE)

  paths
}

#' Run Study 1 analysis from a pair-score CSV
#'
#' @param pair_scores_path Path to a CSV file containing fixed pair-score
#'   records.
#' @param output_dir Directory where summary CSV files should be written.
#'
#' @return Named list of output paths for the written CSV files.
#' @export
run_study1_analysis <- function(pair_scores_path, output_dir) {
  pair_scores <- read_pair_scores(pair_scores_path)
  summary <- build_study1_summary(pair_scores)
  write_study1_summary(summary, output_dir)
}
