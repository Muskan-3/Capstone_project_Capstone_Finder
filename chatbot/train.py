"""Two-stage causal-LM fine-tune for the small-talk layer.

    python train.py --stage 1        # tone, from microsoft/DialoGPT-small
    python train.py --stage 2        # identity + guardrails, from the stage-1 model

Stage 1 teaches a neutral human conversational tone (PersonaChat pairs, personas
stripped). Stage 2 continues from that checkpoint on ~200 curated identity /
guardrail examples - a few more epochs, deliberately allowed to slightly overfit
so the identity answers are reliable.

Runs unmodified on a CUDA GPU (Colab T4), Apple MPS, or plain CPU (slow - use
--max-samples for a local smoke test).
"""

from __future__ import annotations

import argparse

from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)

from common import (
    BASE_MODEL,
    FINAL_DIR,
    IDENTITY_FILE,
    PAIRS_FILE,
    STAGE1_DIR,
    device,
    read_jsonl,
    use_fp16,
)

MAX_LEN = 128


def load_tokenizer(source: str) -> AutoTokenizer:
    tok = AutoTokenizer.from_pretrained(source)
    # DialoGPT / GPT-2 have no pad token. Adding a *distinct* one (rather than
    # pad = eos) matters: the LM-collator masks pad positions in the labels, and
    # if pad == eos it would also mask every real end-of-turn token, so the model
    # would never learn to stop generating.
    if tok.pad_token is None:
        tok.add_special_tokens({"pad_token": "[PAD]"})
    return tok


def build_dataset(rows: list[dict], tok: AutoTokenizer) -> Dataset:
    texts = [
        f"{r['input']}{tok.eos_token}{r['response']}{tok.eos_token}" for r in rows
    ]

    def tokenize(batch):
        return tok(batch["text"], truncation=True, max_length=MAX_LEN)

    ds = Dataset.from_dict({"text": texts})
    return ds.map(tokenize, batched=True, remove_columns=["text"])


def finetune(stage: int, epochs: float, batch_size: int, lr: float, max_samples: int | None) -> None:
    if stage == 1:
        source, out_dir, data_file = BASE_MODEL, STAGE1_DIR, PAIRS_FILE
    elif stage == 2:
        if not STAGE1_DIR.exists():
            raise SystemExit(f"Stage 1 model not found at {STAGE1_DIR} - run --stage 1 first.")
        source, out_dir, data_file = str(STAGE1_DIR), FINAL_DIR, IDENTITY_FILE
    else:
        raise SystemExit("--stage must be 1 or 2")

    if not data_file.exists():
        raise SystemExit(f"data file missing: {data_file}")

    rows = read_jsonl(data_file)
    if max_samples:
        rows = rows[:max_samples]
    print(f"stage {stage}: {len(rows):,} examples | base={source} | device={device()}")

    tok = load_tokenizer(source)
    model = AutoModelForCausalLM.from_pretrained(source)
    model.resize_token_embeddings(len(tok))  # picks up the [PAD] token if added

    ds = build_dataset(rows, tok)
    collator = DataCollatorForLanguageModeling(tokenizer=tok, mlm=False)

    args = TrainingArguments(
        output_dir=str(out_dir / "_trainer"),
        overwrite_output_dir=True,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        learning_rate=lr,
        warmup_ratio=0.05,
        logging_steps=25,
        save_strategy="no",
        report_to=[],
        fp16=use_fp16(),
        dataloader_pin_memory=False,
    )

    trainer = Trainer(model=model, args=args, train_dataset=ds, data_collator=collator)
    trainer.train()

    out_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(out_dir))
    tok.save_pretrained(str(out_dir))
    print(f"saved -> {out_dir}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, required=True, choices=(1, 2))
    ap.add_argument("--epochs", type=float, default=None)
    ap.add_argument("--batch-size", type=int, default=None)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--max-samples", type=int, default=None,
                    help="cap training rows (for a quick local smoke run)")
    args = ap.parse_args()

    # per-stage defaults (overridable): stage 1 is about tone, stage 2 about
    # nailing identity answers, so it gets more passes over less data.
    epochs = args.epochs if args.epochs is not None else (1.0 if args.stage == 1 else 8.0)
    batch = args.batch_size if args.batch_size is not None else (8 if args.stage == 1 else 4)

    finetune(args.stage, epochs, batch, args.lr, args.max_samples)


if __name__ == "__main__":
    main()
