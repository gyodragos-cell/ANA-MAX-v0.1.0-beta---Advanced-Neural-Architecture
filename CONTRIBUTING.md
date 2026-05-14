# Contributing Guidelines

We love contributions! Please follow these steps before opening a Pull Request:

1. **Fork the repository** and clone your fork locally.
2. **Create a new branch** for your feature or bug‑fix:
   ```bash
   git checkout -b my‑awesome‑feature
   ```
3. **Install the development environment**:
   ```bash
   python -m venv venv
   .\\venv\\Scripts\\activate   # PowerShell
   pip install -r requirements.txt -r dev-requirements.txt
   ```
4. **Run the test suite** to ensure nothing is broken:
   ```bash
   python -m pytest
   ```
5. **Make your changes** adhering to the existing code style (PEP‑8, type hints).
6. **Update documentation** (README, docs, or tool docstrings) if you add new functionality.
7. **Commit with a clear message** and push to your fork:
   ```bash
   git push origin my‑awesome‑feature
   ```
8. **Open a Pull Request** against the `main` branch.  Include:
   - Short description of what the PR does.
   - Reference to any related issue (`Fixes #123`).
   - Screenshots or GIFs if UI changes are involved.

### Code of Conduct
All contributors must follow the [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

### Review Process
Maintainers will review your PR within 3‑5 business days.  If changes are required, they will be requested in the PR comments.
