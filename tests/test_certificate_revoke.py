#!/usr/bin/env python3
"""
SAP - Certificate Revocation (E2E)

No keys are committed. Provide keys via env vars.

Env vars:
- SAP_ADMIN_PRIVATE_KEY / SAP_DELEGATE_PRIVATE_KEY
- SAP_NETWORK (default: testnet)
- SAP_VAULT_CONFIG (default: vault_config.json)
- SAP_HAL_PATH (default: ./hal-simplicity/target/release/hal-simplicity)
"""

from __future__ import annotations

import argparse
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
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--admin", action="store_true")
    group.add_argument("--delegate", action="store_true")
    parser.add_argument("--txid", help="Certificate txid to revoke")
    parser.add_argument("--vout", type=int, default=1)
    parser.add_argument("--reason-code", type=int, default=None)
    parser.add_argument("--replacement-txid", default=None)
    parser.add_argument("--recipient", default=None)
    args = parser.parse_args()

    config_path = Path(_env("SAP_VAULT_CONFIG", "vault_config.json"))
    if not config_path.exists():
        print(f"Missing config: {config_path} (create it via tests/test_emit.py first)", file=sys.stderr)
        return 2

    hal_path = _env("SAP_HAL_PATH", "./hal-simplicity/target/release/hal-simplicity")
    if args.admin:
        private_key = _env("SAP_ADMIN_PRIVATE_KEY")
        role_label = "admin"
        sap = SAP.as_admin(str(config_path), private_key=private_key or "", hal_path=hal_path)
    else:
        private_key = _env("SAP_DELEGATE_PRIVATE_KEY")
        role_label = "delegate"
        sap = SAP.as_delegate(str(config_path), private_key=private_key or "", hal_path=hal_path)

    if not private_key:
        print(f"Missing key: set SAP_{role_label.upper()}_PRIVATE_KEY", file=sys.stderr)
        return 2

    txid = args.txid
    vout = args.vout
    if not txid:
        certs = sap.list_certificates()
        if not certs:
            print("No active certificates found. Issue one first.", file=sys.stderr)
            return 1
        txid = certs[0].txid
        vout = certs[0].vout
        print(f"Auto-selected certificate: {txid}:{vout}")

    result = sap.revoke_certificate(
        txid,
        vout=vout,
        recipient=args.recipient,
        reason_code=args.reason_code,
        replacement_txid=args.replacement_txid,
    )
    print(result)
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
