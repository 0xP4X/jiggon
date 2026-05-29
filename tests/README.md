# Jiggon Test Suite

> [!WARNING]
> The automated test suite is currently under reconstruction for the `v0.1.x` (PyPI-distributed) architecture.

The previous tests were built against an older internal architecture and have been temporarily removed to prevent CI failures. 

We welcome open-source contributions! If you would like to help rebuild the test suite for the new `src/jiggon/` layout, please feel free to submit a Pull Request.

## Running Tests
Once tests are restored, you can run them via:
```powershell
pip install -e .[dev]
pytest
```
