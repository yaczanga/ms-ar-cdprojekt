"""Gwarancje metodologiczne badania.

Testy nie sprawdzaja, czy kod sie wykonuje, tylko czy nie lamie zalozen, na
ktorych opiera sie wniosek: braku dostepu do przyszlosci, opoznienia realizacji
zlecenia i rozpoznawania rezimow po wariancji.
"""

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src import backtest, config, data_load, regimes


@pytest.fixture(scope="module")
def daily():
    return data_load.load_daily_prices()


@pytest.fixture(scope="module")
def weekly_returns(daily):
    return data_load.weekly_log_returns(data_load.to_weekly(daily))


def test_podzial_proby_zgodny_z_danymi(daily, weekly_returns):
    """Licznosci proby wynikaja z danych, nie z liczby wpisanej w kod."""
    opis = data_load.sample_description(daily, weekly_returns)
    assert opis["obserwacje_dzienne"] == len(daily)
    assert opis["tygodnie_treningowe"] + opis["tygodnie_testowe"] == len(weekly_returns) - 1
    assert opis["tygodnie_testowe"] == len(
        weekly_returns.loc[config.SIMULATION_START:]
    ) - (1 if weekly_returns.index[0] >= pd.Timestamp(config.SIMULATION_START) else 0)


def test_estymacja_nie_widzi_danych_po_dacie_sygnalu(weekly_returns, monkeypatch):
    """Okno estymacji konczy sie dokladnie na tygodniu, ktorego dotyczy sygnal.

    To jest test na look-ahead bias i sprawdza go strukturalnie: podstawiamy
    atrape pod estymacje i zapisujemy, jaki jest ostatni tydzien kazdego okna.
    Porownywanie samych prawdopodobienstw niczego by nie dowiodlo, bo
    w oknie konczacym sie w chwili t prawdopodobienstwo wygladzone rowna sie
    filtrowanemu - podmiana jednego na drugie nie zmienia wyniku.
    """
    widziane = []

    class AtrapaWyniku:
        params = pd.Series([5.0, 50.0], index=["sigma2[0]", "sigma2[1]"])
        filtered_marginal_probabilities = pd.DataFrame({0: [0.9], 1: [0.1]})

    def atrapa(returns, search_reps):
        widziane.append(returns.index[-1])
        return AtrapaWyniku()

    monkeypatch.setattr(regimes, "fit_ms_ar", atrapa)
    sygnaly, _ = regimes.walk_forward_signals(
        weekly_returns, data_load.split_point(weekly_returns)
    )

    assert len(widziane) == len(sygnaly)
    assert widziane == list(sygnaly.index)


def test_transakcja_po_cenie_otwarcia_nastepnej_sesji():
    """Zlecenie realizowane jest po cenie, ktora w chwili decyzji nie byla znana.

    Sygnal pada na sesji 2024-01-05, wiec kupno musi odbyc sie po cenie
    otwarcia 2024-01-08, a nie po zadnej cenie z dnia sygnalu.
    """
    index = pd.to_datetime(["2024-01-05", "2024-01-08", "2024-01-09"])
    daily = pd.DataFrame(
        {"Otwarcie": [100.0, 110.0, 120.0], "Zamkniecie": [101.0, 111.0, 121.0]},
        index=index,
    )
    signals = pd.DataFrame({"signal": [1, 1]}, index=index[:2])

    wynik = backtest.simulate(daily, signals, capital=1000.0, commission=0.0)
    transakcja = wynik["log"].iloc[0]
    assert transakcja.name == index[1]
    assert transakcja["Cena"] == pytest.approx(110.0)
    assert transakcja["Wolumen"] == pytest.approx(1000.0 / 110.0)


def test_rezimy_rozpoznawane_po_wariancji_nie_po_numerze_stanu():
    """Numeracja stanow w modelu jest dowolna, wiec nie moze rozstrzygac.

    Dla obu kolejnosci wariancji funkcja musi wskazac ten sam rezim jako
    niski. Test zawiedzie, gdyby ktos zastapil argmin stalym indeksem 0.
    """
    for sigma, oczekiwany_niski in (([5.0, 50.0], 0), ([50.0, 5.0], 1)):
        wynik = SimpleNamespace(
            params=pd.Series(sigma, index=["sigma2[0]", "sigma2[1]"])
        )
        rezimy = regimes.regime_variances(wynik)
        assert rezimy["low_idx"] == oczekiwany_niski
        assert rezimy["low_var"] == pytest.approx(5.0)
        assert rezimy["high_var"] == pytest.approx(50.0)


def test_wiersze_macierzy_przejscia_sumuja_sie_do_jednosci():
    """Etykiety rezimow nie moga rozjechac sie z prawdopodobienstwami."""
    for low_idx, high_idx in ((0, 1), (1, 0)):
        wynik = SimpleNamespace(
            params=pd.Series(
                [0.8, 0.3, 5.0, 50.0],
                index=["p[0->0]", "p[1->0]", "sigma2[0]", "sigma2[1]"],
            )
        )
        macierz = regimes.transition_matrix(
            wynik, {"low_idx": low_idx, "high_idx": high_idx}
        )
        np.testing.assert_allclose(macierz.sum(axis=1).to_numpy(), [1.0, 1.0], rtol=1e-12)
        assert (macierz.to_numpy() >= 0).all()


def test_brak_prowizji_oznacza_zerowy_koszt_transakcyjny(daily):
    """Wariant badania liczony jest bez kosztow transakcyjnych.

    Gdyby ktos przestawil COMMISSION, suma prowizji w dzienniku przestanie
    byc zerowa i ten test to wychwyci.
    """
    assert config.COMMISSION == 0.0
    index = pd.to_datetime(["2024-01-05", "2024-01-08", "2024-01-09", "2024-01-10"])
    frame = pd.DataFrame(
        {"Otwarcie": [100.0, 110.0, 120.0, 130.0], "Zamkniecie": [1.0, 2.0, 3.0, 4.0]},
        index=index,
    )
    signals = pd.DataFrame({"signal": [1, 0, 1]}, index=index[:3])
    wynik = backtest.simulate(frame, signals, capital=1000.0)
    assert wynik["log"]["Prowizja"].sum() == pytest.approx(0.0)
