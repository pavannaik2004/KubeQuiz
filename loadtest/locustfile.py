"""Simulated exam takers for KubeQuiz.

Each virtual user picks a name, then keeps taking random quizzes: open the
quiz, "think", submit random answers, look at the result and sometimes the
leaderboard. This is the load that drives the HorizontalPodAutoscaler.

Local:      locust -f loadtest/locustfile.py --host http://localhost:8080
Headless:   locust -f loadtest/locustfile.py --host ... --headless -u 200 -r 20 -t 5m
"""
import random
import re
import uuid

from locust import HttpUser, between, task

QUESTION_RE = re.compile(r'name="q(\d+)" value="(\d+)"')


class QuizTaker(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.client.post(
            "/login",
            data={"username": f"bot-{uuid.uuid4().hex[:8]}"},
            name="/login",
        )
        self.quiz_ids = self._load_quiz_ids()

    def _load_quiz_ids(self):
        with self.client.get("/api/quizzes", name="/api/quizzes", catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"status {r.status_code}")
                return []
            return [q["id"] for q in r.json() if q["question_count"] > 0]

    @task(1)
    def browse_home(self):
        self.client.get("/", name="/")

    @task(4)
    def take_quiz(self):
        if not self.quiz_ids:
            self.quiz_ids = self._load_quiz_ids()
            if not self.quiz_ids:
                return
        quiz_id = random.choice(self.quiz_ids)

        # A Kubernetes Service balances per TCP *connection*. With keep-alive,
        # every simulated student stays pinned to the pod it first reached, so
        # pods added by the HPA would get no traffic (measured in the first
        # live demo: 6 replicas, only 3 served requests). Drop the pooled
        # connection at the start of each attempt, like a browser that went
        # idle; the session cookie (login) is kept.
        self.client.close()

        page = self.client.get(f"/quiz/{quiz_id}", name="/quiz/[id]")
        if page.status_code != 200:
            return

        # Collect the radio options per question and answer randomly.
        options = {}
        for qid, idx in QUESTION_RE.findall(page.text):
            options.setdefault(qid, []).append(idx)
        answers = {f"q{qid}": random.choice(idxs) for qid, idxs in options.items()}

        # Following the redirect also loads /result/<id>.
        self.client.post(f"/quiz/{quiz_id}/submit", data=answers, name="/quiz/[id]/submit")

        if random.random() < 0.3:
            self.client.get(f"/leaderboard/{quiz_id}", name="/leaderboard/[id]")

    @task(1)
    def which_pod(self):
        self.client.get("/api/info", name="/api/info")
