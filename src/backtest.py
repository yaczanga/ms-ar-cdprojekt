"""Symulacja strategii i benchmarku kup-i-trzymaj."""

from __future__ import annotations

import pandas as pd

from . import config

BUY = "KUP"
SELL = "SPRZEDAJ"


def simulate(daily: pd.DataFrame, signals: pd.DataFrame, capital=None, commission=None) -> dict:
    """Symuluje strategie z opoznieniem realizacji o jedna sesje.

    Sygnal wyznaczony na zamkniecie ostatniego dnia tygodnia realizowany jest po
    cenie otwarcia pierwszej kolejnej sesji. Dzieki temu transakcja nie korzysta
    z ceny, ktora w chwili decyzji nie byla jeszcze znana.
    """
    capital = config.INITIAL_CAPITAL if capital is None else capital
    commission = config.COMMISSION if commission is None else commission

    cash, shares, in_market = capital, 0.0, False
    records, curve_dates, curve_values = [], [], []
    bench_shares = None

    for signal_date, signal in signals["signal"].items():
        future = daily.loc[signal_date:]
        if len(future) < 2:
            break

        trade_date = future.index[1]
        open_price = float(future.iloc[1]["Otwarcie"])

        if bench_shares is None:
            bench_shares = capital / (open_price * (1.0 + commission))

        operation, volume, commission_paid = None, 0.0, 0.0
        if signal == 1 and not in_market:
            net_cash = cash / (1.0 + commission)
            shares = net_cash / open_price
            commission_paid = cash - net_cash
            cash, in_market = 0.0, True
            operation, volume = BUY, shares
        elif signal == 0 and in_market:
            gross = shares * open_price
            commission_paid = gross * commission
            cash = gross - commission_paid
            shares, in_market = 0.0, False
            operation = SELL

        value = shares * open_price if in_market else cash
        curve_dates.append(trade_date)
        curve_values.append(value)

        if operation is not None:
            benchmark_value = bench_shares * open_price
            records.append(
                {
                    "Data transakcji": trade_date,
                    "Operacja": operation,
                    "Cena": open_price,
                    "Wolumen": volume,
                    "Prowizja": commission_paid,
                    "Saldo": cash,
                    "Benchmark": benchmark_value,
                    "Wartosc strategii": value,
                    "Roznica": value - benchmark_value,
                }
            )

    if not curve_dates:
        raise RuntimeError("Symulacja nie wygenerowala zadnego punktu krzywej kapitalu.")

    equity = pd.Series(curve_values, index=pd.DatetimeIndex(curve_dates), name="strategia")
    benchmark = pd.Series(
        [bench_shares * float(daily.loc[d, "Otwarcie"]) for d in curve_dates],
        index=equity.index,
        name="kup_i_trzymaj",
    )
    log = pd.DataFrame(records).set_index("Data transakcji")

    return {
        "equity": equity,
        "benchmark": benchmark,
        "log": log,
        "summary": {
            "kapital_poczatkowy": capital,
            "prowizja": commission,
            "kapital_koncowy_strategia": float(equity.iloc[-1]),
            "kapital_koncowy_benchmark": float(benchmark.iloc[-1]),
            "stopa_zwrotu_strategia": float(equity.iloc[-1] / capital - 1.0) * 100.0,
            "stopa_zwrotu_benchmark": float(benchmark.iloc[-1] / capital - 1.0) * 100.0,
            "liczba_transakcji": int(len(log)),
        },
    }


def save_log(log: pd.DataFrame, path=None) -> None:
    """Zapisuje dziennik transakcji do pliku wynikowego."""
    config.ensure_output_dirs()
    path = config.TABLES / "transakcje_walk_forward.csv" if path is None else path
    log.to_csv(path, float_format="%.4f", encoding="utf-8")
