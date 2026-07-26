"""
Pattern clustering (unsupervised).

The clustering predictor groups cases into a small number of
"MO clusters" so the dashboard can show how many cases share
each modus operandi. We combine two feature spaces:

* A TF-IDF matrix built from each case's ``BriefFacts``
  field (which is short, keyword-rich text by design).
* A one-hot encoding of the categorical fields
  (``crime_head``, ``gravity``).

The two matrices are concatenated and fed to a
:class:`sklearn.cluster.KMeans`. The number of clusters is
small (5) — enough to surface distinct MO patterns without
over-fragmenting the synthetic 1k rows.

Public surface
==============

* :class:`ClusteringPredictor`
* :meth:`train(cases)` — fits the TF-IDF + one-hot pipeline
  and a KMeans on top.
* :meth:`predict(cases)` — returns one
  :class:`PredictionResult` per case, with the cluster id as
  the ``value`` and the cosine-style similarity to the
  cluster centroid as the ``confidence``.
* :meth:`evaluate(cases)` — silhouette score + inertia.

Notes
=====

The TF-IDF vocabulary is fitted during training and
persisted as a transformer. At inference time the same
vocabulary is used; new words are dropped (they don't have
a code).
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


def _head_one_hot(case, encoders: dict[str, dict[str, int]]):
    """Build a one-hot dict for the categorical columns."""
    head = case.CrimeMajorHeadName
    grav = case.GravityName
    sub = case.CrimeMinorHeadName
    head_table = encoders.setdefault("head", {})
    grav_table = encoders.setdefault("grav", {})
    sub_table = encoders.setdefault("sub", {})
    if head not in head_table:
        head_table[head] = len(head_table)
    if grav not in grav_table:
        grav_table[grav] = len(grav_table)
    if sub not in sub_table:
        sub_table[sub] = len(sub_table)
    return head, grav, sub


class ClusteringPredictor(BaseSklearnPredictor):
    """KMeans over TF-IDF + one-hot MO features."""

    name = "clustering"
    # Cluster count. Five is enough to surface distinct
    # patterns in the synthetic dataset without
    # over-fragmenting.
    n_clusters = 5

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, cases: Sequence[SyntheticCase]) -> "ClusteringPredictor":
        from sklearn.cluster import KMeans
        from sklearn.feature_extraction.text import TfidfVectorizer

        if not cases:
            raise ValueError("ClusteringPredictor.train needs at least 1 case")

        texts = [c.BriefFacts for c in cases]
        vectorizer = TfidfVectorizer(
            max_features=200,
            ngram_range=(1, 2),
            stop_words="english",
        )
        tfidf = vectorizer.fit_transform(texts)
        # One-hot for the categoricals.
        encoders: dict[str, dict[str, int]] = {}
        heads: list[str] = []
        gravs: list[str] = []
        subs: list[str] = []
        for c in cases:
            h, g, s = _head_one_hot(c, encoders)
            heads.append(h)
            gravs.append(g)
            subs.append(s)
        n_h, n_g, n_s = (
            len(encoders["head"]),
            len(encoders["grav"]),
            len(encoders["sub"]),
        )
        import numpy as np
        onehot = np.zeros((len(cases), n_h + n_g + n_s), dtype=float)
        for i in range(len(cases)):
            onehot[i, encoders["head"][heads[i]]] = 1.0
            onehot[i, n_h + encoders["grav"][gravs[i]]] = 1.0
            onehot[i, n_h + n_g + encoders["sub"][subs[i]]] = 1.0
        # Concatenate the sparse TF-IDF and the dense one-hot.
        from scipy.sparse import hstack, csr_matrix
        X = hstack([tfidf, csr_matrix(onehot)]).tocsr()
        model = KMeans(
            n_clusters=self.n_clusters,
            random_state=0,
            n_init=10,
        )
        model.fit(X)
        self._model = model
        self._transformers = {
            "vectorizer": vectorizer,
            "encoders": encoders,
            "n_h": n_h,
            "n_g": n_g,
            "n_s": n_s,
        }
        return self

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(self, cases) -> list[PredictionResult]:
        if self._model is None:
            raise RuntimeError(
                "ClusteringPredictor.predict called before .train()/.load()"
            )
        from scipy.sparse import hstack, csr_matrix
        import numpy as np

        vectorizer = self._transformers["vectorizer"]
        encoders = self._transformers["encoders"]
        n_h = self._transformers["n_h"]
        n_g = self._transformers["n_g"]
        n_s = self._transformers["n_s"]

        texts = [getattr(c, "BriefFacts", "") or "" for c in cases]
        tfidf = vectorizer.transform(texts)
        onehot = np.zeros((len(cases), n_h + n_g + n_s), dtype=float)
        for i, c in enumerate(cases):
            h = getattr(c, "CrimeMajorHeadName", None)
            g = getattr(c, "GravityName", None)
            s = getattr(c, "CrimeMinorHeadName", None)
            if h in encoders["head"]:
                onehot[i, encoders["head"][h]] = 1.0
            if g in encoders["grav"]:
                onehot[i, n_h + encoders["grav"][g]] = 1.0
            if s in encoders["sub"]:
                onehot[i, n_h + n_g + encoders["sub"][s]] = 1.0
        X = hstack([tfidf, csr_matrix(onehot)]).tocsr()
        labels = self._model.predict(X)
        # Distance to the assigned centroid → similarity.
        dists = self._model.transform(X)  # (n, k)
        out: list[PredictionResult] = []
        for i, label in enumerate(labels):
            d = float(dists[i, label])
            # Normalise: invert and clamp to [0, 1]. A
            # distance of 0 -> 1.0; 2.0+ -> ~0.1.
            conf = max(0.0, min(1.0, 1.0 - d / 2.0))
            case_id = getattr(cases[i], "CaseMasterID", None)
            top = [
                FeatureContribution(
                    feature="brief_facts", value=texts[i][:30] + "...",
                    importance=0.6,
                ),
                FeatureContribution(
                    feature="crime_head", value=str(
                        getattr(cases[i], "CrimeMajorHeadName", "?")
                    ),
                    importance=0.4,
                ),
            ]
            ev = []
            if case_id is not None:
                ev.append(
                    EvidenceItem(
                        case_id=int(case_id),
                        label=f"MO cluster {int(label)}",
                    )
                )
            out.append(
                PredictionResult(
                    value=int(label),
                    confidence=round(conf, 4),
                    top_features=top,
                    evidence=ev,
                )
            )
        return out

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, cases: Sequence[SyntheticCase]) -> dict:
        from sklearn.metrics import silhouette_score

        if self._model is None:
            raise RuntimeError("ClusteringPredictor not trained yet")
        from scipy.sparse import hstack, csr_matrix
        import numpy as np

        vectorizer = self._transformers["vectorizer"]
        encoders = self._transformers["encoders"]
        n_h = self._transformers["n_h"]
        n_g = self._transformers["n_g"]
        n_s = self._transformers["n_s"]
        texts = [c.BriefFacts for c in cases]
        tfidf = vectorizer.transform(texts)
        onehot = np.zeros((len(cases), n_h + n_g + n_s), dtype=float)
        for i, c in enumerate(cases):
            h, g, s = _head_one_hot(c, encoders)
            onehot[i, encoders["head"][h]] = 1.0
            onehot[i, n_h + encoders["grav"][g]] = 1.0
            onehot[i, n_h + n_g + encoders["sub"][s]] = 1.0
        X = hstack([tfidf, csr_matrix(onehot)]).tocsr()
        labels = self._model.predict(X)
        inertia = float(self._model.inertia_)
        sil = float(silhouette_score(X, labels)) if len(set(labels)) > 1 else 0.0
        return {
            "k": int(self.n_clusters),
            "inertia": inertia,
            "silhouette": sil,
        }

    def save_to_store(self, store_dir=None) -> None:
        from backend.ml.services.model_store import save_atomic, store_path

        path = store_path(self.name, store_dir)
        save_atomic(self, str(path))


__all__ = ["ClusteringPredictor"]
