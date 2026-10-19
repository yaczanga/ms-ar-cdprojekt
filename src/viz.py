"""Rysunki projektu.

Barwy pochodza wylacznie z modulu plot_style i sa wybierane przez role, jaka
seria pelni w danych: cynober to przedmiot uwagi, blekit to odniesienie.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter
from matplotlib.transforms import offset_copy

from . import config, plot_style as style

style.apply_style()

# Spacja nierozdzielajaca jako separator tysiecy, zgodnie z zapisem liczb
# w pozostalych napisach projektu.
NBSP = " "


# Odsuniecie znacznika transakcji od krzywej, w punktach typograficznych.
MARKER_OFFSET_PT = 11


def _zloty_axis(ax) -> None:
    """Formatuje os wartosci zlotowych: separator tysiecy od pieciu cyfr."""
    ax.yaxis.set_major_formatter(
        FuncFormatter(lambda value, _: f"{value:,.0f}".replace(",", NBSP))
    )


def _save(fig, name: str, save: bool) -> None:
    """Zapisuje rysunek do katalogu wynikowego pod podana nazwa."""
    if not save:
        return
    config.ensure_output_dirs()
    fig.savefig(config.FIGURES / name, dpi=style.SAVE_DPI, bbox_inches="tight")


def plot_frequency_comparison(
    daily_returns: pd.Series, weekly_returns: pd.Series, save: bool = False
):
    """Porownanie stop zwrotu w interwale dziennym i tygodniowym.

    Dane dzienne sa odniesieniem, dane tygodniowe - interwalem przyjetym
    w badaniu, wiec to one niosa akcent.
    """
    fig, (ax_daily, ax_weekly) = plt.subplots(2, 1, figsize=style.WIDE, sharex=True)

    ax_daily.plot(daily_returns.index, daily_returns.values,
                  color=style.REFERENCE, linewidth=0.7)
    ax_daily.set_title("Dzienne logarytmiczne stopy zwrotu")
    ax_daily.set_ylabel("punkty procentowe")

    ax_weekly.plot(weekly_returns.index, weekly_returns.values,
                   color=style.ACCENT, linewidth=0.9)
    ax_weekly.set_title("Tygodniowe logarytmiczne stopy zwrotu")
    ax_weekly.set_ylabel("punkty procentowe")

    for ax in (ax_daily, ax_weekly):
        ax.axhline(0, color=style.AXES, linewidth=0.8)
        style.decimal_comma(ax, axis="y", places=0)

    fig.tight_layout()
    _save(fig, "01_dane_dzienne_i_tygodniowe.png", save)
    return fig


def plot_regimes(prices: pd.Series, prob_high: pd.Series, title: str,
                 name: str, save: bool = False):
    """Kurs akcji i prawdopodobienstwo rezimu wysokiej zmiennosci.

    Kurs jest odniesieniem, prawdopodobienstwo stanu wysokiej zmiennosci jest
    zdarzeniem negatywnym, wiec nosi barwe ryzyka.
    """
    fig, (ax_price, ax_prob) = plt.subplots(2, 1, figsize=style.WIDE, sharex=True)

    ax_price.plot(prices.index, prices.values, color=style.REFERENCE, linewidth=1.4)
    ax_price.set_title(title)
    ax_price.set_ylabel("kurs zamknięcia (zł)")
    _zloty_axis(ax_price)

    ax_prob.plot(prob_high.index, prob_high.values, color=style.RISK, linewidth=1.4)
    ax_prob.fill_between(prob_high.index, prob_high.values, 0,
                         color=style.RISK, alpha=0.18)
    ax_prob.axhline(config.SIGNAL_THRESHOLD, color=style.AXES,
                    linestyle="--", linewidth=1.0)
    ax_prob.set_title("Prawdopodobieństwo reżimu wysokiej zmienności")
    ax_prob.set_ylabel("prawdopodobieństwo")
    ax_prob.set_ylim(-0.05, 1.05)
    style.decimal_comma(ax_prob, axis="y", places=1)

    fig.tight_layout()
    _save(fig, name, save)
    return fig


def plot_strategy(equity: pd.Series, benchmark: pd.Series, log: pd.DataFrame,
                  save: bool = False):
    """Krzywa kapitalu strategii na tle pasywnego kup-i-trzymaj.

    Strategia jest przedmiotem badania i nosi akcent, benchmark jest
    odniesieniem. Znaczniki transakcji nie sa trzecia seria, tylko adnotacja na
    krzywej strategii - niosa barwe tekstu, a kupno od sprzedazy odroznia
    ksztalt, czytelny takze w druku czarno-bialym.

    Kupno stoi POD krzywa, sprzedaz NAD nia. Postawione na krzywej zlewaja sie
    w jeden znak wszedzie tam, gdzie wyjscie nastepuje kilka tygodni po
    wejsciu - a takich par jest w tym przebiegu wiekszosc. Odsuniecie liczone
    jest w punktach typograficznych, wiec nie przesuwa znacznika wzgledem daty
    ani wartosci portfela.
    """
    fig, ax = plt.subplots(figsize=style.WIDE)

    ax.plot(benchmark.index, benchmark.values, color=style.REFERENCE,
            linewidth=1.6, linestyle="--", label="Kup i trzymaj")
    ax.plot(equity.index, equity.values, color=style.ACCENT,
            linewidth=2.0, label="Strategia MS-AR")

    markers = (("KUP", "^", -MARKER_OFFSET_PT, "Kupno"),
               ("SPRZEDAJ", "v", MARKER_OFFSET_PT, "Sprzedaż"))
    handles = []
    for operation, marker, offset, label in markers:
        shifted = offset_copy(ax.transData, fig=fig, y=offset, units="points")
        dates = [d for d in log.index[log["Operacja"] == operation] if d in equity.index]
        if dates:
            ax.scatter(dates, equity.loc[dates], marker=marker, s=55,
                       color=style.TEXT_SECONDARY, zorder=5, transform=shifted)
        handles.append(
            Line2D([], [], marker=marker, linestyle="none", markersize=8,
                   color=style.TEXT_SECONDARY, label=label)
        )

    ax.set_title("Symulacja strategii na próbie testowej")
    ax.set_ylabel("wartość portfela (zł)")
    # Dwie legendy: serie u gory, ksztalty znacznikow nizej. W jednej ramce
    # znacznik czytalby sie jak trzecia seria, a nie jak adnotacja na krzywej.
    series_legend = ax.legend(loc="upper left")
    ax.add_artist(series_legend)
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, 0.80),
              labelcolor=style.TEXT_SECONDARY)
    _zloty_axis(ax)

    fig.tight_layout()
    _save(fig, "04_symulacja_strategii.png", save)
    return fig
