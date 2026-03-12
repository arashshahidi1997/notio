# Release

## Prerequisites

Install development dependencies:

```bash
pip install -e ".[dev]"
```

## Build

```bash
python -m build
```

## Check

```bash
python -m twine check dist/*
```

## Upload

Test PyPI:

```bash
python -m twine upload --repository testpypi dist/*
```

Production PyPI:

```bash
python -m twine upload dist/*
```

## Make shortcuts

```bash
make build          # build wheel and sdist
make check          # twine check
make publish-test   # upload to TestPyPI
make publish        # upload to PyPI
```
