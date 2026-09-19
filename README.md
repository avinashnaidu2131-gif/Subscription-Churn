# FT-04: Subscription Churn Automation

AI middleware that mitigates passive credit-card churn for SaaS/D2C platforms.
Given a failed transaction, it:

1. **Categorizes the decline code** — decides whether it's even worth retrying
   (a `do_not_honor` is retryable but risky; an `expired_card` is not).
2. **Maps the issuing-bank / card-network pattern** — determines the
   cardholder's timezone and how aggressively that issuer's risk rules
   should throttle retry attempts.
3. **Predicts the optimal retry schedule** with a CatBoost model — ranks
   candidate `(gateway, day, hour)` slots by predicted success probability.
4. **Explains itself** via SHAP, so you can see exactly which signals (decline
   code, bank, timing) drive each prediction.

## Project layout

```
churn-retry-middleware/
├── app/
│   ├── config.py               # shared feature schema, paths, constants
│   ├── domain/
│   │   ├── decline_taxonomy.py # categorizes decline codes (retryable? cooldown? category?)
│   │   └── bank_network_map.py # bank -> network, region, timezone, risk sensitivity
│   ├── data/
│   │   └── generator.py        # synthetic dataset generator (2,000 mock failed txns)
│   ├── ml/
│   │   ├── model.py            # CatBoostClassifier wrapper (train/predict/save/load)
│   │   └── explain.py          # SHAP summary plot
│   ├── optimizer/
│   │   └── retry_optimizer.py  # combines taxonomy + bank map + model into a schedule
│   ├── api/
│   │   ├── main.py             # FastAPI app + startup model loading
│   │   ├── routes.py           # /optimize-retry, /decline-codes, /bank-patterns, /health
│   │   └── schemas.py          # Pydantic request/response models
│   ├── state.py                # process-wide model/optimizer singleton
│   └── artifacts/              # generated: retry_model.cbm, shap_summary.png, synthetic_retry_data.csv
├── scripts/
│   └── train_pipeline.py       # orchestrates: generate data -> train -> save -> SHAP
├── requirements.txt
└── README.md
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
```

## Run

```bash
# 1. Train the model once (generates data, trains CatBoost, saves the model
#    artifact, and writes the SHAP plot to app/artifacts/shap_summary.png)
python scripts/train_pipeline.py

# 2. Start the API (loads the saved model at startup)
uvicorn app.api.main:app --reload --port 8000
```

Interactive docs: http://127.0.0.1:8000/docs

## API

### `POST /optimize-retry`
Given a failed transaction, returns either a ranked retry schedule or a
no-retry verdict (for hard declines like `expired_card`).

```bash
curl -X POST http://127.0.0.1:8000/optimize-retry \
  -H "Content-Type: application/json" \
  -d '{
        "transaction_id": "txn_12345",
        "decline_code": "insufficient_funds",
        "issuing_bank": "Chase"
      }'
```

```bash
# A hard decline returns retryable: false and no schedule
curl -X POST http://127.0.0.1:8000/optimize-retry \
  -H "Content-Type: application/json" \
  -d '{
        "transaction_id": "txn_99999",
        "decline_code": "expired_card",
        "issuing_bank": "HDFC Bank"
      }'
```

### `GET /decline-codes` / `GET /decline-codes/{code}`
Exposes the decline-code categorization taxonomy (category, retryable,
minimum cooldown, description).

### `GET /bank-patterns` / `GET /bank-patterns/{bank}`
Exposes the issuing-bank/network pattern map (card network, region,
timezone, risk sensitivity, weekly retry cap).

### `GET /health`
Reports whether the trained model is currently loaded.

## Notes on the "intelligent, localized" part

- Every candidate retry slot is generated in the **issuing bank's own
  timezone** (via `zoneinfo`), then converted to UTC for scheduling — so a
  retry recommended for "10am" actually means 10am where the cardholder's
  bank operates, not 10am UTC.
- Banks tagged `high` decline-sensitivity (e.g. HDFC, ICICI, Wells Fargo in
  this mock data) get both a lower weekly retry cap and a probability
  penalty, so the optimizer doesn't over-retry against issuers known to
  enforce tighter velocity/risk rules.
- Hard declines (`expired_card`, `invalid_cvv`) never produce a retry
  schedule — the API tells you to route those to a "update your payment
  method" flow instead, since no amount of retry timing fixes them.

## Extending this prototype

- Swap `app/data/generator.py` for a real query against your transaction
  warehouse — everything downstream only depends on the shared feature
  schema in `app/config.py`.
- `app/domain/*` is pure config/business-logic — safe to expand with real
  bank-specific data (more banks, real regional business-hour curves) without
  touching the model or API code.
- For production, replace the in-process model singleton (`app/state.py`)
  with a proper model registry, and add authentication to the API.
