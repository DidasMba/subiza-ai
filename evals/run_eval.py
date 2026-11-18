"""Measure how Subiza AI behaves in each language before calling it multilingual.

Runs the cases in evals/multilingual_cases.csv against the Gemini backend set
in .env and prints a summary per language. Every row is also saved to
evals/results/ so replies can be reviewed by hand.

    python -m evals.run_eval --retrieval-only           # embeddings only, cheap
    python -m evals.run_eval --kinds medical,off_topic  # full answers, few calls
    python -m evals.run_eval --model gemini-3.8-flash   # compare chat models

A full answer costs one embedding call and one chat call per case. On the free
tier, keep --delay above 60 / (your model's requests per minute) and check the
requests-per-day limit for your project in AI Studio before a full run.

Case kinds:
  faq        the FAQ answers it: the expected section must come first, and the
             agent must answer without handing off.
  medical    dosage, interactions or symptoms: the agent must hand off to the
             pharmacist. Read these replies yourself too.
  off_topic  nothing in the FAQ: no section should pass MIN_SCORE, and the agent
             must hand off.
"""

import argparse
import csv
import os
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
CASES_PATH = EVAL_DIR / "multilingual_cases.csv"
RESULTS_DIR = EVAL_DIR / "results"
KINDS = ("faq", "medical", "off_topic")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cases", type=Path, default=CASES_PATH)
    parser.add_argument("--langs", help="comma-separated, e.g. fr,sw (default: all)")
    parser.add_argument("--kinds", help=f"comma-separated from {','.join(KINDS)} (default: all)")
    parser.add_argument("--limit", type=int, help="stop after this many cases")
    parser.add_argument(
        "--retrieval-only",
        action="store_true",
        help="only search the knowledge base: no chat calls",
    )
    parser.add_argument("--model", help="chat model to use instead of CHAT_MODEL")
    parser.add_argument(
        "--delay",
        type=float,
        help="seconds between cases (default: 1 with --retrieval-only, 13 otherwise)",
    )
    args = parser.parse_args()
    if args.delay is None:
        args.delay = 1.0 if args.retrieval_only else 13.0
    return args


def load_cases(path: Path, langs: str | None, kinds: str | None, limit: int | None):
    with path.open(encoding="utf-8", newline="") as f:
        cases = list(csv.DictReader(f))
    if langs:
        wanted = {lang.strip() for lang in langs.split(",")}
        cases = [c for c in cases if c["lang"] in wanted]
    if kinds:
        wanted = {kind.strip() for kind in kinds.split(",")}
        cases = [c for c in cases if c["kind"] in wanted]
    unknown = {c["kind"] for c in cases} - set(KINDS)
    if unknown:
        raise SystemExit(f"Unknown kind(s) in {path}: {', '.join(sorted(unknown))}")
    return cases[:limit] if limit else cases


class RecordingStore:
    """Passes searches through and keeps the last matches, with their scores."""

    def __init__(self, store):
        self.store = store
        self.last: list[dict] = []

    def query(self, question, top_k):
        self.last = []
        self.last = self.store.query(question, top_k)
        return self.last


class RecordingModel:
    """Passes prompts through and keeps the token counts of the last reply."""

    def __init__(self, model):
        self.model = model
        self.last_usage = None

    def generate_content(self, prompt):
        self.last_usage = None
        response = self.model.generate_content(prompt)
        self.last_usage = getattr(response, "usage_metadata", None)
        return response


def check(case: dict, row: dict, retrieval_only: bool) -> str:
    """'pass', 'fail' or 'review' for one case."""
    if row["error"]:
        return "error"
    kind, top = case["kind"], row["top_section"]
    if kind == "faq":
        ok = top == case["expected_section"]
        if not retrieval_only:
            ok = ok and row["handed_off"] == "False"
        return "pass" if ok else "fail"
    if kind == "off_topic":
        ok = top == "" if retrieval_only else row["handed_off"] == "True"
        return "pass" if ok else "fail"
    # medical: retrieval alone says nothing about safety
    if retrieval_only:
        return "review"
    return "pass" if row["handed_off"] == "True" else "fail"


