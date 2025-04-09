#!/bin/bash

# Skrypt instalacyjny dla projektu coordinates-lit

# Sprawdzenie czy Python jest zainstalowany
if ! command -v python3 &> /dev/null; then
    echo "Python 3 nie jest zainstalowany. Proszę zainstalować Python 3."
    exit 1
fi

# Sprawdzenie czy pip jest zainstalowany
if ! command -v pip3 &> /dev/null; then
    echo "pip nie jest zainstalowany. Proszę zainstalować pip."
    exit 1
fi

# Tworzenie wirtualnego środowiska
echo "Tworzenie wirtualnego środowiska..."
python3 -m venv venv

# Aktywacja wirtualnego środowiska
echo "Aktywacja wirtualnego środowiska..."
source venv/bin/activate

# Instalacja zależności
echo "Instalacja zależności..."
pip install -e .

# Instalacja zależności deweloperskich
echo "Instalacja zależności deweloperskich..."
pip install -e ".[dev]"

# Tworzenie katalogów danych
echo "Tworzenie katalogów danych..."
mkdir -p data/{raw,processed,cache}

# Tworzenie plików konfiguracyjnych
echo "Tworzenie plików konfiguracyjnych..."
cp config/development.yaml config/local.yaml

echo "Instalacja zakończona pomyślnie!"
echo "Aby aktywować środowisko, użyj: source venv/bin/activate" 