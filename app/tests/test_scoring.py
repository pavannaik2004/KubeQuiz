from kubequiz.scoring import parse_answers, score_answers

QUESTIONS = [
    {"id": 1, "text": "a", "options": ["x", "y"], "correct_index": 0},
    {"id": 2, "text": "b", "options": ["x", "y", "z"], "correct_index": 2},
    {"id": 3, "text": "c", "options": ["x", "y"], "correct_index": 1},
]


def test_all_correct():
    score, total, _ = score_answers(QUESTIONS, {1: 0, 2: 2, 3: 1})
    assert (score, total) == (3, 3)


def test_unanswered_and_wrong():
    score, total, results = score_answers(QUESTIONS, {1: 1, 2: None})
    assert (score, total) == (0, 3)
    assert [r["correct"] for r in results] == [False, False, False]
    assert results[2]["chosen"] is None


def test_parse_answers_rejects_out_of_range_and_garbage():
    form = {"q1": "0", "q2": "7", "q3": "abc"}
    assert parse_answers(form, QUESTIONS) == {1: 0, 2: None, 3: None}
