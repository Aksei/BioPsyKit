"""Module providing functions for plotting ECG data."""
from typing import Optional, Sequence, Tuple, Dict, List

import numpy as np
import pandas as pd
import seaborn as sns
import neurokit2 as nk

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.gridspec as gs
import matplotlib.dates as mdates
import matplotlib.ticker as mticks

from neurokit2.hrv.hrv_frequency import _hrv_frequency_show
from neurokit2.hrv.hrv_utils import _hrv_get_rri

import biopsykit.colors as colors
from biopsykit.signals.ecg import EcgProcessor
from biopsykit.signals.ecg.ecg import _assert_ecg_input
from biopsykit.utils.array_handling import sanitize_input_1d
from biopsykit.utils.datatype_helper import EcgResultDataFrame


__all__ = [
    "ecg_plot",
    "hr_plot",
    "hrv_plot",
    "hr_distribution_plot",
    "rr_distribution_plot",
    "hrv_frequency_plot",
    "hrv_poincare_plot",
    "individual_beats_plot",
]

# TODO add signal plot method for all phases


def ecg_plot(
    ecg_processor: Optional["EcgProcessor"] = None,
    key: Optional[str] = None,
    ecg_signal: Optional[pd.DataFrame] = None,
    heart_rate: Optional[pd.DataFrame] = None,
    sampling_rate: Optional[int] = 256,
    plot_ecg_signal: Optional[bool] = True,
    plot_distribution: Optional[bool] = True,
    plot_individual_beats: Optional[bool] = True,
    **kwargs,
) -> Tuple[plt.Figure, Sequence[plt.Axes]]:
    """Plot ECG processing results.

    By default, this plot consists of four subplots:
        * `top left`: course of ECG signal plot with signal quality indicator,
          detected R peaks and R peaks marked as outlier
        * `bottom left`: course of heart rate (tachogram)
        * `top right`: individual heart beats overlaid on top of each other
        * `bottom right`: heart rate distribution (histogram)


    To use this function, either simply pass an :class:`~biopsykit.signals.ecg.EcgProcessor` object together with
    a ``key`` indicating which phase needs to be processed should be processed or the two dataframes ``ecg_signal``
    and ``heart_rate`` resulting from :meth:`~biopsykit.signals.ecg.EcgProcessor.ecg_process()`.


    Parameters
    ----------
    ecg_processor : :class:`~biopsykit.signals.ecg.EcgProcessor`, optional
        ``EcgProcessor`` object. If this argument is supplied, the ``key`` argument needs to be supplied as well
    key : str, optional
        Dictionary key of the phase to process. Needed when ``ecg_processor`` is passed as argument
    ecg_signal : :class:`~biopsykit.utils.datatype_helper.EcgResultDataFrame`, optional
        Dataframe with processed ECG signal. Output from :meth:`~biopsykit.signals.ecg.EcgProcessor.ecg_process()`
    heart_rate : :class:`~pandas.DataFrame`, optional
        Dataframe with heart rate output. Output from :meth:`~biopsykit.signals.ecg.EcgProcessor.ecg_process()`
    sampling_rate : float, optional
        Sampling rate of recorded data. Not needed if ``ecg_processor`` is supplied as parameter. Default: 256
    plot_ecg_signal : bool, optional
        Whether to plot the cleaned ECG signal in a subplot or not. Default: ``True``
    plot_distribution : bool, optional
        Whether to plot the heart rate distribution in a subplot or not. Default: ``True``
    plot_individual_beats : bool, optional
        Whether to plot the individual heart beats in a subplot or not. Default: ``True``
    kwargs
        Additional parameters to configure the plot. Parameters include:
            * ``figsize``: figure size
            * ``title``: Optional name to add to plot title (after "Electrocardiogram (ECG)")
            * ``legend_loc``: Location of legend in plot. Passed as `loc` parameter to :func:`matplotlib.Axes.legend`
            * ``legend_fontsize``: Fontsize of legend text. Passed as `fontsize` :func:`matplotlib.Axes.legend`


    Returns
    -------
    fig : :class:`matplotlib.figure.Figure`
        Figure object
    axs : list of :class:`matplotlib.axes.Axes`
        list of subplot axes objects


    See Also
    --------
    `hr_plot`
        plot heart rate only
    `hr_distribution_plot`
        plot heart rate distribution only
    `individual_beats_plot`
        plot individual beats only
    `hrv_plot`
        plot heart rate variability

    """
    _assert_ecg_input(ecg_processor, key, ecg_signal, heart_rate)
    if ecg_processor is not None:
        ecg_signal = ecg_processor.ecg_result[key]
        heart_rate = ecg_processor.heart_rate[key]
        sampling_rate = ecg_processor.sampling_rate

    sns.set_palette(colors.fau_palette)

    figsize = kwargs.get("figsize", (15, 5))
    title = kwargs.get("title", None)
    if isinstance(ecg_signal.index, pd.DatetimeIndex):
        plt.rcParams["timezone"] = ecg_signal.index.tz.zone
    plt.rcParams["mathtext.default"] = "regular"

    # Prepare figure and set axes
    fig = plt.figure(figsize=figsize, constrained_layout=False)

    axs = _get_ecg_plot_specs(fig, plot_ecg_signal, plot_individual_beats, plot_distribution)

    if title:
        fig.suptitle("Electrocardiogram (ECG) – {}".format(title), fontweight="bold")
    else:
        fig.suptitle("Electrocardiogram (ECG)", fontweight="bold")
    plt.subplots_adjust(hspace=0.3, wspace=0.1)

    peaks = np.where(ecg_signal["ECG_R_Peaks"] == 1)[0]
    outlier = np.array([])
    if "R_Peak_Outlier" in ecg_signal:
        outlier = np.where(ecg_signal["R_Peak_Outlier"] == 1)[0]

    peaks = np.setdiff1d(peaks, outlier)

    if plot_ecg_signal:
        _ecg_plot(axs, ecg_signal, peaks, outlier, **kwargs)

    # Plot heart rate: plot outlier only if no ECG signal is plotted
    hr_plot(heart_rate, plot_outlier=not plot_ecg_signal, outlier=ecg_signal.index[outlier], ax=axs["hr"])
    axs["hr"].set_xlabel("Time")

    # Plot individual heart beats
    if plot_individual_beats:
        individual_beats_plot(ecg_signal, peaks, sampling_rate, ax=axs["beats"])

    # Plot heart rate distribution
    if plot_distribution:
        hr_distribution_plot(heart_rate, ax=axs["dist"])

    fig.tight_layout()
    return fig, list(axs.values())


