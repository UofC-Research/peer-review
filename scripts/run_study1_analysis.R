#!/usr/bin/env Rscript

source("src/analysis/study1_analysis.R")

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2) {
  stop(
    "Usage: Rscript scripts/run_study1_analysis.R <pair_scores_csv> <output_dir>",
    call. = FALSE
  )
}

paths <- run_study1_analysis(args[[1]], args[[2]])
cat("Wrote Study 1 summaries:\n")
cat(sprintf("- PRES: %s\n", paths$pres))
cat(sprintf("- Indicator deltas: %s\n", paths$indicator_deltas))
cat(sprintf("- Raw scores: %s\n", paths$raw_scores))
