"""Immutable datasets and deterministic disjoint splits; gold lives separately."""

import random
import re
import unicodedata
from pathlib import Path

from .records import Question
from .scoring import numeric
from .storage import atomic_json, digest, read_json, run_lock

FIXTURES = [
    ("What is 17 + 25?", "42"),
    ("What is 91 - 37?", "54"),
    ("What is 12 times 8?", "96"),
    ("What is 144 divided by 12?", "12"),
    ("What is -7 + 3?", "-4"),
    ("What is 2.5 + 1.75?", "4.25"),
    ("What is one half plus one quarter? Give a fraction or decimal.", "3/4"),
    ("Three boxes each hold 6 apples. You give away 5 apples. How many remain?", "13"),
    ("A $80 jacket is discounted by 25 percent. What is its price in dollars?", "60"),
    (
        "A train travels 150 kilometers in 2.5 hours. What is its average speed in kilometers per hour?",
        "60",
    ),
]
SPLIT_SIZES = {"pilot": 100, "train": 400, "validation": 100, "test": 500}


def normalized(prompt):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", prompt).casefold()).strip()


def check_questions(questions):
    ids, prompts = set(), set()
    for question in questions:
        if question.answer_type != "number" or not question.prompt.strip():
            raise ValueError("Only nonempty numeric questions are supported")
        content = normalized(question.prompt)
        if question.id in ids or content in prompts:
            raise ValueError(f"Duplicate ID or normalized question: {question.id}")
        ids.add(question.id)
        prompts.add(content)


def save_dataset(directory, questions, gold, metadata):
    directory = Path(directory)
    check_questions(questions)
    if set(gold) != {q.id for q in questions}:
        raise ValueError("Gold IDs must exactly match question IDs")
    for value in gold.values():
        numeric(value)
    rows = [q.to_dict() for q in questions]
    manifest = {
        "schema_version": 1,
        "metadata": metadata,
        "questions_sha256": digest(rows),
        "gold_sha256": digest(gold),
        "splits": {
            split: [q.id for q in questions if q.split == split]
            for split in sorted({q.split for q in questions})
        },
    }
    with run_lock(directory):
        if (directory / "manifest.json").exists():
            if read_json(directory / "manifest.json") != manifest:
                raise ValueError(f"Dataset already frozen with different content: {directory}")
            load_questions(directory)
            load_gold(directory)
            return directory
        atomic_json(directory / "questions.json", rows)
        atomic_json(directory / "gold.json", gold)
        atomic_json(directory / "manifest.json", manifest)
    return directory


def prepare_fixtures(directory):
    questions = [
        Question(f"arithmetic-{i:02d}", "arithmetic-v1", "smoke", prompt)
        for i, (prompt, _) in enumerate(FIXTURES)
    ]
    return save_dataset(
        directory,
        questions,
        {q.id: FIXTURES[i][1] for i, q in enumerate(questions)},
        {"source": "arithmetic-v1"},
    )


def freeze_gsm8k(train_rows, test_rows, directory, seed, revision, sizes=None):
    sizes = sizes or SPLIT_SIZES
    rng, seen, questions, gold = random.Random(seed), set(), [], {}
    # Prioritize official test when removing duplicates across upstream splits.
    pools = {}
    duplicates_removed = 0
    for upstream, rows in [("test", test_rows), ("train", train_rows)]:
        pool = []
        for row in rows:
            key = normalized(row["question"])
            if key in seen:
                duplicates_removed += 1
                continue
            seen.add(key)
            if "####" not in row["answer"]:
                raise ValueError("GSM8K row has no final-answer delimiter")
            answer = row["answer"].rsplit("####", 1)[1].strip()
            numeric(answer)
            pool.append((f"gsm8k-{upstream}-{digest(key)[:20]}", row["question"], answer))
        pool.sort()
        rng.shuffle(pool)
        pools[upstream] = pool
    if (
        len(pools["train"]) < sum(sizes[s] for s in ["pilot", "train", "validation"])
        or len(pools["test"]) < sizes["test"]
    ):
        raise ValueError("Not enough unique GSM8K questions for requested splits")
    offset = 0
    for split in ["pilot", "train", "validation", "test"]:
        selected = (
            pools["test"][: sizes[split]]
            if split == "test"
            else pools["train"][offset : offset + sizes[split]]
        )
        if split != "test":
            offset += sizes[split]
        for identifier, prompt, answer in selected:
            questions.append(Question(identifier, "openai/gsm8k:main", split, prompt))
            gold[identifier] = answer
    return save_dataset(
        directory,
        questions,
        gold,
        {
            "source": "openai/gsm8k",
            "subset": "main",
            "revision": revision,
            "seed": seed,
            "sizes": sizes,
            "duplicates_removed": duplicates_removed,
            "split_algorithm": "v1-test-first",
        },
    )


def prepare_gsm8k(directory, seed, revision="main", cache_dir=".cache/huggingface"):
    from datasets import load_dataset
    from huggingface_hub import HfApi

    resolved = HfApi().dataset_info("openai/gsm8k", revision=revision).sha
    data = load_dataset("openai/gsm8k", "main", revision=resolved, cache_dir=cache_dir)
    return freeze_gsm8k(data["train"], data["test"], directory, seed, resolved)


def load_questions(directory, split=None):
    directory = Path(directory)
    manifest, rows = read_json(directory / "manifest.json"), read_json(directory / "questions.json")
    if digest(rows) != manifest["questions_sha256"]:
        raise ValueError("Question artifact changed after split freeze")
    questions = [Question(**row) for row in rows]
    check_questions(questions)
    actual = {
        s: [q.id for q in questions if q.split == s] for s in sorted({q.split for q in questions})
    }
    if actual != manifest["splits"]:
        raise ValueError("Split manifest does not match questions")
    selected = [q for q in questions if split is None or q.split == split]
    if not selected:
        raise ValueError(f"No questions found for split {split!r}")
    return selected


def load_gold(directory):
    directory = Path(directory)
    manifest, gold = read_json(directory / "manifest.json"), read_json(directory / "gold.json")
    if digest(gold) != manifest["gold_sha256"]:
        raise ValueError("Scoring-only gold artifact changed after split freeze")
    return gold
