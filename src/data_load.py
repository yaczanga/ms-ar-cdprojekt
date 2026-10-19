"""Wczytanie notowan, agregacja tygodniowa i kontrola stacjonarnosci."""

from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

from . import config

REQUIRED_COLUMNS = ("Data", "Otwarcie", "Najwyzszy", "Najnizszy", "Zamkniecie")


def load_daily_prices(path=None) -> pd.DataFrame:
    """Wczytuje dzienne notowania i zwraca ramke indeksowana data rosnaco."""
    path = config.PRICES_CSV if path is None else path
    frame = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError(f"Brak kolumn w {path}: {missing}")
    frame["Data"] = pd.to_datetime(frame["Data"])
    return frame.set_index("Data").sort_index()


def to_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    """Agreguje notowania dzienne do tygodni konczacych sie w piatek."""
    return (
        daily.resample(config.WEEKLY_RULE)
        .agg({"Zamkniecie": "last", "Otwarcie": "first"})
        .dropna()
    )


def weekly_log_returns(weekly: pd.DataFrame) -> pd.Series:
    """Logarytmiczne tygodniowe stopy zwrotu, przeskalowane do punktow procentowych."""
    returns = config.RETURN_SCALE * np.log(weekly["Zamkniecie"]).diff().dropna()
    returns.name = "r_weekly"
    return returns


def daily_log_returns(daily: pd.DataFrame) -> pd.Series:
    """Logarytmiczne dzienne stopy zwrotu w tej samej skali co tygodniowe."""
    returns = config.RETURN_SCALE * np.log(daily["Zamkniecie"]).diff().dropna()
    returns.name = "r_daily"
    return returns


def split_point(returns: pd.Series, start=None) -> int:
    """Pozycja pierwszego tygodnia proby testowej."""
    start = config.SIMULATION_START if start is None else start
    return int(returns.index.searchsorted(start))


def sample_description(daily: pd.DataFrame, returns: pd.Series, start=None) -> dict:
    """Licznosci proby, ktore opisuja badanie. Liczone z danych, nie wpisane."""
    start = config.SIMULATION_START if start is None else start
    idx = split_point(returns, start)
    return {
        "obserwacje_dzienne": len(daily),
        "pierwsza_obserwacja": daily.index.min().date().isoformat(),
        "ostatnia_obserwacja": daily.index.max().date().isoformat(),
        "tygodnie_treningowe": idx - 1,
        "tygodnie_testowe": len(returns) - idx,
    }


def adf_table(weekly: pd.DataFrame) -> pd.DataFrame:
    """Test Dickeya-Fullera dla logarytmu cen i dla pierwszych roznic.

    Test liczony jest na szeregu tygodniowym, bo to on wchodzi do modelu.
    Na danych dziennych statystyka jest inna i nie opisuje szeregu, ktorego
    stacjonarnosc jest tu warunkiem koniecznym.
    """
    log_prices = np.log(weekly["Zamkniecie"].astype(float))
    rows = []
    for label, series in (
        ("Logarytm cen akcji", log_prices),
        ("Logarytmowane pierwsze roznice cen akcji", log_prices.diff().dropna()),
    ):
        statistic, p_value = adfuller(series, autolag="AIC", result_object=False)[:2]
        rows.append({"Szereg": label, "Statystyka testowa": statistic, "P-value": p_value})
    return pd.DataFrame(rows).set_index("Szereg")
