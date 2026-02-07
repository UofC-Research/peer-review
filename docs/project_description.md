# Publish or Perish: Quantifying the Impact of Peer Review on Scientific Work

## Background

Publish or perish is a pervasive norm across scientific disciplines, making peer review an unavoidable stage in the research lifecycle. Yet peer-review practices vary widely across fields and journals: in some cases reviewers request substantial changes to study design, analysis, or interpretation, while in others feedback is limited to clarification, presentation, or formatting.

Although reviewer suggestions may be constructive, they are not always aligned with authors’ original scientific motivations. When extensive or disruptive revisions are requested, authors’ willingness and capacity to implement changes may depend on contextual pressures such as disciplinary norms, journal practices, and time constraints. In some domains—particularly in biomedical research—peer review may involve substantial post-hoc modification of analyses or
framing, raising questions about whether such changes consistently enhance statistical rigor or instead reflect structural or editorial normalization.

Despite the central role of peer review, empirical evidence quantifying **how manuscripts actually change between preprint and peer-reviewed publication** remains limited.

---
## Project Scope and Structure

This project is designed as a **multi-study research program** examining how scientific manuscripts change as they move through the peer-review process.

- **Study 1 (current preregistered study)** focuses exclusively on **measurement and description**: quantifying within-manuscript changes in preregistered indicators of statistical rigor between preprint and published versions within bioRxiv and medRxiv.

- **Study 2 (planned, separately preregistered)** will examine whether the magnitude and nature of changes measured in Study 1 are **associated with broader contextual factors**, such as funding environments, academic systems, author career stage, and disciplinary norms. Study 2 will be preregistered only after Study 1 is completed and locked.

- **Study 3 (future)** expands to additional preprint servers. Because this constitutes a change in document ecosystem, it is reserved for a future, separately preregistered study focused on external validity.

The scope restrictions, analytic commitments, and non-causal framework of Study 1 are fully specified in the preregistered protocol:

- [`Section 1 Study Overview`](peer_review_planning_document.md#1-study-overview)
- [`Section 2 Research Question`](peer_review_planning_document.md#2-research-question)
- [`Section 4 Conceptual Model`](peer_review_planning_document.md#4-conceptual-model-causal-dag-informed-non-causal)
- [`Section 5 Formal DAGs`](peer_review_planning_document.md#5-formal-dags-conceptual)

The **Study 1 preregistration is the controlling document** for all measurement rules, variable definitions, exclusion criteria, and analytic constraints. This project description is **non-normative** and introduces no analytic commitments beyond those explicitly preregistered in the Study 1 protocol.

---
## Study 1: Primary Aim (Current Preregistration)

The primary aim of Study 1 is to **quantify observable changes in research manuscripts associated with peer review**, without assuming that such changes represent improvement, degradation, or convergence in quality.

Specifically, Study 1:

- Compares **matched manuscript pairs** (preprint vs. published)
- Measures change using **preregistered indicators of statistical rigor and reporting transparency**
- Applies **symmetric scoring rules** to preprint and published versions
- Treats all results as **descriptive and associational**, not causal

All definitions, hypotheses, scoring rules, and exclusion criteria governing Study 1 are fixed prior to data access and documented in:

- [`Section 7 Preregistered Variables (V1-V10)`](peer_review_planning_document.md#7-preregistered-variables-v1-v10)
- [`Section 8 Scoring and Composite Measures`](peer_review_planning_document.md#8-scoring-and-composite-measures)
- [`Section 9 Analysis Plan`](peer_review_planning_document.md#9-analysis-plan-high-level)
- [`Section 10 Hypotheses and Interpretation Framework`](peer_review_planning_document.md#10-hypotheses-and-interpretation-framework)

The study is explicitly **null-tolerant**: minimal or null change is treated as a substantively informative outcome.

---

## Measurement Framework

Manuscript-level changes are quantified using preregistered indicators of statistical rigor, including:

- Effect estimate reporting
- Uncertainty reporting
- Significance reporting transparency
- Power or sample-size justification
- Model specification clarity
- Multiplicity handling or disclosure
- Robustness and sensitivity analyses
- Missing data reporting
- Transparency and reproducibility practices
- Study design reporting

Each indicator is scored independently for the preprint and published versions of each manuscript, and within-manuscript change scores are computed using symmetric, preregistered rules.

**All indicator definitions, scoring criteria, composite score construction, and analytic constraints are specified exclusively in the Study 1 preregistration**, including:

- [`Appendix A — Preregistered Codebook`](peer_review_planning_document.md#appendix-a-preregistered-codebook-for-statistical-rigor-indicators-v1-v10)
- [`Appendix B — Machine-Readable Codebook (YAML)`](peer_review_planning_document.md#appendix-b-machine-readable-codebook-yaml)

In addition to preregistered rigor indicators, Study 1 records auxiliary textual and structural manuscript characteristics (e.g., readability metrics, article length, number of tables and figures). These auxiliary metrics are analysed descriptively only and are not treated as indicators of statistical rigor, research quality, or improvement.

---
## Deferred Analyses and Future Extensions

Although manuscript changes may plausibly vary by:

- Funding structure of authors’ institutions
- Academic system or regional research environment
- Career stage of key authors
- Scientific discipline

these factors are **not operationalized, recorded, or analysed in Study 1**.

This restriction is explicitly stated in the preregistered protocol:

- [`Section 12 Deferred Analyses and Planned Extensions`](peer_review_planning_document.md#12-deferred-analyses-and-planned-extensions)

Analyses examining associations between manuscript changes and such contextual factors will be conducted only in **future, separately preregistered studies**. No post-hoc subgroup analyses involving these factors will be performed in Study 1.

---
## Interpretation Framework

Observed patterns of change—whether positive, negative, or near-zero—are interpreted as **empirical descriptions of how manuscripts change during peer review**, not as evidence that peer review causes improvement or decline.

Interpretive constraints are defined in:

- [`Section 10 Hypotheses and Interpretation Framework`](peer_review_planning_document.md#10-hypotheses-and-interpretation-framework)
- [`Section 9.1 Unit of Analysis and Unit of Inference`](peer_review_planning_document.md#91-unit-of-analysis-and-unit-of-inference)

The project explicitly avoids causal attribution, normative quality judgments, and ranking of journals, authors, or institutions.

---
## Broader Impact

By grounding interpretation in preregistered, manuscript-level measurements, this project contributes evidence to ongoing discussions about the role of peer review in scientific communication.

- **For authors**: realistic expectations about the types and magnitudes of changes between preprint and publication
- **For trainees and early-career researchers**: data-driven insight into review cultures
- **For policymakers and research administrators**: systematic, non-causal evidence relevant to debates about rigor,
  incentives, and academic autonomy

All interpretations, implications, and conclusions drawn from this project are constrained by the preregistered, non-causal framework specified in the Study 1 protocol.
