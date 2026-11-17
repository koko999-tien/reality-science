"""Extend only the bounded browser-fixture time budget; reuse verified lifecycle."""
import functools
import os
import sys
from pathlib import Path

from run_live import queue

E = Path(__file__).resolve().parent
os.environ["REALITY_OPENBOT_BROWSER"] = "1"
os.environ["REALITY_OPENBOT_EVIDENCE"] = str(E)
os.environ["REALITY_DRAFT_MANIFEST"] = str(E / "instance.json")
queue.run = functools.partial(queue.run, timeout=2160)
sys.argv = [sys.argv[0], "live-openbot-01", "tests/integration/test_draft_openbot_live.py"]
raise SystemExit(queue.main())
