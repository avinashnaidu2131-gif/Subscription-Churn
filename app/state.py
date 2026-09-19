"""
Tiny process-wide singleton holder for the loaded model/optimizer.

Kept separate from api/main.py so api/routes.py can import it without a
circular import (main.py -> routes.py -> main.py). Swap for a proper model
registry / dependency-injection container if this grows beyond a prototype.
"""
from typing import Optional

from app.ml.model import RetryModel
from app.optimizer.retry_optimizer import RetryOptimizer

_optimizer: Optional[RetryOptimizer] = None


def set_model(model: RetryModel) -> None:
    global _optimizer
    _optimizer = RetryOptimizer(model)


def get_optimizer(raise_if_missing: bool = True) -> Optional[RetryOptimizer]:
    if _optimizer is None and raise_if_missing:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail="Model not loaded yet. Run `python scripts/train_pipeline.py` first, then restart the server.",
        )
    return _optimizer
