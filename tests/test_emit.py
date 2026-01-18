#!/usr/bin/env python3
"""
SAS - Emission / Drain (E2E)

This script is intentionally "local-only" friendly:
- No private keys are committed to the repo.
- You provide keys via environment variables.

Prerequisites:
- `hal-simplicity` and `simc` installed (or set paths via env vars below)
- Fund the generated vault address on Liquid Testnet before issuing

Env vars:
- SAS_ADMIN_PRIVATE_KEY: 64-hex private key (admin)
- SAS_DELEGATE_PRIVATE_KEY: 64-hex private key (delegate)
- SAS_NETWORK: testnet|mainnet (default: testnet)
- SAS_VAULT_CONFIG: path to vault config json (default: vault_config.json)
- SAS_HAL_PATH: path to hal-simplicity binary (default: ./hal-simplicity/target/release/hal-simplicity)
- SAS_SIMC_PATH: path to simc binary (default: ./simfony/target/release/simc)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from embit import ec

from sdk import SAS
from sdk.sas import VaultConfig


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _xonly_pubkey_from_private_key(private_key_hex: str) -> str:
    private_key = ec.PrivateKey(bytes.fromhex(private_key_hex))
    return private_key.get_public_key().xonly().hex()


def _load_or_create_config(
    config_path: Path,
    admin_private_key: str,
    delegate_private_key: str,
    network: str,
    hal_path: str,
    simc_path: str,
) -> VaultConfig:
    if config_path.exists():
        return VaultConfig.load(str(config_path))

    admin_pubkey = _xonly_pubkey_from_private_key(admin_private_key)
    delegate_pubkey = _xonly_pubkey_from_private_key(delegate_private_key)

    config = SAS.create_vault(
        admin_pubkey=admin_pubkey,
        delegate_pubkey=delegate_pubkey,
        network=network,
        hal_path=hal_path,
        simc_path=simc_path,
    )
    config.save(str(config_path))
    return config


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--admin-unconditional", action="store_true", help="Drain vault (admin only)")
    group.add_argument("--admin-issue", action="store_true", help="Issue certificate as admin")
    group.add_argument("--delegate-issue", action="store_true", help="Issue certificate as delegate")
    parser.add_argument("--cid", default="QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG")
    parser.add_argument("--recipient", help="Recipient address for drain")
    args = parser.parse_args()

    network = _env("SAS_NETWORK", "testnet")
    config_path = Path(_env("SAS_VAULT_CONFIG", "vault_config.json"))
    hal_path = _env("SAS_HAL_PATH", "./hal-simplicity/target/release/hal-simplicity")
    simc_path = _env("SAS_SIMC_PATH", "./simfony/target/release/simc")

    admin_private_key = _env("SAS_ADMIN_PRIVATE_KEY")
    delegate_private_key = _env("SAS_DELEGATE_PRIVATE_KEY")
    if not admin_private_key or not delegate_private_key:
        print(
            "Missing keys. Set SAS_ADMIN_PRIVATE_KEY and SAS_DELEGATE_PRIVATE_KEY (64-hex).",
            file=sys.stderr,
        )
        return 2

    config = _load_or_create_config(
        config_path=config_path,
        admin_private_key=admin_private_key,
        delegate_private_key=delegate_private_key,
        network=network,
        hal_path=hal_path,
        simc_path=simc_path,
    )

    print(f"Vault config: {config_path}")
    print(f"Vault address: {config.vault_address}")
    print(f"Certificate address: {config.certificate_address}")
    print()

    if args.admin_unconditional:
        if not args.recipient:
            print("--recipient is required for --admin-unconditional", file=sys.stderr)
            return 2
        admin = SAS.as_admin(str(config_path), private_key=admin_private_key, hal_path=hal_path)
        result = admin.drain_vault(recipient=args.recipient)
        print(result)
        return 0 if result.success else 1

    if args.admin_issue:
        admin = SAS.as_admin(str(config_path), private_key=admin_private_key, hal_path=hal_path)
        result = admin.issue_certificate(cid=args.cid)
        print(result)
        return 0 if result.success else 1

    delegate = SAS.as_delegate(str(config_path), private_key=delegate_private_key, hal_path=hal_path)
    result = delegate.issue_certificate(cid=args.cid)
    print(result)
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
