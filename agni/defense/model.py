"""Sentinel: tabular + text fusion detector.

Tabular head  : HistGradientBoosting over engineered transaction features.
Text head     : TF-IDF + logistic regression over message/document artifacts,
                max-pooled to the sending account.
Fusion score  : weighted blend (text weight configurable, default 0.2).

Threshold policy: maximize F1 subject to false-positive rate on legitimate
traffic staying within the configured budget (default 0.5%).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score


class FusionDetector:
    def __init__(self, seed: int = 7, text_weight: float = 0.2):
        self.seed = seed
        self.text_weight = text_weight
        self.tab = HistGradientBoostingClassifier(
            max_iter=250, learning_rate=0.08, max_leaf_nodes=31,
            min_samples_leaf=20, l2_regularization=1.0, random_state=seed)
        self.text_ready = False

    # ------------------------------------------------------------------- fit
    def fit(self, X: pd.DataFrame, y: np.ndarray,
            artifacts: pd.DataFrame | None = None) -> "FusionDetector":
        y = np.asarray(y)
        n_pos = max(int(y.sum()), 1)
        n_neg = max(int(len(y) - n_pos), 1)
        sw = np.where(y == 1, len(y) / (2 * n_pos), len(y) / (2 * n_neg))
        self.tab.fit(X, y, sample_weight=sw)

        if artifacts is not None and len(artifacts) >= 40:
            counts = artifacts["label"].value_counts()
            if min(counts.get(0, 0), counts.get(1, 0)) >= 20:
                self._vec = TfidfVectorizer(max_features=20000, ngram_range=(1, 2),
                                            min_df=2, sublinear_tf=True)
                Z = self._vec.fit_transform(artifacts["text"])
                self._txt = LogisticRegression(C=8.0, max_iter=2000,
                                               class_weight="balanced",
                                               random_state=self.seed)
                self._txt.fit(Z, artifacts["label"].to_numpy())
                self.text_ready = True
        return self

    # --------------------------------------------------------------- scoring
    def account_text_scores(self, artifacts: pd.DataFrame) -> dict[str, float]:
        """Max fraud probability per source account from its artifacts."""
        if not self.text_ready or artifacts is None or not len(artifacts):
            return {}
        probs = self._txt.predict_proba(
            self._vec.transform(artifacts["text"]))[:, 1]
        return (pd.DataFrame({"src": artifacts["src"].to_numpy(), "p": probs})
                .groupby("src")["p"].max().to_dict())

    def predict_proba(self, X: pd.DataFrame,
                      acct_text: dict[str, float] | None = None) -> np.ndarray:
        p_tab = self.tab.predict_proba(X)[:, 1]
        if not acct_text or not hasattr(X, "columns") or "src" not in getattr(X, "columns", []):
            return p_tab
        w = self.text_weight
        srcs = X["src"].to_numpy()
        t = np.array([acct_text.get(s, -1.0) for s in srcs])
        has = t >= 0
        out = p_tab.copy()
        out[has] = (1 - w) * p_tab[has] + w * t[has]
        return np.clip(out, 0, 1)

    # ---------------------------------------------------------------- metrics
    @staticmethod
    def choose_threshold(p: np.ndarray, y: np.ndarray,
                         fpr_budget: float = 0.005) -> float:
        legit = p[y == 0]
        if not len(legit):
            return 0.5
        cands = np.unique(np.quantile(legit, np.linspace(0.90, 0.9995, 120)))
        best_thr, best_f1 = 0.9999, -1.0
        for thr in cands:
            pred = p >= thr
            fpr = float((pred & (y == 0)).sum()) / max((y == 0).sum(), 1)
            tp = float((pred & (y == 1)).sum())
            prec = tp / max(float(pred.sum()), 1e-9)
            rec = tp / max((y == 1).sum(), 1)
            f1 = 2 * prec * rec / max(prec + rec, 1e-9)
            if fpr <= fpr_budget and f1 > best_f1:
                best_f1, best_thr = f1, float(thr)
        return best_thr

    @staticmethod
    def evaluate(p: np.ndarray, y: np.ndarray, thr: float,
                 fpr_budget: float = 0.005) -> dict:
        pred = (p >= thr).astype(int)
        prec, rec, f1, _ = precision_recall_fscore_support(
            y, pred, average="binary", zero_division=0)
        auc = roc_auc_score(y, p) if 0 < y.sum() < len(y) else 0.5
        fpr = float((pred[y == 0] == 1).mean()) if (y == 0).any() else 0.0
        return {"threshold": round(float(thr), 6),
                "precision": round(float(prec), 4), "recall": round(float(rec), 4),
                "f1": round(float(f1), 4), "roc_auc": round(float(auc), 4),
                "fpr": round(fpr, 5), "fpr_ok": bool(fpr <= fpr_budget)}
