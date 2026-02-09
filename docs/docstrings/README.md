# Docstring Style Policy

This repository intentionally uses two docstring styles based on code role.

## src/ — NumPy Style

Production and analytical code uses NumPy-style docstrings to support:

- explicit parameter semantics
- complex return structures
- scientific documentation standards
- future auto-generated API documentation

## tests/ — Google Style

Test code uses concise Google-style docstrings because:

- tests document behavioral intent, not APIs
- readability during review is prioritized
- excessive structure adds noise without clarity

This is a deliberate, documented choice and not stylistic inconsistency.
