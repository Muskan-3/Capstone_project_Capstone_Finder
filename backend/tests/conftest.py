"""Test bootstrap.

Point the app at a throwaway DB + artifacts dir *before* anything imports
``app.config``, so no module reloading is needed.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_TMP = Path(tempfile.mkdtemp(prefix="compass-tests-"))
import os  # noqa: E402

os.environ.setdefault("COMPASS_DATABASE_URL", f"sqlite:///{_TMP/'test.db'}")
os.environ.setdefault("COMPASS_ARTIFACTS_DIR", str(_TMP / "artifacts"))
os.environ.setdefault("COMPASS_AUTO_SEED", "true")
