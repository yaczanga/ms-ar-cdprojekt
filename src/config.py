"""Sciezki i parametry badania.

Jedyne miejsce, w ktorym zapisane sa sciezki i stale. Kod poza tym modulem
nie buduje sciezek z literalow.
"""

from pathlib import Path

# Korzen projektu wyznaczony wzgledem polozenia tego pliku: src/config.py ->
# katalog nadrzedny src/ jest korzeniem. Dziala niezaleznie od katalogu
# roboczego, z ktorego wystartowal notebook albo pytest.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_RAW = PROJECT_ROOT / "data" / "raw"
OUTPUTS = PROJECT_ROOT / "outputs"
FIGURES = OUTPUTS / "figures"
TABLES = OUTPUTS / "tables"

PRICES_CSV = DATA_RAW / "cdr_d.csv"

# Parametry proby
SIMULATION_START = "2023-01-01"
WEEKLY_RULE = "W-FRI"

# Parametry modelu przelacznikowego
N_REGIMES = 2
AR_ORDER = 1
SEARCH_REPS_HISTORY = 10
SEARCH_REPS_WALK_FORWARD = 5
RETURN_SCALE = 100.0

# Estymacja przeszukuje losowe punkty startowe, wiec bez ziarna kolejne
# przebiegi daja nieznacznie rozne oszacowania wariancji rezimow.
RANDOM_SEED = 0

# Parametry strategii
INITIAL_CAPITAL = 10_000.0
COMMISSION = 0.0
SIGNAL_THRESHOLD = 0.5


def ensure_output_dirs() -> None:
    """Tworzy katalogi wynikowe, jesli jeszcze nie istnieja."""
    for path in (FIGURES, TABLES):
        path.mkdir(parents=True, exist_ok=True)
