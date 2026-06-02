# P8: Training Scaffold (v2 Placeholder)

> **For agentic workers:** Use subagent-driven-development to implement task-by-task.

**Goal:** Create the `training/` directory scaffold for FinBERT fine-tuning. Files are stubs only — NOT executed in v1.

**Architecture:** Three stub files that raise NotImplementedError. Documented as v2 work.

---

### Task 1: Training scaffold files

**Files:**
- Create: `training/dataset.py`
- Create: `training/trainer.py`
- Create: `training/evaluate.py`

- [ ] **Step 1: Create training/dataset.py**

```python
# training/dataset.py
# v2: FinBERT fine-tuning dataset loader
# Sources: Financial PhraseBank, FiQA, SEntFiN via HuggingFace datasets
# Format: {"text": "...", "label": "positive|negative|neutral"}
# Split: 80% train / 10% val / 10% test
raise NotImplementedError("FinBERT fine-tuning is a v2 feature. See PLAN.md Part 4.")
```

- [ ] **Step 2: Create training/trainer.py**

```python
# training/trainer.py
# v2: HuggingFace Trainer for FinBERT fine-tuning
# Config: lr=2e-5, batch=16, epochs=3, warmup_steps=100
# Base model: ProsusAI/finbert
# Output: models/finbert-finetuned/
raise NotImplementedError("FinBERT fine-tuning is a v2 feature. See PLAN.md Part 4.")
```

- [ ] **Step 3: Create training/evaluate.py**

```python
# training/evaluate.py
# v2: Evaluate fine-tuned vs base FinBERT on test split
# Reports: accuracy, F1 per class, confusion matrix
raise NotImplementedError("FinBERT fine-tuning is a v2 feature. See PLAN.md Part 4.")
```

- [ ] **Step 4: Commit**

```bash
git add training/
git commit -m "feat: training/ scaffold stubs for v2 FinBERT fine-tuning"
```

---

## P8 Done — All Plans Written

| Plan | File | Status |
|------|------|--------|
| P1 | `docs/superpowers/plans/2026-06-02-p1-scaffolding.md` | Ready |
| P2 | `docs/superpowers/plans/2026-06-02-p2-storage.md` | Ready |
| P3 | `docs/superpowers/plans/2026-06-02-p3-agents-1-3.md` | Ready |
| P4 | `docs/superpowers/plans/2026-06-02-p4-agents-4-5.md` | Ready |
| P5 | `docs/superpowers/plans/2026-06-02-p5-agents-6-7-graph.md` | Ready |
| P6 | `docs/superpowers/plans/2026-06-02-p6-backtesting.md` | Ready |
| P7 | `docs/superpowers/plans/2026-06-02-p7-dashboard-gha.md` | Ready |
| P8 | `docs/superpowers/plans/2026-06-02-p8-training-scaffold.md` | Ready |

Implement in order P1→P8. Each plan is independently testable.
