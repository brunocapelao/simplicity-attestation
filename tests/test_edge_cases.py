#!/usr/bin/env python3
"""
SAP - Basic Safety Checks (Local)

This script is a lightweight sanity check that avoids embedding any secrets
or hardcoded deployment keys.

It verifies:
- Delegate cannot call admin-only operations (drain_vault)

Env vars:
- SAP_ADMIN_PRIVATE_KEY / SAP_DELEGATE_PRIVATE_KEY
- SAP_VAULT_CONFIG (default: vault_config.json)
- SAP_HAL_PATH (default: ./hal-simplicity/target/release/hal-simplicity)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sdk import SAP


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def main() -> int:
    config_path = Path(_env("SAP_VAULT_CONFIG", "vault_config.json"))
    if not config_path.exists():
        print(f"Missing config: {config_path} (create it via tests/test_emit.py first)", file=sys.stderr)
        return 2

    hal_path = _env("SAP_HAL_PATH", "./hal-simplicity/target/release/hal-simplicity")
    admin_private_key = _env("SAP_ADMIN_PRIVATE_KEY")
    delegate_private_key = _env("SAP_DELEGATE_PRIVATE_KEY")
    if not admin_private_key or not delegate_private_key:
        print("Missing keys. Set SAP_ADMIN_PRIVATE_KEY and SAP_DELEGATE_PRIVATE_KEY.", file=sys.stderr)
        return 2

    admin = SAP.as_admin(str(config_path), private_key=admin_private_key, hal_path=hal_path)
    delegate = SAP.as_delegate(str(config_path), private_key=delegate_private_key, hal_path=hal_path)

    print("Admin info:", admin.info())
    print("Delegate info:", delegate.info())

    try:
        delegate.drain_vault(recipient="tex1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqd3h7hu")
        print("ERROR: delegate.drain_vault unexpectedly succeeded", file=sys.stderr)
        return 1
    except Exception as e:
        print("OK: delegate cannot drain vault:", e)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
