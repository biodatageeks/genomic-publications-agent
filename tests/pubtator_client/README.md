# PubTator Client Tests

This directory contains tests for the PubTator client module. The tests are organized into unit tests and integration tests.

## Running Tests

You can run the tests in different ways:

1. Run only unit tests (using mocks):
```bash
pytest -v -m "not integration"
```

2. Run only integration tests (using real API):
```bash
pytest -v -m "integration"
```

3. Run all tests:
```bash
pytest -v
```

## Test Structure

- Unit tests are located in `test_pubtator_client.py`
- Integration tests are marked with the `@pytest.mark.integration` decorator
- Mock data is provided in fixtures for unit testing
- Real API calls are made during integration tests

## Requirements

Make sure you have the following packages installed:
- pytest
- requests
- bioc 