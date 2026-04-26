from __future__ import annotations

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
import numpy as np

from apps.predictions.services.intent_types import IntentClass

NGRAM_RANGE = (1, 3)
MIN_DF = 1
REGULARISATION_C = 2.0
MAX_ITER = 1000
CV_FOLDS = 5


class IntentClassifier:
    def __init__(self) -> None:
        self._pipeline: Pipeline | None = None
        self.cv_accuracy: float = 0.0

    def _build_pipeline(self) -> Pipeline:
        return Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=NGRAM_RANGE,
                min_df=MIN_DF,
                sublinear_tf=True,
            )),
            ("clf", LogisticRegression(
                C=REGULARISATION_C,
                max_iter=MAX_ITER,
                class_weight="balanced",
                solver="lbfgs",
            )),
        ])

    def train(self) -> None:
        from apps.predictions.services.training_data import TRAINING_EXAMPLES
        texts = [q for q, _ in TRAINING_EXAMPLES]
        labels = [label.value for _, label in TRAINING_EXAMPLES]
        pipeline = self._build_pipeline()
        scores = cross_val_score(pipeline, texts, labels, cv=CV_FOLDS, scoring="accuracy")
        self.cv_accuracy = float(np.mean(scores))
        pipeline.fit(texts, labels)
        self._pipeline = pipeline

    def classify(self, query: str) -> tuple[IntentClass, float]:
        if self._pipeline is None:
            self.train()
        probas = self._pipeline.predict_proba([query])[0]
        classes = self._pipeline.classes_
        idx = int(np.argmax(probas))
        return IntentClass(classes[idx]), float(probas[idx])

    def get_cv_accuracy(self) -> float:
        if self._pipeline is None:
            self.train()
        return self.cv_accuracy


_CLASSIFIER_INSTANCE: IntentClassifier | None = None


def get_classifier() -> IntentClassifier:
    global _CLASSIFIER_INSTANCE
    if _CLASSIFIER_INSTANCE is None:
        _CLASSIFIER_INSTANCE = IntentClassifier()
    return _CLASSIFIER_INSTANCE


def reset_classifier() -> None:
    global _CLASSIFIER_INSTANCE
    _CLASSIFIER_INSTANCE = None