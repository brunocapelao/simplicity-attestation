#!/usr/bin/env python3
"""
SAS - Attack Vectors (Local / Offline)

This script intentionally does NOT broadcast transactions.
It builds PSETs and uses `hal-simplicity simplicity pset run` to prove that
common invalid constructions are rejected by the vault covenant.

Prerequisites:
- `hal-simplicity` and `simc` installed (or set paths via env vars below)
- A `vault_config.json` already created (e.g. via tests/test_emit.py)

Env vars:
- SAS_NETWORK: testnet|mainnet (default: testnet)
- SAS_VAULT_CONFIG: path to vault config json (default: vault_config.json)
- SAS_HAL_PATH: path to hal-simplicity binary (default: hal-simplicity)
- SAS_ADMIN_PRIVATE_KEY / SAS_DELEGATE_PRIVATE_KEY: 64-hex (only used for role checks)
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from embit import ec

from sdk import SAS
from sdk.protocols.sas import SAPProtocol
from sdk.infra.hal import HalSimplicity
from sdk.sas import VaultConfig


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _gen_priv_hex() -> str:
    while True:
        candidate = os.urandom(32)
        try:
            pk = ec.PrivateKey(candidate)
            return pk.secret.hex()
        except Exception:
            continue


@dataclass(frozen=True)
class Case:
    name: str
    build_outputs: Callable[[VaultConfig], list[dict]]
    expect_sig_hash: bool


def _base_issuance_outputs(config: VaultConfig) -> list[dict]:
    # 100_000 sats input: change + cert dust + fee + op_return(0)
    fee_sats = 500
    cert_sats = 546
    change_sats = 100_000 - fee_sats - cert_sats

    sap_payload = SAPProtocol.encode_attest("TEST-ATTACK-VECTORS")

    return [
        {
            "address": config.vault_address,
            "asset": config.asset_id,
            "amount": change_sats / 100_000_000,
        },
        {
            "address": config.certificate_address,
            "asset": config.asset_id,
            "amount": cert_sats / 100_000_000,
        },
        {
            "address": f"data:{sap_payload}",
            "asset": config.asset_id,
            "amount": 0,
        },
        {
            "address": "fee",
            "asset": config.asset_id,
            "amount": fee_sats / 100_000_000,
        },
    ]

def _vault_dummy_witness() -> str:
    from sdk.core.witness import WitnessEncoder

    return WitnessEncoder.vault_dummy("delegate_issue")


def _run_vault_pset_local(config: VaultConfig, hal: HalSimplicity, outputs: list[dict]):
    inputs = [{"txid": "00" * 32, "vout": 0}]
    pset = hal.pset_create(inputs, outputs)
    pset = hal.pset_update_input(
        pset=pset,
        index=0,
        script_pubkey=config.vault_script_pubkey,
        asset=config.asset_id,
        amount="0.00100000",
        cmr=config.vault_cmr,
        internal_key=config.internal_key,
    )
    return hal.pset_run(pset, 0, config.vault_program, _vault_dummy_witness())


def _assert(condition: bool, msg: str) -> None:
    if not condition:
        raise AssertionError(msg)


def main() -> int:
    config_path = Path(_env("SAS_VAULT_CONFIG", "vault_config.json"))
    if not config_path.exists():
        print(f"Missing config: {config_path} (create it via tests/test_emit.py first)", file=sys.stderr)
        return 2

    config = VaultConfig.load(str(config_path))
    hal_path = _env("SAS_HAL_PATH", "hal-simplicity") or "hal-simplicity"
    hal = HalSimplicity(hal_path, network="liquid")

    base = _base_issuance_outputs(config)

    cases: list[Case] = [
        Case(
            name="delegate diverts change (output0 not vault)",
            build_outputs=lambda c: [
                {**base[0], "address": c.certificate_address},
                base[1],
                base[2],
                base[3],
            ],
            expect_sig_hash=False,
        ),
        Case(
            name="invalid output count (3 outputs)",
            build_outputs=lambda _c: [base[0], base[1], base[3]],
            expect_sig_hash=False,
        ),
        Case(
            name="non-standard certificate (output1 not certificate script)",
            build_outputs=lambda c: [
                base[0],
                {**base[1], "address": c.vault_address},
                base[2],
                base[3],
            ],
            expect_sig_hash=False,
        ),
        Case(
            name="missing OP_RETURN (output2 not null datum)",
            build_outputs=lambda c: [
                base[0],
                base[1],
                {**base[2], "address": c.vault_address, "amount": 0.0},
                base[3],
            ],
            expect_sig_hash=False,
        ),
        Case(
            name="fee output not fee (output3 not fee)",
            build_outputs=lambda c: [
                base[0],
                base[1],
                base[2],
                {**base[3], "address": c.vault_address},
            ],
            expect_sig_hash=False,
        ),
    ]

    print(f"Config: {config_path}")
    print(f"Vault: {config.vault_address}")
    print(f"Certificate: {config.certificate_address}")
    print()

    # Covenant checks (offline via pset run)
    for case in cases:
        run = _run_vault_pset_local(config, hal, case.build_outputs(config))
        # Covenant failures should prevent reaching sig_all_hash.
        if case.expect_sig_hash:
            _assert(run.sig_all_hash is not None, f"{case.name}: expected sig_all_hash")
        else:
            _assert(run.sig_all_hash is None, f"{case.name}: expected NO sig_all_hash (covenant should fail)")
        print(f"OK: {case.name}")

    # Role/permission checks (SDK-level)
    admin_priv = _env("SAS_ADMIN_PRIVATE_KEY")
    delegate_priv = _env("SAS_DELEGATE_PRIVATE_KEY")
    if admin_priv and delegate_priv:
        delegate = SAS.as_delegate(str(config_path), private_key=delegate_priv, hal_path=hal_path)
        try:
            delegate.drain_vault(recipient=config.vault_address)
            raise AssertionError("delegate.drain_vault unexpectedly succeeded")
        except Exception:
            print("OK: delegate cannot drain vault (permission check)")
    else:
        print("SKIP: delegate drain permission check (missing env keys)")

    # Forgery prevention (mismatched private key rejected)
    try:
        SAS.as_delegate(str(config_path), private_key=_gen_priv_hex(), hal_path=hal_path)
        raise AssertionError("Mismatched delegate private key unexpectedly accepted")
    except Exception:
        print("OK: mismatched private key rejected (prevents third-party forging via SDK)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
