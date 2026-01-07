# Contributing to SAP

Thank you for your interest in contributing to the Simplicity Attestation Protocol!

## 🚀 Getting Started

### Prerequisites

1. **Python 3.8+** with `embit` and `requests`:
   ```bash
   pip install embit requests
   ```

2. **Rust toolchain** for compiling tools:
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   ```

3. **simc** (Simfony Compiler):
   ```bash
   git clone https://github.com/BlockstreamResearch/simfony.git
   cd simfony && cargo build --release
   cp target/release/simc ~/.cargo/bin/
   ```

4. **hal-simplicity**:
   ```bash
   git clone https://github.com/brunocapelao/hal-simplicity.git
   cd hal-simplicity && cargo build --release
   cp target/release/hal-simplicity ~/.cargo/bin/
   ```

### Running Tests

```bash
cd tests
python test_emit.py --admin-issue
python test_certificate_revoke.py --admin
python test_edge_cases.py
```

## 📝 How to Contribute

### Reporting Bugs

1. Check if the issue already exists
2. Create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Logs/screenshots if applicable

### Suggesting Features

1. Open an issue with `[Feature]` prefix
2. Describe the use case and expected behavior
3. Explain how it aligns with SAP's goals

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests locally
5. Commit with clear messages: `git commit -m "feat: add X feature"`
6. Push and open a PR

## 🎨 Code Style

### Python

- Follow PEP 8
- Use type hints
- Document functions with docstrings
- Run `ruff check` before committing

### Simfony/Simplicity

- Comment complex jet usage
- Document spending paths clearly
- Keep functions focused and small

### Commits

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `refactor:` Code change that neither fixes a bug nor adds a feature
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

## 📁 Project Structure

```
├── contracts/          # Simfony contracts
│   ├── vault.simf      # Delegation vault (3 spending paths)
│   └── certificate.simf # Certificate UTXO
├── sdk/                # Python SDK
│   ├── sap.py          # Main SAP class
│   ├── client.py       # Legacy SAPClient
│   └── ...
├── tests/              # Test scripts
├── docs/               # Documentation
│   ├── DOCUMENTATION.md
│   ├── PROTOCOL_SPEC.md
│   └── pt/             # Portuguese docs
└── README.md
```

## 🔒 Security

If you discover a security vulnerability, please **do not** open a public issue. Instead, email the maintainers directly.

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Questions? Open an issue or reach out to the maintainers!
