"""Estymacja modelu MS-AR i generowanie sygnalow procedura rozszerzajacego sie okna."""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tools.sm_exceptions import ConvergenceWarning

from . import config


def fit_ms_ar(returns: pd.Series, search_reps: int):
    """Estymuje autoregresyjny model przelacznikowy Markowa metoda najwiekszej wiarygodnosci.

    Przeszukiwanie punktow startowych jest losowe, wiec generator przekazujemy
    jawnie przez argument rng - bez niego dwa przebiegi tego samego kodu daja
    rozne oszacowania wariancji rezimow na drugim miejscu po przecinku.
    Globalne np.random.seed tu nie dziala, bo statsmodels uzywa wlasnego
    generatora.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        model = sm.tsa.MarkovAutoregression(
            returns,
            k_regimes=config.N_REGIMES,
            order=config.AR_ORDER,
            switching_trend=True,
            switching_variance=True,
        )
        return model.fit(search_reps=search_reps, disp=False, rng=config.RANDOM_SEED)


def regime_variances(result) -> dict:
    """Identyfikuje rezim niskiej i wysokiej zmiennosci po wariancji skladnika losowego.

    Numeracja stanow w modelu jest dowolna, wiec rezimow nie wolno rozpoznawac
    po indeksie - rozstrzyga oszacowana wariancja.
    """
    sigma = result.params[result.params.index.str.contains("sigma2")]
    low = int(np.argmin(sigma.to_numpy()))
    high = int(np.argmax(sigma.to_numpy()))
    return {
        "low_idx": low,
        "high_idx": high,
        "low_var": float(sigma.iloc[low]),
        "high_var": float(sigma.iloc[high]),
    }


def transition_matrix(result, regimes: dict) -> pd.DataFrame:
    """Macierz prawdopodobienstw przejscia z etykietami rezimow, nie numerami stanow."""
    p00 = float(result.params.get("p[0->0]", np.nan))
    p10 = float(result.params.get("p[1->0]", np.nan))
    if np.isnan(p00) or np.isnan(p10):
        raise RuntimeError("Model nie zwrocil parametrow macierzy przejscia.")

    if regimes["low_idx"] == 0:
        low_low, high_low = p00, p10
    else:
        low_low, high_low = 1.0 - p10, 1.0 - p00

    return pd.DataFrame(
        {
            "Do: niska zmiennosc": [low_low, high_low],
            "Do: wysoka zmiennosc": [1.0 - low_low, 1.0 - high_low],
        },
        index=["Z: niska zmiennosc", "Z: wysoka zmiennosc"],
    )


def smoothed_high_vol(result, regimes: dict) -> pd.Series:
    """Wygladzone prawdopodobienstwa stanu wysokiej zmiennosci dla analizy historycznej."""
    return result.smoothed_marginal_probabilities[regimes["high_idx"]]


def walk_forward_signals(returns: pd.Series, start_idx: int) -> pd.DataFrame:
    """Sygnaly z procedury rozszerzajacego sie okna.

    W kroku t model estymowany jest wylacznie na danych do t wlacznie, a decyzja
    opiera sie na prawdopodobienstwie filtrowanym, nie wygladzonym. Bez tego
    rozrozniena do sygnalu przeciekaja informacje z przyszlosci.
    """
    dates, probs, signals = [], [], []
    last_result = None

    for i in range(start_idx, len(returns)):
        window = returns.iloc[: i + 1]
        prob_low = config.SIGNAL_THRESHOLD
        try:
            result = fit_ms_ar(window, config.SEARCH_REPS_WALK_FORWARD)
            last_result = result
            regimes = regime_variances(result)
            prob_low = float(
                result.filtered_marginal_probabilities[regimes["low_idx"]].iloc[-1]
            )
        except Exception:
            # Brak zbieznosci w pojedynczym kroku nie przerywa symulacji;
            # przy prawdopodobienstwie rownym progowi sygnal wypada na 0.
            pass

        dates.append(returns.index[i])
        probs.append(prob_low)
        signals.append(int(prob_low > config.SIGNAL_THRESHOLD))

    frame = pd.DataFrame(
        {"prob_low_vol": probs, "signal": signals}, index=pd.DatetimeIndex(dates)
    )
    frame.index.name = "Data"
    return frame, last_result


def high_risk_share(signals: pd.DataFrame) -> float:
    """Udzial tygodni, w ktorych model wskazal stan wysokiego ryzyka."""
    return float((signals["signal"] == 0).mean())
