import json
import importlib.util
import sys
from typing import List
from app.config import APP_DIR, PRIVATE_DIR

# -------------------------
# Migration runner
# -------------------------
MIGRATIONS_DIR = APP_DIR / "migrations"
MIGRATIONS_APPLIED_FILE = PRIVATE_DIR / "migrations_applied.json"
PRIVATE_DIR.mkdir(parents=True, exist_ok=True)

def _load_applied_migrations() -> List[str]:
    if MIGRATIONS_APPLIED_FILE.exists():
        try:
            with open(MIGRATIONS_APPLIED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []

def _save_applied_migrations(names: List[str]) -> None:
    with open(MIGRATIONS_APPLIED_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(names), f)

def main() -> None:
    if not MIGRATIONS_DIR.exists():
        return
    applied = set(_load_applied_migrations())
    files = sorted(MIGRATIONS_DIR.glob("*.py"))
    for path in files:
        name = path.stem
        if name in applied:
            continue
        try:
            spec = importlib.util.spec_from_file_location(f"migrations.{name}", path)
            module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
            assert spec and spec.loader
            spec.loader.exec_module(module)  # type: ignore[union-attr]
            if hasattr(module, "run"):
                module.run()
            applied.add(name)
        except Exception as e:
            # Don't hard-fail, just report
            print(f"> Migration '{name}' failed: {e}", file=sys.stderr)
    _save_applied_migrations(list(applied))