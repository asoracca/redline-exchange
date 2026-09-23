"""Reproduce one failure and resume. No failure switch exists in the HTTP API."""

import json
import tempfile
from research_copilot import experiments
from research_copilot.models import StartRequest
from research_copilot.planner import EXAMPLES
from research_copilot.workflow import Manager


def main():
    with tempfile.TemporaryDirectory() as root:
        manager = Manager(root)
        original = experiments.execute
        calls = 0

        def fail_once(*args):
            nonlocal calls
            calls += 1
            if calls == 4:
                raise RuntimeError("Deliberate fourth-task failure")
            return original(*args)

        try:
            experiments.execute = fail_once
            run = manager.start(StartRequest(question=EXAMPLES[0]), background=False)
            before = {k: run[k] for k in ("state", "completed_tasks", "work", "error")}
            saved = [r["key"] for r in manager.store.tasks(run["id"])]
            experiments.execute = original
            manager.resume(run["id"])
            manager.futures[run["id"]].result(timeout=30)
            after = manager.store.get(run["id"])
            print(
                json.dumps(
                    dict(
                        before=before,
                        retained_tasks=saved,
                        after={
                            k: after[k]
                            for k in ("state", "completed_tasks", "work", "error")
                        },
                        unique_tasks=len(manager.store.tasks(run["id"])),
                        note="The failed attempt remains charged: 6500 work units for a 6000-unit plan.",
                    ),
                    indent=2,
                )
            )
            assert (
                before["completed_tasks"] == 3
                and after["state"] == "completed"
                and after["completed_tasks"] == 12
                and after["work"] == 6500
            )
        finally:
            experiments.execute = original
            manager.close()


if __name__ == "__main__":
    main()
