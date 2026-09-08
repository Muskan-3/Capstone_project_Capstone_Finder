"""Inference for the fine-tuned small-talk model.

    from generate import SmallTalker
    bot = SmallTalker()            # loads models/projectlens-final/
    bot.reply("who are you")

Only ever called for messages the intent router sent to "smalltalk". Task
messages never reach this file.
"""

from __future__ import annotations

import re

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from common import FINAL_DIR, STAGE1_DIR, device


def _first_sentences(text: str, n: int = 2) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    out = " ".join(parts[:n]).strip()
    return out or text.strip()


class SmallTalker:
    def __init__(self, model_dir: str | None = None):
        path = model_dir or (str(FINAL_DIR) if FINAL_DIR.exists() else str(STAGE1_DIR))
        self.dev = device()
        self.tok = AutoTokenizer.from_pretrained(path)
        self.model = AutoModelForCausalLM.from_pretrained(path).to(self.dev)
        self.model.eval()

    @torch.no_grad()
    def reply(self, text: str, *, greedy: bool = False, max_new_tokens: int = 50) -> str:
        prompt = f"{text}{self.tok.eos_token}"
        enc = self.tok(prompt, return_tensors="pt").to(self.dev)
        out = self.model.generate(
            input_ids=enc["input_ids"],
            attention_mask=enc["attention_mask"],
            max_new_tokens=max_new_tokens,
            pad_token_id=self.tok.pad_token_id or self.tok.eos_token_id,
            eos_token_id=self.tok.eos_token_id,
            do_sample=not greedy,
            top_p=0.92,
            top_k=50,
            temperature=0.7,
            repetition_penalty=1.3,
            no_repeat_ngram_size=3,
        )
        gen = out[0][enc["input_ids"].shape[-1]:]
        reply = self.tok.decode(gen, skip_special_tokens=True)
        reply = reply.split(self.tok.eos_token)[0].strip()
        return _first_sentences(reply, n=2) or "(empty reply)"