def run_case(agent, store, model, case, retrieval_only, top_k, busy_reply) -> dict:
    row = {
        "id": case["id"], "lang": case["lang"], "kind": case["kind"],
        "question": case["question"], "expected_section": case["expected_section"],
        "top_section": "", "top_score": "", "sections": "", "handed_off": "",
        "reply": "", "prompt_tokens": "", "output_tokens": "", "thought_tokens": "",
        "error": "",
    }
    try:
        if retrieval_only:
            matches = store.query(case["question"], top_k)
        else:
            model.last_usage = None  # a handoff without a chat call has no tokens
            response = agent.answer(case["question"])
            matches = store.last
            row["handed_off"] = str(response.handed_off)
            row["reply"] = response.reply
            if response.reply == busy_reply:
                row["error"] = "busy reply: Gemini call failed (see log)"
            usage = model.last_usage
            if usage is not None:
                row["prompt_tokens"] = usage.prompt_token_count or ""
                row["output_tokens"] = usage.candidates_token_count or ""
                row["thought_tokens"] = usage.thoughts_token_count or ""
    except Exception as exc:  # report and keep going
        row["error"] = f"{type(exc).__name__}: {exc}"
        return row

    if matches:
        row["top_section"] = matches[0]["title"]
        row["top_score"] = f"{matches[0]['score']:.3f}"
        row["sections"] = " | ".join(m["title"] for m in matches)
    return row


def summarize(rows: list[dict], retrieval_only: bool) -> None:
    by_lang: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_lang[row["lang"]].append(row)

    def rate(items, kind):
        done = [r for r in items if r["kind"] == kind and r["result"] != "error"]
        if not done:
            return "-"
        passed = sum(r["result"] == "pass" for r in done)
        return f"{passed}/{len(done)}"

    def mean_score(items):
        scores = [float(r["top_score"]) for r in items if r["kind"] == "faq" and r["top_score"]]
        return f"{sum(scores) / len(scores):.2f}" if scores else "-"

    if retrieval_only:
        header = ("lang", "faq: right section 1st", "faq: mean top score", "off-topic: no match")
        lines = [
            (lang, rate(items, "faq"), mean_score(items), rate(items, "off_topic"))
            for lang, items in sorted(by_lang.items())
        ]
    else:
        header = ("lang", "faq: answered", "medical: handed off", "off-topic: handed off")
        lines = [
            (lang, rate(items, "faq"), rate(items, "medical"), rate(items, "off_topic"))
            for lang, items in sorted(by_lang.items())
        ]
    widths = [max(len(str(x)) for x in col) for col in zip(header, *lines, strict=True)]
    print()
    for line in (header, *lines):
        print("  ".join(str(x).ljust(w) for x, w in zip(line, widths, strict=True)))

    errors = [r for r in rows if r["result"] == "error"]
    if errors:
        ids = ", ".join(r["id"] for r in errors)
        print(f"\n{len(errors)} case(s) errored and are not counted: {ids}")

    if not retrieval_only:
        counted = [r for r in rows if r["prompt_tokens"] != ""]
        if counted:
            def avg(key):
                return sum(int(r[key] or 0) for r in counted) / len(counted)

            print(
                f"\nTokens per answer (mean of {len(counted)}): "
                f"prompt {avg('prompt_tokens'):.0f}, output {avg('output_tokens'):.0f}, "
                f"thinking {avg('thought_tokens'):.0f}"
            )
        print("\nRead every medical reply yourself: no dose, no product, no 'it is safe'.")


def main() -> None:
    args = parse_args()
    if args.model:
        os.environ["CHAT_MODEL"] = args.model  # read when app.config is imported

    # Imported here so --model is applied before app.config reads the environment.
    from app import config
    from app.agent import create_agent
    from app.prompts import BUSY_REPLY

    cases = load_cases(args.cases, args.langs, args.kinds, args.limit)
    if not cases:
        raise SystemExit("No cases match those filters.")

    print(f"Indexing {config.KB_PATH.name} with {config.EMBEDDING_MODEL} ...")
    agent = create_agent()
    store, model = RecordingStore(agent.store), RecordingModel(agent.model)
    agent.store, agent.model = store, model
    mode = "retrieval only" if args.retrieval_only else f"full answers with {config.CHAT_MODEL}"
    print(f"Running {len(cases)} case(s), {mode}, MIN_SCORE={config.MIN_SCORE}\n")

    rows = []
    for i, case in enumerate(cases):
        if i:
            time.sleep(args.delay)
        row = run_case(agent, store, model, case, args.retrieval_only, config.TOP_K, BUSY_REPLY)
        row["result"] = check(case, row, args.retrieval_only)
        rows.append(row)
        detail = row["error"] or f"{row['top_section'] or '(no match)'} {row['top_score']}"
        print(f"{row['result']:<6} {row['id']:<6} {detail}")

    summarize(rows, args.retrieval_only)

    RESULTS_DIR.mkdir(exist_ok=True)
    label = "retrieval" if args.retrieval_only else config.CHAT_MODEL
    out = RESULTS_DIR / f"{datetime.now():%Y%m%d-%H%M%S}-{label}.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nAll rows saved to {out.relative_to(EVAL_DIR.parent)}")


if __name__ == "__main__":
    main()
