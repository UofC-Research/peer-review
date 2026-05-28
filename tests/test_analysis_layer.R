library(testthat)

source("src/analysis/study1_analysis.R")

pair_scores <- data.frame(
  manuscript_id = c("m1", "m2", "m3"),
  preprint_raw_statistical_rigour = c(3, 10, 5),
  published_raw_statistical_rigour = c(5, 9, 5),
  PRES = c(2, -1, 0),
  V1_delta = c(1, 0, -1),
  V2_delta = c(0, -1, 0),
  V3_delta = c(1, 0, 1),
  V4_delta = c(0, 0, 0),
  V5_delta = c(0, 1, 0),
  V6_delta = c(0, 0, 0),
  V7_delta = c(0, 0, 0),
  V8_delta = c(0, 0, 0),
  V9_delta = c(0, -1, 0),
  V10_delta = c(0, 0, 0),
  stringsAsFactors = FALSE
)

test_that("PRES summary is descriptive and non-inferential", {
  summary <- summarize_pres(pair_scores)

  expect_equal(summary$n_pairs, 3)
  expect_equal(summary$mean_pres, mean(c(2, -1, 0)))
  expect_equal(summary$median_pres, 0)
  expect_equal(summary$min_pres, -1)
  expect_equal(summary$max_pres, 2)
  expect_equal(summary$n_declined, 1)
  expect_equal(summary$n_no_change, 1)
  expect_equal(summary$n_improved, 1)
})

test_that("indicator delta summary counts direction per V1-V10", {
  summary <- summarize_indicator_deltas(pair_scores)

  expect_equal(summary$indicator, paste0("V", 1:10))
  v1 <- summary[summary$indicator == "V1",]
  v2 <- summary[summary$indicator == "V2",]

  expect_equal(v1$n_improved, 1)
  expect_equal(v1$n_no_change, 1)
  expect_equal(v1$n_declined, 1)
  expect_equal(v1$mean_delta, 0)

  expect_equal(v2$n_improved, 0)
  expect_equal(v2$n_no_change, 2)
  expect_equal(v2$n_declined, 1)
})

test_that("raw score summary compares preprint and published versions", {
  summary <- summarize_raw_scores(pair_scores)

  expect_equal(summary$version, c("preprint", "published"))
  expect_equal(summary$n_pairs, c(3, 3))
  expect_equal(summary$mean_raw_score[1], mean(c(3, 10, 5)))
  expect_equal(summary$mean_raw_score[2], mean(c(5, 9, 5)))
})

test_that("study summary validates required pair-score columns", {
  expect_error(
    build_study1_summary(pair_scores[, !(names(pair_scores) %in% "V10_delta")]),
    "missing required columns"
  )

  summary <- build_study1_summary(pair_scores)
  expect_equal(names(summary), c("pres", "indicator_deltas", "raw_scores"))
  expect_equal(summary$pres$n_pairs, 3)
})

test_that("summary CSV exports are written with stable file names", {
  output_dir <- tempfile("study1-summary-")
  summary <- build_study1_summary(pair_scores)

  paths <- write_study1_summary(summary, output_dir)

  expect_true(file.exists(paths$pres))
  expect_true(file.exists(paths$indicator_deltas))
  expect_true(file.exists(paths$raw_scores))
  expect_equal(basename(paths$pres), "pres_summary.csv")
  expect_equal(basename(paths$indicator_deltas), "indicator_delta_summary.csv")
  expect_equal(basename(paths$raw_scores), "raw_score_summary.csv")
})

test_that("run_study1_analysis reads pair scores and writes summaries", {
  input_path <- tempfile("pair-scores-", fileext = ".csv")
  output_dir <- tempfile("study1-run-")
  write.csv(pair_scores, input_path, row.names = FALSE)

  paths <- run_study1_analysis(input_path, output_dir)

  pres_summary <- read.csv(paths$pres, stringsAsFactors = FALSE)
  indicator_summary <- read.csv(paths$indicator_deltas, stringsAsFactors = FALSE)

  expect_equal(pres_summary$n_pairs, 3)
  expect_equal(indicator_summary$indicator, paste0("V", 1:10))
})
