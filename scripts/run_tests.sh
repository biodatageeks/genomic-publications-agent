#!/bin/bash

# Skrypt do uruchamiania testów dla projektu coordinates-lit

# Sprawdzenie czy wirtualne środowisko jest aktywne
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Wirtualne środowisko nie jest aktywne. Proszę aktywować środowisko."
    exit 1
fi

# Uruchomienie testów z pokryciem kodu
echo "Uruchamianie testów z pokryciem kodu..."
pytest --cov=src --cov-report=term-missing tests/

# Sprawdzenie typów
echo "Sprawdzanie typów..."
mypy src/

# Formatowanie kodu
echo "Formatowanie kodu..."
black src/ tests/
isort src/ tests/

echo "Testy zakończone!" 