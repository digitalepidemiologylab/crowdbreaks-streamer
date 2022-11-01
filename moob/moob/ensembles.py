import numpy as np
from sklearn.base import clone
from strlearn.ensembles.base import StreamingEnsemble

class MOOB(StreamingEnsemble):
    """
    Multiclass Oversamping-Based Online Bagging.
    """
    def __init__(
        self, base_estimator=None, n_estimators=5, time_decay_factor=0.9):
        """Initialization."""
        super().__init__(base_estimator, n_estimators)
        self.time_decay_factor = time_decay_factor
        # The text below comes from S. Wang, L. L. Minku, and X. Yao,
        # “Dealing with Multiple Classes in Online Class Imbalance Learning”,
        # p. 7: The pre-defined time decay factor forces older data to have
        # less impact on the class percentage, so that self.current_tdcs_
        # is adjusted more based on new data.
        # The default value of the time decay factor is 0.9 [ref 1]:
        # this choice was shown to be a reasonable setting to balance
        # the responding speed and estimation variance.
        # Ref 1: S. Wang, L. L. Minku, and X. Yao. A learning framework for
        # online class imbalance learning. In IEEE Symposium on Computational
        # Intelligence and Ensemble Learning (CIEL), pages 36–45, 2013.


    def partial_fit(self, X, y, classes=None):
        y = y.astype(np.int64)
        super().partial_fit(X, y, classes)
        if not self.green_light:
            return self

        if len(self.ensemble_) == 0:
            self.ensemble_ = [
                clone(self.base_estimator) for i in range(self.n_estimators)
            ]

        # time decayed class sizes tracking
        if not hasattr(self, "last_instance_sizes"):
            self.current_tdcs_ = np.zeros((1, self.classes_.shape[0]))
        else:
            self.current_tdcs_ = self.last_instance_sizes

        self.chunk_tdcs = np.ones((self.X_.shape[0], self.classes_.shape[0]))

        for iteration, label in enumerate(self.y_):
            complementary_labels = [c for c in self.classes_ if c != label]
            self.current_tdcs_[0, label] = (
                    self.current_tdcs_[0, label] * self.time_decay_factor
                ) + (1 - self.time_decay_factor)
            for k in complementary_labels:
                self.current_tdcs_[0, k] = (
                    self.current_tdcs_[0, k] * self.time_decay_factor
                )

            self.chunk_tdcs[iteration] = self.current_tdcs_

        self.last_instance_sizes = self.current_tdcs_

        # Multiclass oversampling-based online bagging (MOOB)
        self.weights = []
        for instance, label in enumerate(self.y_):
            max_class_size = max(self.chunk_tdcs[instance])
            instance_class_size = self.chunk_tdcs[instance][label]
            lmbda = max_class_size / instance_class_size

            K = np.asarray(
                [np.random.poisson(lam=lmbda, size=1)[0]
                 for i in range(self.n_estimators)]
            )

            self.weights.append(K)

        self.weights = np.asarray(self.weights).T

        for w, base_model in enumerate(self.ensemble_):
            base_model.partial_fit(
                self.X_, self.y_, self.classes_, sample_weight=self.weights[w]
            )

        return self