def _get_ecg_plot_specs(
    fig: plt.Figure, plot_ecg_signal: bool, plot_individual_beats: bool, plot_distribution: bool
) -> Dict[str, plt.Axes]:
    if plot_individual_beats or plot_distribution:
        spec = gs.GridSpec(2, 2, width_ratios=[3, 1])
        if plot_ecg_signal:
            axs = {
                "ecg": fig.add_subplot(spec[0, :-1]),
                "hr": fig.add_subplot(spec[1, :-1]),
            }
        else:
            axs = {"hr": fig.add_subplot(spec[:, :-1])}
        if plot_distribution and plot_individual_beats:
            axs["beats"] = fig.add_subplot(spec[0, -1])
            axs["dist"] = fig.add_subplot(spec[1, -1])
        elif plot_individual_beats:
            axs["beats"] = fig.add_subplot(spec[:, -1])
        elif plot_distribution:
            axs["dist"] = fig.add_subplot(spec[:, -1])
    else:
        if plot_ecg_signal:
            axs = {"ecg": fig.add_subplot(2, 1, 1), "hr": fig.add_subplot(2, 1, 2)}
        else:
            axs = {"hr": fig.add_subplot(1, 1, 1)}
    return axs


def _ecg_plot(
    axs: Dict[str, plt.Axes],
    ecg_signal: EcgResultDataFrame,
    peaks: np.array,
    outlier: np.array,
    **kwargs,
):
    legend_loc = kwargs.get("legend_loc", "upper right")
    legend_fontsize = kwargs.get("legend_fontsize", "small")

    axs["ecg"].get_shared_x_axes().join(axs["ecg"], axs["hr"])

    # z-normalize the ecg signal for better visualization
    ecg_clean = nk.standardize(ecg_signal["ECG_Clean"])
    x_axis = ecg_signal.index
    ylim_ecg = [-5, 10]
    quality = ecg_signal["ECG_Quality"] * ylim_ecg[1]
    minimum_line = np.full(len(x_axis), ylim_ecg[0])

    # Plot quality area first
    axs["ecg"].fill_between(
        x_axis,
        minimum_line,
        quality,
        alpha=0.2,
        zorder=2,
        interpolate=True,
        facecolor=colors.fau_color("med"),
        label="Quality",
    )
    # Plot signals
    axs["ecg"].plot(
        ecg_clean,
        color=colors.fau_color("fau"),
        label="ECG (z-norm.)",
        zorder=1,
        linewidth=1.5,
    )
    axs["ecg"].scatter(
        x_axis[peaks],
        ecg_clean.iloc[peaks],
        color=colors.fau_color("nat"),
        label="R Peaks",
        zorder=2,
    )
    if "R_Peak_Outlier" in ecg_signal:
        axs["ecg"].scatter(
            x_axis[outlier],
            ecg_clean[outlier],
            color=colors.fau_color("phil"),
            label="Outlier",
            zorder=2,
        )
    axs["ecg"].set_ylabel("ECG Signal (z-norm.)")
    axs["ecg"].set_ylim(ylim_ecg)

    # Optimize legend
    handles, labels = axs["ecg"].get_legend_handles_labels()
    # order = [2, 0, 1, 3]
    if "R_Peak_Outlier" in ecg_signal:
        order = [0, 1, 2, 3]
    else:
        order = [0, 1, 2]

    axs["ecg"].legend(
        [handles[idx] for idx in order], [labels[idx] for idx in order], loc=legend_loc, fontsize=legend_fontsize
    )

    axs["ecg"].tick_params(axis="x", which="both", bottom=True, labelbottom=True)
    axs["ecg"].tick_params(axis="y", which="major", left=True)

    if isinstance(ecg_signal.index, pd.DatetimeIndex):
        # TODO add axis style for non-Datetime axes
        axs["ecg"].xaxis.set_major_locator(mdates.MinuteLocator())
        axs["ecg"].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        axs["ecg"].xaxis.set_minor_locator(mticks.AutoMinorLocator(6))


