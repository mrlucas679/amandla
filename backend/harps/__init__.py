"""
HARPS — Human Action Recognition with Path Signatures
Integrated into AMANDLA for real-time SASL sign language recognition.

Subpackages
-----------
datasets    : JHMDB, MHAD, WLASL adapters + FeatureCacheBuilder
transforms  : Compose, PersonCentricNormalize, PSF feature extractors
models      : MLPClassifier, LinearNet
train       : Trainer, MLPTrainer, checkpoint, convergence monitoring
utils       : cache, metrics, scaler, pca, seed, runlog, feature_select
experiments : ablation runner, pipelines, logging
"""

from . import datasets, transforms, models, train, utils, experiments

__all__ = ["datasets", "transforms", "models", "train", "utils", "experiments"]