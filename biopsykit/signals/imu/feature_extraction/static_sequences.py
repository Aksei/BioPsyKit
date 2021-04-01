from typing import Optional, Union

import pandas as pd
import numpy as np
from biopsykit.signals.imu.static_moment_detection import find_static_sequences
from scipy.stats import skew

from biopsykit.utils.array_handling import sanitize_input_nd, sanitize_sliding_window_input


def static_sequence_features(
        data: pd.DataFrame,
        static_sequences: pd.DataFrame,
        start: Optional[Union[str, pd.Timestamp]] = None,
        end: Optional[Union[str, pd.Timestamp]] = None,
        index: Optional[Union[int, str]] = None):

    if data.empty:
        return None

    if start is None:
        start = data.index[0]
    if end is None:
        end = data.index[-1]

    if isinstance(start, str):
        start = pd.Timestamp(start, tz="Europe/Berlin")
    if isinstance(end, str):
        end = pd.Timestamp(end, tz="Europe/Berlin")

    total_time = (end - start)

    static_sequences = sanitize_input_nd(static_sequences, ncols=2)

    durations = np.array([get_sequence_duration(data, sequence) for sequence in static_sequences])
    durations_60 = durations[durations >= 60]

    loc_max_sequence = data.index[static_sequences[np.argmax(durations)][0]]
    loc_max_sequence_relative = (loc_max_sequence - start) / total_time

    feature_dict = {}
    feature_dict['ss_max_position'] = loc_max_sequence_relative
    # feature_dict['sleep_bouts_number'.format(index)] = len(sleep_bouts)
    # feature_dict['wake_bouts_number'] = len(wake_bouts)

    # mean_orientations = get_mean_orientation_in_static_sequences(data, static_sequences)
    # dominant_orientation = mean_orientations.iloc[mean_orientations.index.argmax()]
    # dict_ori = {'ss_dominant_orientation_{}'.format(x): dominant_orientation.loc['acc_{}'.format(x)] for x
    #             in
    #             ['x', 'y', 'z']}
    # feature_dict.update(dict_ori)

    for dur, suffix in zip([durations, durations_60], ['', '_60']):
        feature_dict['ss_number{}'.format(suffix)] = len(dur)
        feature_dict['ss_max{}'.format(suffix)] = np.max(dur)
        feature_dict['ss_median{}'.format(suffix)] = np.median(dur)
        feature_dict['ss_mean{}'.format(suffix)] = np.mean(dur)
        feature_dict['ss_std{}'.format(suffix)] = np.std(dur, ddof=1)
        feature_dict['ss_skewness{}'.format(suffix)] = skew(dur)

    if index is None:
        index = [0]
    features = pd.DataFrame(feature_dict, index=[index])

    return features


def get_sequence_duration(data: pd.DataFrame, start_end: np.array) -> float:
    return (data.index[start_end[1]] - data.index[start_end[0]]).total_seconds()


def get_mean_orientation_in_static_sequences(data: pd.DataFrame, static_sequences: pd.DataFrame) -> np.array:
    static_sequences = sanitize_input_nd(static_sequences, 2)
    mean_orientations = [data.iloc[start_end[0]:start_end[1]] for start_end in static_sequences]
    mean_orientations = {len(data): data.mean() for data in mean_orientations}
    mean_orientations = pd.DataFrame(mean_orientations).T
    # mean_orientations.rename(columns={'index': 'length'}, inplace=True)
    return mean_orientations


def get_static_sequences(
        data: pd.DataFrame,
        threshold: float,
        window_samples: Optional[int] = None,
        window_sec: Optional[int] = None,
        sampling_rate: Optional[Union[int, float]] = 0,
        overlap_samples: Optional[int] = None,
        overlap_percent: Optional[float] = None,
) -> pd.DataFrame:
    # compute the data_norm of the variance in the windows
    window, overlap = sanitize_sliding_window_input(
        window_samples=window_samples, window_sec=window_sec,
        sampling_rate=sampling_rate, overlap_samples=overlap_samples, overlap_percent=overlap_percent
    )
    if data.empty:
        start_end = np.zeros(shape=(0,2))
    else:
        start_end = find_static_sequences(data, window_length=window, overlap=overlap, inactive_signal_th=threshold,
                                          metric='variance')
        if start_end[-1, -1] >= len(data):
            # fix: handle edge case manually
            start_end[-1, -1] = len(data) - 1
    return pd.DataFrame(start_end, columns=['start', 'end'])