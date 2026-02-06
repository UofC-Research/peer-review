from __future__ import annotations

import re
from typing import Mapping

from peer_elt.parse.interfaces import SpacyProcessor


class SimpleTokenStatsProcessor(SpacyProcessor):
    """Minimal spaCy-like processor for token and sentence counts.

    This is a lightweight fallback that mimics a subset of spaCy-derived
    features without depending on the spaCy runtime.
    """

    _token_pattern = re.compile(r"\b\w+\b")
    _sentence_pattern = re.compile(r"[^.!?]+[.!?]")

    def process_sections(self, sections: Mapping[str, str]) -> Mapping[str, Mapping[str, int]]:
        features: dict[str, dict[str, int]] = {}
        for section, text in sections.items():
            token_count = len(self._token_pattern.findall(text))
            sentence_count = len(self._sentence_pattern.findall(text))
            features[section] = {
                "token_count": token_count,
                "sentence_count": sentence_count,
            }
        return features
