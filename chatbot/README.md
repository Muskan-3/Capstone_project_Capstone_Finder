# Small-talk layer — two-stage offline fine-tune

A tiny fine-tuned dialogue model that handles **only** greetings, identity
questions, thanks/farewells, and gentle "that's off-topic" redirects. Real
project recommendations never touch it — they stay on the TF-IDF + KMeans
engine in `../backend`. `intent_router.py` is the hard boundary between the two.

```
message ─▶ intent_router.classify()
             ├─ greeting / identity / thanks / farewell / offtopic ─▶ fine-tuned DialoGPT
             └─ recommend (or anything ambiguous)                  ─▶ backend recommendation engine
```

## Files

| File | What it does |
|---|---|
| `prepare_stage1_data.py` | Build `data/personachat_pairs.jsonl` from `bavard/personachat_truecased` (personas dropped) |
| `build_identity_data.py` | Write `data/identity_examples.jsonl` — the ~300 curated identity/guardrail examples |
| `train.py` | `--stage 1` (tone, from DialoGPT-small) and `--stage 2` (identity, from the stage-1 model) |
| `intent_router.py` | Rule-based `classify(message) -> Route(destination, intent)` — the guardrail |
| `generate.py` | `SmallTalker().reply(text)` — inference for `smalltalk`-routed messages only |
| `chat_test.py` | Runs the brief's four prompts + router checks, flags on-script vs drifted |
| `integrate_example.py` | Reference for wiring router + model + engine together |
| `common.py` | Paths, device detection (CUDA → MPS → CPU) |

## Run it

### Locally (CPU/MPS — fine for Stage 2, too slow for full Stage 1)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python build_identity_data.py                 # Stage 2 data (instant)
python prepare_stage1_data.py                 # Stage 1 data (~1 min download)

# quick smoke test of the training code:
python train.py --stage 1 --max-samples 400 --epochs 1
python train.py --stage 2                     # full Stage 2, a few minutes
python chat_test.py
```

### Full quality — Google Colab (free T4 GPU)

`prepare_stage1_data.py` on the full 139k pairs + `train.py --stage 1` at
1–2 epochs needs a GPU. Open `colab.ipynb` (or paste the commands below into a
Colab notebook set to **Runtime → GPU**):

```python
!git clone <your repo url> && cd <repo>/chatbot
!pip install -q -r requirements.txt
!python build_identity_data.py
!python prepare_stage1_data.py
!python train.py --stage 1 --epochs 2 --batch-size 8
!python train.py --stage 2 --epochs 8 --batch-size 4
!python chat_test.py
```

Then download `models/projectlens-final/` and drop it back into `chatbot/models/`
locally, or push it to somewhere the backend can load it from.

## The guardrail rule

`train.py` and `generate.py` produce a model that only ever sees messages the
router labelled `smalltalk`. A message asking for a project — or anything the
router isn't sure about — goes to `task`, i.e. the grounded engine. The
generative model is structurally incapable of inventing a project suggestion
because it is never called for that path. Don't remove the router.

## Note on the identity name

`build_identity_data.py` has `ASSISTANT_NAME = "Capstone Compass"` (the name the
deployed product uses). Change that one constant and rerun the script if the
bot should introduce itself differently.
