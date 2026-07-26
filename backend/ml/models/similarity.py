"""
Crime similarity (top-k nearest neighbours).

The similarity predictor returns the ``top_k`` cases most
similar to a query case, scored by cosine similarity over a
short TF-IDF representation of ``BriefFacts``. The real
schema also has an ``mo_embedding`` column (pgvector,
``vector(384)``), but the seed populates it as ``NULL``, so
the predictor falls back to TF-IDF when no embedding is
present.

Public surface
==============

* :class:`SimilarityPredictor`
* :meth:`train(cases)` — fits the TF-IDF vocabulary.
* :meth:`predict(query, top_k=10)` — accepts a single
  query case (or anything with a ``BriefFacts``) and returns
  a list of :class:`PredictionResult`, each carrying the
  matched case's id and similarity score.
* :meth:`evaluate(cases)` — coverage (% of cases that
  found at least one match) and hit-rate (% of cases whose
  top match shared the same crime sub-head).

Why not use the pgvector embedding
===================================

The seed data is too small (30 rows) and the embedding
column is NULL. The TF-IDF fallback is a faithful demo
without the weight of a sentence-transformer model.
"""
from __future__ import annotations

from typing import Sequence

from backend.ml.models.base import (
    BaseSklearnPredictor,
    EvidenceItem,
    FeatureContribution,
    PredictionResult,
)
from backend.ml.preprocessing.synthetic_data import SyntheticCase


class SimilarityPredictor(BaseSklearnPredictor):
    """Cosine-similarity nearest-neighbour over TF-IDF."""

    name = "similarity"

    def __init__(self) -> None:
        super().__init__()
        # The list of training rows is kept in memory —
        # they are tiny (1k rows of text), and the predictor
        # needs them at inference time to score a query
        # against every training row.
        self._corpus: list = []
        self._matrix = None  # set in .train()

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, cases: Sequence[SyntheticCase]) -> "SimilarityPredictor":
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        if not cases:
            raise ValueError("SimilarityPredictor.train needs at least 1 case")
        self._corpus = list(cases)
        texts = [c.BriefFacts for c in cases]
        vectorizer = TfidfVectorizer(
            max_features=300,
            ngram_range=(1, 2),
            stop_words="english",
        )
        self._matrix = vectorizer.fit_transform(texts)
        # The vectorizer is needed at inference time to
        # project the query into the same space.
        self._transformers = {
            "vectorizer": vectorizer,
            "similarity_fn": cosine_similarity,
        }
        return self

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(self, query, top_k: int = 10) -> list[PredictionResult]:
        if self._matrix is None:
            raise RuntimeError(
                "SimilarityPredictor.predict called before .train()/.load()"
            )
        if not self._corpus:
            return []
        vectorizer = self._transformers["vectorizer"]
        cos = self._transformers["similarity_fn"]
        q_text = getattr(query, "BriefFacts", None) or ""
        if not q_text:
            return []
        q_vec = vectorizer.transform([q_text])
        sims = cos(q_vec, self._matrix).ravel()
        # Rank by score; exclude the query itself if it's
        # in the corpus.
        qid = getattr(query, "CaseMasterID", None)
        order = sims.argsort()[::-1]
        out: list[PredictionResult] = []
        for idx in order:
            if qid is not None and self._corpus[idx].CaseMasterID == qid:
                continue
            score = float(sims[idx])
            if score <= 0.0:
                continue
            case = self._corpus[idx]
            out.append(
                PredictionResult(
                    value=int(case.CaseMasterID),
                    confidence=round(min(1.0, score), 4),
                    top_features=[
                        FeatureContribution(
                            feature="brief_facts",
                            value=case.BriefFacts[:30] + "...",
                            importance=score,
                        ),
                        FeatureContribution(
                            feature="crime_sub_head",
                            value=case.CrimeMinorHeadName,
                            importance=0.4,
                        ),
                    ],
                    evidence=[
                        EvidenceItem(
                            case_id=int(case.CaseMasterID),
                            fir_number=str(case.CrimeNo),
                            label=case.CrimeMinorHeadName,
                        )
                    ],
                )
            )
            if len(out) >= top_k:
                break
        return out

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, cases: Sequence[SyntheticCase]) -> dict:
        """Coverage + hit-rate.

        * coverage: fraction of cases that found at least
          one non-zero-similarity match.
        * hit_rate: fraction of cases whose top match shared
          the same crime sub-head (a proxy for "the
          predictor pointed at a similar crime").
        """
        if self._matrix is None or not self._corpus:
            return {"coverage": 0.0, "hit_rate": 0.0}
        # The corpus is set in train(); for the synthetic
        # demo we evaluate against the same rows the model
        # was trained on. Production code would hold out a
        # split.
        n = len(self._corpus)
        covered = 0
        hits = 0
        for case in self._corpus:
            results = self.predict(case, top_k=1)
            if results:
                covered += 1
                top = results[0]
                top_id = top.value
                # find the matching corpus row
                for c in self._corpus:
                    if c.CaseMasterID == top_id:
                        if c.CrimeMinorHeadName == case.CrimeMinorHeadName:
                            hits += 1
                        break
        return {
            "coverage": covered / n if n else 0.0,
            "hit_rate": hits / n if n else 0.0,
        }

    def save_to_store(self, store_dir=None) -> None:
        from backend.ml.services.model_store import save_atomic, store_path

        path = store_path(self.name, store_dir)
        # Override the default save: the corpus is part of
        # the predictor's state.
        save_atomic(self, str(path))


__all__ = ["SimilarityPredictor"]