def hr_plot(
    heart_rate: pd.DataFrame,
    plot_mean: Optional[bool] = True,
    plot_outlier: Optional[bool] = True,
    outlier: Optional[np.ndarray] = None,
    **kwargs,
) -> Tuple[plt.Figure, plt.Axes]:
    """Plot course of heart rate over time (tachogram).

    This plot is also used as subplot in :func:`~biopsykit.signals.ecg.plotting.ecg_plot`.


    Parameters
    ----------
    heart_rate : :class:`~pandas.DataFrame`
        Dataframe with heart rate output. Output from :meth:`~biopsykit.signals.ecg.EcgProcessor.ecg_process()`
    plot_mean : bool, optional
        Whether to plot the mean heart rate as horizontal line or not. Default: ``True``
    plot_outlier : bool, optional
        Whether to plot ECG signal outlier as vertical outlier or not. Default: ``True``
    outlier : :class:`numpy.array`, optional
        List of outlier indices. Only needed if ``plot_outlier`` is ``True``. Default: ``None``
    kwargs
        Additional parameters to configure the plot. Parameters include:
            * ``figsize``: Figure size
            * ``title``: Optional name to add to plot title (after "Electrocardiogram (ECG)")
            * ``legend_loc``: Location of legend in plot. Passed as `loc` parameter to :func:`matplotlib.Axes.legend`
            * ``legend_fontsize``: Fontsize of legend text. Passed as `fontsize` :func:`matplotlib.Axes.legend`
            * ``ax``: Pre-existing axes for the plot. Otherwise, a new figure and axes object are created and returned.


    Returns
    -------
    fig : :class:`matplotlib.figure.Figure`
        figure object
    ax : :class:`matplotlib.axes.Axes`
        axes object


    See Also
    --------
    `ecg_plot`
        plot ECG overview

    """
    ax: plt.Axes = kwargs.get("ax", None)
    figsize = kwargs.get("figsize", (15, 5))
    title: str = kwargs.get("title", None)
    legend_loc = kwargs.get("legend_loc", "upper right")
    legend_fontsize = kwargs.get("legend_fontsize", "small")
    plt.rcParams["mathtext.default"] = "regular"

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.get_figure()

    sns.set_palette(colors.fau_palette)

    if title:
        ax.set_title("Heart Rate – {}".format(title))

    ax.plot(
        heart_rate["Heart_Rate"],
        color=colors.fau_color("wiso"),
        label="Heart Rate",
        linewidth=1.5,
    )

    if plot_mean:
        rate_mean = heart_rate["Heart_Rate"].mean()
        ax.axhline(
            y=rate_mean,
            label="Mean: {:.1f} bpm".format(rate_mean),
            linestyle="--",
            color=colors.adjust_color("wiso", 1.5),
            linewidth=2,
        )
        ax.margins(x=0)

    ax.set_ylim(auto=True)

    if plot_outlier and outlier is not None:
        ax.vlines(
            outlier,
            ymin=0,
            ymax=1,
            transform=ax.get_xaxis_transform(),
            colors=colors.fau_color("phil"),
            alpha=0.5,
            label="ECG Outlier",
        )
        ax.relim()

    if isinstance(heart_rate.index, pd.DatetimeIndex):
        # TODO add axis style for non-Datetime axes
        ax.xaxis.set_major_locator(mdates.MinuteLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax.xaxis.set_minor_locator(mticks.AutoMinorLocator(6))

    ax.tick_params(axis="x", which="both", bottom=True)
    ax.tick_params(axis="y", which="major", left=True)
    ax.yaxis.set_major_locator(mticks.MaxNLocator(5, steps=[5, 10]))

    if plot_mean or plot_outlier:
        ax.legend(loc=legend_loc, fontsize=legend_fontsize)

    ax.set_xlabel("Time")
    ax.set_ylabel("Heart Rate [bpm]")

    fig.tight_layout()
    fig.autofmt_xdate(rotation=0, ha="center")
    return fig, ax


def hrv_plot(
    ecg_processor: Optional["EcgProcessor"] = None,
    key: Optional[str] = None,
    ecg_signal: Optional[pd.DataFrame] = None,
    rpeaks: Optional[pd.DataFrame] = None,
    sampling_rate: Optional[int] = 256,
    plot_psd: Optional[bool] = True,
    **kwargs,
) -> Tuple[plt.Figure, Sequence[plt.Axes]]:
    """Plot Heart Rate Variability results.

    By default, it consists of 3 plots:
        * `top left`: RR interval distribution (histogram) including boxplot to visualize distribution and median
        * `bottom left`: Power Spectral Density (PSD) plot of RR intervals
        * `right`: Poincaré plot of RR intervals

    To use this function, either simply pass an :class:`~biopsykit.signals.ecg.EcgProcessor` object together with
    a ``key`` indicating which phase needs to be processed should be processed or the two dataframes ``ecg_signal``
    and ``heart_rate`` resulting from :meth:`~biopsykit.signals.ecg.EcgProcessor.ecg_process()`.


    Parameters
    ----------
    ecg_processor : EcgProcessor, optional
        `EcgProcessor` object. If this argument is passed, the ``key`` argument needs to be supplied as well
    key : str, optional
        Dictionary key of the phase to process. Needed when ``ecg_processor`` is passed as argument
    ecg_signal : pd.DataFrame, optional
        dataframe with processed ECG signal. Output from `EcgProcessor.ecg_process()`
    rpeaks : :class:`~biopsykit.utils.datatype_helper.RPeakDataFrame`, optional
        Dataframe with detected R peaks. Output from :meth:`~biopsykit.signals.ecg.EcgProcessor.ecg_process()`
    sampling_rate : float, optional
        Sampling rate of recorded data. Not needed if ``ecg_processor`` is supplied as parameter. Default: 256 Hz
    plot_psd : bool, optional
        Whether to plot power spectral density (PDF) from frequency-based HRV analysis in a subplot or not.
        Default: ``True``
    kwargs
        Additional parameters to configure the plot. Parameters include:
            * ``figsize``: Figure size
            * ``title``: Optional name to add to plot title (after "Electrocardiogram (ECG)")
            * ``legend_loc``: Location of legend in plot. Passed as `loc` parameter to :func:`matplotlib.Axes.legend`
            * ``legend_fontsize``: Fontsize of legend text. Passed as `fontsize` :func:`matplotlib.Axes.legend`
            * ``ax``: Pre-existing axes for the plot. Otherwise, a new figure and axes object are created and returned.

    Returns
    -------
    fig : :class:`matplotlib.figure.Figure`
        figure object
    ax : :class:`matplotlib.axes.Axes`
        axes object


    See Also
    --------
    `rr_distribution_plot`
        plot RR interval distribution
    `hrv_poincare_plot`
        plot HRV using Poincaré plot
    `hrv_frequency_plot`
        plot Power Spectral Density (PSD) of RR intervals

    """
    _assert_ecg_input(ecg_processor, key, ecg_signal, rpeaks)

    figsize = kwargs.get("figsize", (14, 7))
    title = kwargs.get("title", None)
    plt.rcParams["mathtext.default"] = "regular"

    if ecg_processor is not None:
        ecg_signal = ecg_processor.ecg_result[key]
        rpeaks = ecg_processor.rpeaks[key]
        sampling_rate = ecg_processor.sampling_rate

    # perform R peak correction before computing HRV measures
    rpeaks = EcgProcessor.correct_rpeaks(ecg_signal=ecg_signal, rpeaks=rpeaks, sampling_rate=sampling_rate)

    fig = plt.figure(constrained_layout=False, figsize=figsize)

    if plot_psd:
        spec = gs.GridSpec(ncols=2, nrows=2, height_ratios=[1, 1], width_ratios=[1, 1])
        axs = {
            "dist": fig.add_subplot(spec[0, :-1]),
            "freq": fig.add_subplot(spec[1, :-1]),
        }
    else:
        spec = gs.GridSpec(ncols=2, nrows=1, width_ratios=[1, 1])
        axs = {"dist": fig.add_subplot(spec[0, :-1])}

    spec_within = gs.GridSpecFromSubplotSpec(4, 4, subplot_spec=spec[:, -1], wspace=0.025, hspace=0.05)
    axs["poin"] = fig.add_subplot(spec_within[1:4, 0:3])
    axs["poin_x"] = fig.add_subplot(spec_within[0, 0:3])
    axs["poin_y"] = fig.add_subplot(spec_within[1:4, 3])
    axs["poin"].get_shared_x_axes().join(axs["poin"], axs["poin_x"])
    axs["poin"].get_shared_y_axes().join(axs["poin"], axs["poin_y"])

    if title:
        fig.suptitle("Heart Rate Variability (HRV) – {}".format(title), fontweight="bold")
    else:
        fig.suptitle("Heart Rate Variability (HRV)", fontweight="bold")

    rr_distribution_plot(rpeaks, sampling_rate, ax=axs["dist"])
    hrv_poincare_plot(rpeaks, sampling_rate, axs=[axs["poin"], axs["poin_x"], axs["poin_y"]])
    if plot_psd:
        hrv_frequency_plot(rpeaks, sampling_rate, ax=axs["freq"])

    fig.tight_layout()
    return fig, list(axs.values())


def hr_distribution_plot(heart_rate: pd.DataFrame, **kwargs) -> Tuple[plt.Figure, plt.Axes]:
    """Plot heart rate distribution (histogram).

    This plot is also used as subplot in :func:`~biopsykit.signals.ecg.plotting.ecg_plot`.


    Parameters
    ----------
    heart_rate : pd.DataFrame, optional
        dataframe with heart rate output. Output from `EcgProcessor.ecg_process()`
    kwargs
        Additional parameters to configure the plot. Parameters include:
            * ``figsize``: Figure size
            * ``ax``: Pre-existing axes for the plot. Otherwise, a new figure and axes object are created and returned.


    Returns
    -------
    fig : :class:`matplotlib.figure.Figure`
        figure object
    ax : :class:`matplotlib.axes.Axes`
        axes object

    See Also
    --------
    `ecg_plot`
        plot ECG overview

    """
    ax: plt.Axes = kwargs.get("ax", None)
    figsize = kwargs.get("figsize", (15, 5))
    plt.rcParams["mathtext.default"] = "regular"

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.get_figure()

    ax = sns.histplot(heart_rate, color=colors.fau_color("tech"), ax=ax, kde=True, legend=False)

    ax.set_title("Heart Rate Distribution")
    ax.set_xlabel("Heart Rate [bpm]")
    ax.set_xlim(heart_rate.min().min() - 1, heart_rate.max().max() + 1)
    ax.tick_params(axis="x", which="major", bottom=True, labelbottom=True)

    ax.set_yticks([])
    ax.set_ylabel("")

    fig.tight_layout()
    return fig, ax


def rr_distribution_plot(
    rpeaks: pd.DataFrame, sampling_rate: Optional[int] = 256, **kwargs
) -> Tuple[plt.Figure, plt.Axes]:
    """Plot distribution of RR intervals (histogram) with boxplot and rugplot.

    This plot is also used as subplot in :func:`~biopsykit.signals.ecg.plotting.hrv_plot`.


    Parameters
    ----------
    rpeaks : pd.DataFrame, optional
        dataframe with R peaks. Output of `EcgProcessor.ecg_process()`
    sampling_rate : float, optional
        Sampling rate of recorded data. Default: 256 Hz
    kwargs
        Additional parameters to configure the plot. Parameters include:
            * ``figsize``: Figure size
            * ``ax``: Pre-existing axes for the plot. Otherwise, a new figure and axes object are created and returned.

    Returns
    -------
    fig : :class:`matplotlib.figure.Figure`
        figure object
    ax : :class:`matplotlib.axes.Axes`
        axes object

    See Also
    --------
    `hr_distribution_plot`
        plot heart rate distribution (without boxplot and rugplot)

    """
    ax: plt.Axes = kwargs.get("ax", None)
    figsize = kwargs.get("figsize", (15, 5))
    plt.rcParams["mathtext.default"] = "regular"

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.get_figure()

    rri = _get_rr_intervals(rpeaks, sampling_rate)

    sns.set_palette(colors.fau_palette_blue("box_2"))
    sns.histplot(rri, ax=ax, bins=10, kde=False, alpha=0.5, zorder=1)
    sns.rugplot(rri, ax=ax, lw=1.5, height=0.05, zorder=2)
    ax2 = ax.twinx()
    sns.kdeplot(rri, ax=ax2, lw=2.0, zorder=1)
    ax2.set_ylim(0)
    ax2.axis("off")

    ax.tick_params(axis="both", left=True, bottom=True)
    ax.set_title("Distribution of RR Intervals")
    ax.set_xlabel("RR Intervals [ms]")
    ax.set_ylabel("Count")

    ax2.boxplot(
        rri,
        vert=False,
        positions=[ax2.get_ylim()[-1] / 10 + 0.05 * ax2.get_ylim()[-1]],
        widths=ax2.get_ylim()[-1] / 10,
        manage_ticks=False,
        patch_artist=True,
        boxprops=dict(
            linewidth=2.0,
            color=colors.adjust_color("tech", 0.5),
            facecolor=colors.fau_color("tech"),
        ),
        medianprops=dict(linewidth=2.0, color=colors.adjust_color("tech", 0.5)),
        whiskerprops=dict(linewidth=2.0, color=colors.adjust_color("tech", 0.5)),
        capprops=dict(linewidth=2.0, color=colors.adjust_color("tech", 0.5)),
        zorder=4,
    )

    ax.set_xlim(0.95 * np.min(rri), 1.05 * np.max(rri))

    fig.tight_layout()
    return fig, ax


def individual_beats_plot(
    ecg_signal: pd.DataFrame, rpeaks: Optional[Sequence[int]] = None, sampling_rate: Optional[int] = 256, **kwargs
) -> Tuple[plt.Figure, plt.Axes]:
    """Plot all segmented heart beats overlaid on top of each other.

    This plot is also used as subplot in :func:`~biopsykit.signals.ecg.plotting.ecg_plot`.


    Parameters
    ----------
    ecg_signal : :class:`~biopsykit.utils.datatype_helper.EcgResultDataFrame`, optional
        Dataframe with processed ECG signal. Output from :meth:`~biopsykit.signals.ecg.EcgProcessor.ecg_process()`
    rpeaks : :class:`~biopsykit.utils.datatype_helper.RPeakDataFrame`, optional
        Dataframe with detected R peaks or ``None`` to infer R peaks from ``ecg_signal``. Default: ``None``
    sampling_rate : float, optional
        Sampling rate of recorded data. Default: 256
    kwargs
        Additional parameters to configure the plot. Parameters include:
            * ``figsize``: Figure size
            * ``ax``: Pre-existing axes for the plot. Otherwise, a new figure and axes object are created and returned.


    Returns
    -------
    fig : :class:`matplotlib.figure.Figure`
        figure object
    ax : :class:`matplotlib.axes.Axes`
        axes object


    See Also
    --------
    `ecg_plot`
        plot ECG overview

    """
    ax: plt.Axes = kwargs.get("ax", None)
    figsize = kwargs.get("figsize", (15, 5))
    plt.rcParams["mathtext.default"] = "regular"

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.get_figure()

    if rpeaks is None:
        rpeaks = np.where(ecg_signal["ECG_R_Peaks"] == 1)[0]

    heartbeats = nk.ecg_segment(ecg_signal["ECG_Clean"], rpeaks, sampling_rate)
    heartbeats = nk.epochs_to_df(heartbeats)
    heartbeats_pivoted = heartbeats.pivot(index="Time", columns="Label", values="Signal")

    ax.set_title("Individual Heart Beats")
    ax.margins(x=0)

    # Aesthetics of heart beats
    cmap = iter(plt.cm.YlOrRd(np.linspace(0, 1, num=int(heartbeats["Label"].nunique()))))

    for x, color in zip(heartbeats_pivoted, cmap):
        ax.plot(heartbeats_pivoted[x], color=color)

    ax.set_yticks([])
    ax.tick_params(axis="x", which="major", bottom=True, labelbottom=True)

    fig.tight_layout()
    return fig, ax


# def ecg_plot_artifacts(ecg_signals: pd.DataFrame, sampling_rate: Optional[int] = 256):
#     # TODO not implemented yet
#     # Plot artifacts
#     _, rpeaks = nk.ecg_peaks(ecg_signals["ECG_Clean"], sampling_rate=sampling_rate)
#     _, _ = nk.signal_fixpeaks(rpeaks, sampling_rate=sampling_rate, iterative=True, show=True)


def hrv_poincare_plot(
    rpeaks: pd.DataFrame, sampling_rate: Optional[int] = 256, **kwargs
) -> Tuple[plt.Figure, Sequence[plt.Axes]]:
    """Plot Heart Rate Variability as Poincaré Plot.

    This plot is also used as subplot in :func:`~biopsykit.signals.ecg.plotting.hrv_plot`.


    Parameters
    ----------
    rpeaks : :class:`~biopsykit.utils.datatype_helper.RPeakDataFrame`
            Dataframe with detected R peaks. Output from :meth:`~biopsykit.signals.ecg.EcgProcessor.ecg_process()`
    sampling_rate : float, optional
        Sampling rate of recorded data. Default: 256 Hz
    kwargs
        Additional parameters to configure the plot. Parameters include:
            * ``figsize``: Figure size
            * ``ax``: List of pre-existing axes for the plot. Otherwise, a new figure and list of axes objects are
              created and returned.


    Returns
    -------
    fig : :class:`matplotlib.figure.Figure`
        Figure object
    axs : list of :class:`matplotlib.axes.Axes`
        list of subplot axes objects

    See Also
    --------
    `hrv_plot`
        plot heart rate variability

    """
    axs: List[plt.Axes] = kwargs.get("axs", None)
    figsize = kwargs.get("figsize", (8, 8))
    plt.rcParams["mathtext.default"] = "regular"

    if axs is None:
        fig = plt.figure(figsize=figsize)
        axs = list()
        # Prepare figure
        spec = gs.GridSpec(4, 4)
        axs.append(plt.subplot(spec[1:4, 0:3]))
        axs.append(plt.subplot(spec[0, 0:3]))
        axs.append(plt.subplot(spec[1:4, 3]))
        spec.update(wspace=0.025, hspace=0.05)  # Reduce spaces
    else:
        fig = axs[0].get_figure()

    rri = _get_rr_intervals(rpeaks, sampling_rate)

    mean_rri = float(np.mean(rri))
    sd = np.ediff1d(rri)
    sdsd = np.std(sd, ddof=1)
    sd1 = sdsd / np.sqrt(2)
    sd2 = np.sqrt(2 * np.std(rri, ddof=1) ** 2 - sd1 ** 2)

    area = np.pi * sd1 * sd2

    sns.set_palette(colors.fau_palette_blue("box_2"))
    sns.kdeplot(
        x=rri[:-1],
        y=rri[1:],
        ax=axs[0],
        n_levels=20,
        shade=True,
        thresh=0.05,
        alpha=0.8,
    )
    sns.scatterplot(x=rri[:-1], y=rri[1:], ax=axs[0], alpha=0.5, edgecolor=colors.fau_color("fau"))
    sns.histplot(x=rri[:-1], bins=int(len(rri) / 10), ax=axs[1], edgecolor="none")
    sns.histplot(y=rri[1:], bins=int(len(rri) / 10), ax=axs[2], edgecolor="none")

    ellipse = mpl.patches.Ellipse(
        (mean_rri, mean_rri),
        width=2 * sd2,
        height=2 * sd1,
        angle=45,
        ec=colors.fau_color("fau"),
        fc=colors.adjust_color("fau", 1.5),
        alpha=0.8,
    )
    axs[0].add_artist(ellipse)

    na = 4
    arr_sd1 = axs[0].arrow(
        mean_rri,
        mean_rri,
        -(sd1 - na) * np.cos(np.deg2rad(45)),
        (sd1 - na) * np.cos(np.deg2rad(45)),
        head_width=na,
        head_length=na,
        linewidth=2.0,
        ec=colors.fau_color("phil"),
        fc=colors.fau_color("phil"),
        zorder=4,
    )
    arr_sd2 = axs[0].arrow(
        mean_rri,
        mean_rri,
        (sd2 - na) * np.cos(np.deg2rad(45)),
        (sd2 - na) * np.sin(np.deg2rad(45)),
        head_width=na,
        head_length=na,
        linewidth=2.0,
        ec=colors.fau_color("med"),
        fc=colors.fau_color("med"),
        zorder=4,
    )
    axs[0].add_line(
        mpl.lines.Line2D(
            (np.min(rri), np.max(rri)),
            (np.min(rri), np.max(rri)),
            c=colors.fau_color("med"),
            ls=":",
            lw=2.0,
            alpha=0.8,
        )
    )
    axs[0].add_line(
        mpl.lines.Line2D(
            (
                mean_rri - sd1 * np.cos(np.deg2rad(45)) * na,
                mean_rri + sd1 * np.cos(np.deg2rad(45)) * na,
            ),
            (
                mean_rri + sd1 * np.sin(np.deg2rad(45)) * na,
                mean_rri - sd1 * np.sin(np.deg2rad(45)) * na,
            ),
            c=colors.fau_color("phil"),
            ls=":",
            lw=2.0,
            alpha=0.8,
        )
    )
    # for Area and SD1/SD2 in Legend
    a3 = mpl.patches.Patch(facecolor="white", alpha=0.0)
    a4 = mpl.patches.Patch(facecolor="white", alpha=0.0)

    axs[0].legend(
        [arr_sd1, arr_sd2, a3, a4],
        [
            "SD1: $%.3f ms$" % sd1,
            "SD2: $%.3f ms$" % sd2,
            "S: $%.3f ms^2$" % area,
            "SD1/SD2: %.3f" % (sd1 / sd2),
        ],
        framealpha=1,
        fontsize="small",
    )

    axs[0].set_xlabel(r"$RR_{i}~[ms]$")
    axs[0].set_ylabel(r"$RR_{i+1}~[ms]$")
    axs[0].xaxis.set_major_locator(mticks.MultipleLocator(100))
    axs[0].xaxis.set_minor_locator(mticks.MultipleLocator(25))
    axs[0].yaxis.set_major_locator(mticks.MultipleLocator(100))
    axs[0].yaxis.set_minor_locator(mticks.MultipleLocator(25))
    axs[0].tick_params(axis="both", which="both", left=True, bottom=True)
    axs[0].tick_params(axis="x", labelrotation=30)
    axs[1].axis("off")
    axs[2].axis("off")

    fig.tight_layout()
    return fig, axs


def hrv_frequency_plot(
    rpeaks: pd.DataFrame, sampling_rate: Optional[int] = 256, **kwargs
) -> Tuple[plt.Figure, plt.Axes]:
    """Plot Power Spectral Density (PSD) of RR intervals.

    This plot is also used as subplot in :func:`~biopsykit.signals.ecg.plotting.hrv_plot`.


    Parameters
    ----------
    rpeaks : :class:`~biopsykit.utils.datatype_helper.RPeakDataFrame`
            Dataframe with detected R peaks. Output from :meth:`~biopsykit.signals.ecg.EcgProcessor.ecg_process()`
    sampling_rate : float, optional
        Sampling rate of recorded data. Default: 256 Hz
    kwargs
        Additional parameters to configure the plot. Parameters include:
            * ``figsize``: Figure size
            * ``ax``: Pre-existing axes for the plot. Otherwise, a new figure and axes object are created and returned.


    Returns
    -------
    fig : :class:`matplotlib.figure.Figure`
        figure object
    ax : :class:`matplotlib.axes.Axes`
        axes object


    See Also
    --------
    `hrv_plot`
        plot heart rate variability

    """
    ax: plt.Axes = kwargs.get("ax", None)
    figsize = kwargs.get("figsize", (15, 5))
    plt.rcParams["mathtext.default"] = "regular"

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.get_figure()

    rpeaks = sanitize_input_1d(rpeaks["R_Peak_Idx"])
    rri = _hrv_get_rri(rpeaks, sampling_rate=sampling_rate, interpolate=True)[0]
    hrv = nk.hrv_frequency(rpeaks, sampling_rate)
    out_bands = hrv[["HRV_ULF", "HRV_VLF", "HRV_LF", "HRV_HF", "HRV_VHF"]]
    out_bands.columns = [col.replace("HRV_", "") for col in out_bands.columns]
    _hrv_frequency_show(rri, out_bands, sampling_rate=256, ax=ax)

    ax.set_title("Power Spectral Density (PSD)")
    ax.set_ylabel("Spectrum $[{ms}^2/Hz]$")
    ax.set_xlabel("Frequency [Hz]")

    ax.tick_params(axis="both", left=True, bottom=True)
    ax.margins(x=0)
    ax.set_ylim(0)

    fig.tight_layout()
    return fig, ax


def _get_rr_intervals(rpeaks: pd.DataFrame, sampling_rate: Optional[int] = 256) -> np.array:
    rri = (np.ediff1d(rpeaks["R_Peak_Idx"], to_begin=0) / sampling_rate) * 1000
    rri = rri[1:]
    return rri
