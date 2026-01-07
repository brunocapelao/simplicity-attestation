# SAP SDK (Python)

Python SDK for the Simplicity Attestation Protocol on Liquid.

## Documentation

- English: `docs/DOCUMENTATION.md`
- Portuguese: `docs/pt/SDK.md`

## Quick Start

```python
from sdk import SAPClient

client = SAPClient.from_config("secrets.json")
issue = client.issue_certificate(cid="Qm...")
status = client.verify_certificate(issue.txid, 1)
revoke = client.revoke_certificate(issue.txid, 1)
```

## Tools

The SDK requires `simc` and `hal-simplicity` in your PATH. See `docs/DOCUMENTATION.md` for setup.
