"""
SAS SDK - Hal-Simplicity CLI Wrapper

Provides a clean Python interface to the hal-simplicity command-line tool.
"""

import subprocess
import json
import shutil
from typing import Optional, List, Tuple
from pathlib import Path

from ..models import RunResult


class HalSimplicityError(Exception):
    """Error from hal-simplicity CLI."""
    pass


class HalSimplicity:
    """
    Wrapper for hal-simplicity CLI tool.
    
    Handles all interactions with the Simplicity toolchain for PSET
    creation, signing, and transaction extraction.
    """
    
    DEFAULT_BINARY = "hal-simplicity"
    
    def __init__(self, binary_path: Optional[str] = None, network: str = "liquid"):
        """
        Initialize HalSimplicity wrapper.
        
        Args:
            binary_path: Path to hal-simplicity binary. Auto-detected if None.
            network: Network flag for PSET operations ("liquid" or "bitcoin").
        """
        self.binary = binary_path or self._find_binary()
        self.network = network
        self._validate_binary()
    
    def _find_binary(self) -> str:
        """Find hal-simplicity binary in common locations."""
        locations = [
            self.DEFAULT_BINARY,
            shutil.which("hal-simplicity"),
            Path.home() / ".cargo/bin/hal-simplicity",
        ]
        
        for loc in locations:
            if loc and Path(loc).exists():
                return str(loc)
        
        return self.DEFAULT_BINARY
    
    def _validate_binary(self) -> None:
        """Validate that the binary exists and is executable."""
        if not Path(self.binary).exists():
            raise HalSimplicityError(
                f"hal-simplicity binary not found at: {self.binary}\n"
                f"Please install from: https://github.com/brunocapelao/hal-simplicity"
            )
    
    def _run(self, args: List[str]) -> Tuple[str, Optional[str]]:
        """
        Run hal-simplicity command.

        Returns:
            Tuple of (stdout, stderr). stderr is None on success.
        """
        cmd = [self.binary] + args
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return "", result.stderr

        return result.stdout.strip(), None
    
    def _run_json(self, args: List[str]) -> dict:
        """Run command and parse JSON output."""
        output, err = self._run(args)
        if err:
            raise HalSimplicityError(f"Command failed: {err}")

        try:
            data = json.loads(output)
            if isinstance(data, dict) and data.get("error"):
                raise HalSimplicityError(f"hal-simplicity error: {data['error']}")
            return data
        except json.JSONDecodeError as e:
            raise HalSimplicityError(f"Invalid JSON output: {e}\nOutput: {output}")
    
    # =========================================================================
    # PSET Operations
    # =========================================================================
    
    def pset_create(self, inputs: List[dict], outputs: List[dict]) -> str:
        """
        Create a new PSET (Partially Signed Elements Transaction).
        
        Args:
            inputs: List of {"txid": str, "vout": int}
            outputs: List of {"address": str, "asset": str, "amount": float}
        
        Returns:
            Base64-encoded PSET string.
        """
        inputs_json = json.dumps(inputs)
        outputs_json = json.dumps(outputs)
        
        result = self._run_json([
            "simplicity", "pset", "create",
            f"--{self.network}",
            inputs_json,
            outputs_json
        ])
        
        return result["pset"]
    
    def pset_update_input(
        self,
        pset: str,
        index: int,
        script_pubkey: str,
        asset: str,
        amount: str,
        cmr: str,
        internal_key: str
    ) -> str:
        """
        Update a PSET input with UTXO information.
        
        Args:
            pset: Base64-encoded PSET.
            index: Input index to update.
            script_pubkey: Script pubkey of the UTXO.
            asset: Asset ID.
            amount: Amount in BTC format (e.g., "0.00001000").
            cmr: Commitment Merkle Root of the Simplicity program.
            internal_key: Taproot internal key.
        
        Returns:
            Updated Base64-encoded PSET.
        """
        input_utxo = f"{script_pubkey}:{asset}:{amount}"
        
        result = self._run_json([
            "simplicity", "pset", "update-input",
            f"--{self.network}",
            pset,
            str(index),
            "--input-utxo", input_utxo,
            "--cmr", cmr,
            "--internal-key", internal_key
        ])
        
        return result["pset"]
    
    def pset_run(
        self,
        pset: str,
        index: int,
        program: str,
        witness: str
    ) -> RunResult:
        """
        Run a Simplicity program with witness and get jet outputs.
        
        This is used to get the sig_all_hash for signing.
        
        Args:
            pset: Base64-encoded PSET.
            index: Input index.
            program: Base64-encoded Simplicity program.
            witness: Hex-encoded witness data.
        
        Returns:
            RunResult with jet outputs including sig_all_hash.
        """
        result = self._run_json([
            "simplicity", "pset", "run",
            f"--{self.network}",
            pset,
            str(index),
            program,
            witness
        ])
        
        return RunResult.from_dict(result)
    
    def pset_finalize(
        self,
        pset: str,
        index: int,
        program: str,
        witness: str
    ) -> str:
        """
        Finalize a PSET input with program and witness.
        
        Args:
            pset: Base64-encoded PSET.
            index: Input index.
            program: Base64-encoded Simplicity program.
            witness: Hex-encoded witness data.
        
        Returns:
            Finalized Base64-encoded PSET.
        """
        result = self._run_json([
            "simplicity", "pset", "finalize",
            f"--{self.network}",
            pset,
            str(index),
            program,
            witness
        ])
        
        return result["pset"]
    
    def pset_extract(self, pset: str) -> str:
        """
        Extract raw transaction hex from finalized PSET.
        
        Args:
            pset: Finalized Base64-encoded PSET.
        
        Returns:
            Raw transaction hex string.
        """
        output, err = self._run([
            "simplicity", "pset", "extract",
            f"--{self.network}",
            pset
        ])
        
        if err:
            raise HalSimplicityError(f"PSET extract failed: {err}")
        
        # Remove quotes if present
        return output.strip('"')
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def verify_program(
        self,
        pset: str,
        index: int,
        program: str,
        witness: str
    ) -> bool:
        """
        Verify that a program+witness combination is valid.
        
        Returns:
            True if verification succeeds, False otherwise.
        """
        try:
            result = self.pset_run(pset, index, program, witness)
            return result.success
        except HalSimplicityError:
            return False
