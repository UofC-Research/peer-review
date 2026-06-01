from __future__ import annotations

"""Text feature processors for the parsing subsystem.

This module contains lightweight implementations of processor protocols defined
in :mod:`peer_elt.parse.interfaces`.

Notes
-----
The processors here are intended to be dependency-light. For example,
:class:`SimpleTokenStatsProcessor` provides basic token/sentence counts without
requiring a spaCy runtime.
"""

import re
from typing import Mapping

from peer_elt.parse.interfaces import SpacyProcessor


class SimpleTokenStatsProcessor(SpacyProcessor):
    """Compute simple token and sentence statistics per section.

    This processor is a lightweight fallback that mimics a small subset of
    spaCy-derived features without depending on spaCy itself.

    Notes
    -----
    - Tokens are counted using the regex pattern ``\\b\\w+\\b``.
    - Sentences are approximated by matching spans ending in ``.``, ``!``, or
      ``?``. This is heuristic and may under/over-count for abbreviations or
      unusual punctuation.
    """

    _token_pattern = re.compile(r"\b\w+\b")
    _sentence_pattern = re.compile(r"[^.!?]+[.!?]")

    def process_sections(self, sections: Mapping[str, str]) -> Mapping[str, Mapping[str, int]]:
        """Compute per-section token and sentence counts.

        Parameters
        ----------
        sections : Mapping[str, str]
            Mapping of section name to section text.

        Returns
        -------
        Mapping[str, Mapping[str, int]]
            Mapping of section name to computed features. The inner mapping
            contains:

            - ``token_count``: number of token-like matches
            - ``sentence_count``: number of sentence-like matches
        """
        return {
            section: {
                "token_count": len(self._token_pattern.findall(text)),
                "sentence_count": len(self._sentence_pattern.findall(text)),
            }
            for section, text in sections.items()
        }
