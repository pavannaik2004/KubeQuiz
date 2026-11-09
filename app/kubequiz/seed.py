"""Create the schema and load sample quizzes if the database is empty.

Kubernetes runs this once as the db-init Job:  python -m kubequiz.seed
"""
import json
import logging
import os
import sys

from . import db

log = logging.getLogger("kubequiz.seed")

SAMPLE_QUIZZES = [
    {
        "title": "Kubernetes Basics",
        "description": "Pods, Deployments, Services and scaling.",
        "time_limit_seconds": 300,
        "questions": [
            ("What is the smallest deployable unit in Kubernetes?",
             ["Container", "Pod", "Node", "ReplicaSet"], 1),
            ("Which object keeps a desired number of identical Pods running?",
             ["Service", "ConfigMap", "Deployment", "Namespace"], 2),
            ("Which Service type exposes a port on every node's IP?",
             ["ClusterIP", "NodePort", "ExternalName", "Headless"], 1),
            ("What does the HorizontalPodAutoscaler change?",
             ["CPU limits of a Pod", "Number of nodes", "Number of Pod replicas",
              "Container image tag"], 2),
            ("Which component provides the CPU metrics the HPA reads?",
             ["kube-proxy", "metrics-server", "etcd", "CoreDNS"], 1),
            ("A failing readiness probe causes Kubernetes to...",
             ["Restart the container", "Delete the Deployment",
              "Stop sending Service traffic to the Pod", "Evict the node"], 2),
            ("Where is the cluster state stored?",
             ["etcd", "kubelet", "The container registry", "A ConfigMap"], 0),
        ],
    },
    {
        "title": "Docker Fundamentals",
        "description": "Images, containers and Dockerfiles.",
        "time_limit_seconds": 240,
        "questions": [
            ("Which Dockerfile instruction sets the default command?",
             ["RUN", "CMD", "FROM", "COPY"], 1),
            ("Each RUN instruction in a Dockerfile creates a new...",
             ["Container", "Volume", "Image layer", "Network"], 2),
            ("Why put `COPY requirements.txt` before `COPY . .`?",
             ["Smaller image", "Better layer caching", "Required by pip",
              "It runs faster at runtime"], 1),
            ("Which command lists running containers?",
             ["docker images", "docker ps", "docker logs", "docker inspect"], 1),
            ("What does a multi-stage build mainly reduce?",
             ["Build time only", "Final image size", "Number of containers",
              "Network usage at runtime"], 1),
        ],
    },
    {
        "title": "DevOps & Ansible",
        "description": "Automation, idempotency and CI/CD.",
        "time_limit_seconds": 240,
        "questions": [
            ("Ansible connects to managed Linux hosts using...",
             ["An agent daemon", "SSH", "SNMP", "RDP"], 1),
            ("An idempotent playbook run a second time should...",
             ["Fail", "Change nothing if the state already matches",
              "Reinstall everything", "Delete the inventory"], 1),
            ("Which file lists the hosts Ansible manages?",
             ["playbook.yml", "ansible.cfg", "Inventory", "requirements.yml"], 2),
            ("Reusable, structured bundles of Ansible tasks are called...",
             ["Roles", "Modules", "Facts", "Handlers"], 0),
            ("CI stands for...",
             ["Container Integration", "Continuous Integration",
              "Cluster Inspection", "Code Isolation"], 1),
            ("Which Ansible feature runs a task only when notified of a change?",
             ["Tags", "Handlers", "Loops", "Vault"], 1),
        ],
    },
]


def seed_if_empty(conn):
    count = conn.execute("SELECT COUNT(*) FROM quizzes").fetchone()[0]
    if count:
        log.info("database already has %d quizzes, skipping seed", count)
        return False
    # BEGIN IMMEDIATE takes the write lock up front, so two seeders started at
    # the same moment cannot both insert the sample data.
    conn.execute("BEGIN IMMEDIATE")
    try:
        if conn.execute("SELECT COUNT(*) FROM quizzes").fetchone()[0]:
            conn.rollback()
            return False
        for quiz in SAMPLE_QUIZZES:
            cur = conn.execute(
                "INSERT INTO quizzes (title, description, time_limit_seconds) VALUES (?, ?, ?)",
                (quiz["title"], quiz["description"], quiz["time_limit_seconds"]),
            )
            for text, options, correct in quiz["questions"]:
                conn.execute(
                    "INSERT INTO questions (quiz_id, text, options, correct_index) "
                    "VALUES (?, ?, ?, ?)",
                    (cur.lastrowid, text, json.dumps(options), correct),
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    log.info("seeded %d sample quizzes", len(SAMPLE_QUIZZES))
    return True


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    path = os.environ.get("DB_PATH", "instance/quiz.db")
    log.info("initialising database at %s", path)
    conn = db.connect(path)
    conn.isolation_level = None  # manage transactions explicitly (BEGIN IMMEDIATE)
    db.init_schema(conn)
    seed_if_empty(conn)
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
