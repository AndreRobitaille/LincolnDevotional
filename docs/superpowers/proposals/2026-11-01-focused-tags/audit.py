"""Validate the archived proposal with the production topic policy."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from tools.audit_topics import main

if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    main(["--taxonomy", str(here / "topic_taxonomy.json"),
          "--assignments", str(here / "entry_topics.json"), *sys.argv[1:]])
