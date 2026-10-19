"""Sciezki i parametry badania - jedyne zrodlo stalych, nie powtarzane w kodzie."""

from pathlib import Path

# Korzen liczony od polozenia tego pliku, nie od katalogu roboczego.
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

# Bez ziarna kolejne przebiegi daja rozne oszacowania wariancji rezimow.
RANDOM_SEED = 0

# Parametry strategii
INITIAL_CAPITAL = 10_000.0
COMMISSION = 0.0
SIGNAL_THRESHOLD = 0.5


def ensure_output_dirs() -> None:
    """Tworzy katalogi wynikowe, jesli jeszcze nie istnieja."""
    for path in (FIGURES, TABLES):
        path.mkdir(parents=True, exist_ok=True)
