# Docstring Style Policy

This repository intentionally uses language-specific documentation styles based
on code role.

## src/ — NumPy Style

Production and analytical code uses NumPy-style docstrings to support:

- explicit parameter semantics
- complex return structures
- scientific documentation standards
- future auto-generated API documentation

## R scripts - roxygen Style

R analysis code and command-line wrappers use roxygen-style comments so function
contracts are explicit and can be promoted into package documentation if the R
analysis layer is later packaged.

## tests/ — Google Style

Test code uses concise Google-style docstrings because:

- tests document behavioral intent, not APIs
- readability during review is prioritized
- excessive structure adds noise without clarity

This is a deliberate, documented choice and not stylistic inconsistency.
