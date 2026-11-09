"""Pure scoring logic, kept separate from Flask so it is easy to unit test."""


def score_answers(questions, answers):
    """Return (score, total, per-question results).

    questions: list of dicts with "id", "options" and "correct_index"
    answers:   mapping of question id (int) -> chosen option index (int or None)
    """
    results = []
    score = 0
    for q in questions:
        chosen = answers.get(q["id"])
        correct = chosen is not None and chosen == q["correct_index"]
        if correct:
            score += 1
        results.append(
            {
                "id": q["id"],
                "text": q["text"],
                "options": q["options"],
                "chosen": chosen,
                "correct_index": q["correct_index"],
                "correct": correct,
            }
        )
    return score, len(questions), results


def parse_answers(form, questions):
    """Read q<id> fields from a submitted form; ignore invalid values."""
    answers = {}
    for q in questions:
        raw = form.get(f"q{q['id']}")
        try:
            idx = int(raw)
        except (TypeError, ValueError):
            idx = None
        if idx is not None and not 0 <= idx < len(q["options"]):
            idx = None
        answers[q["id"]] = idx
    return answers
