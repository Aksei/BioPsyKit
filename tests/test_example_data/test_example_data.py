from contextlib import contextmanager
from pathlib import Path

import pandas as pd
import pytest

from biopsykit.example_data import *
from biopsykit.example_data import get_eeg_example, get_questionnaire_example_wrong_range
from biopsykit.questionnaires import pss
from biopsykit.questionnaires.utils import find_cols
from biopsykit.utils._datatype_validation_helper import _assert_is_dtype, _assert_has_columns, _assert_has_index_levels
from biopsykit.utils.datatype_helper import (
    is_subject_condition_dataframe,
    is_saliva_raw_dataframe,
    is_saliva_mean_se_dataframe,
    is_hr_phase_dict,
    is_sleep_endpoint_dataframe,
    is_imu_dataframe,
    is_ecg_raw_dataframe,
    is_hr_subject_data_dict,
)
from biopsykit.utils.exceptions import ValueRangeError


@contextmanager
def does_not_raise():
    yield


# TODO add new Test Class with pre-and post-test hook that allows to test example data downloading
#  (by modifying example_data.__init__() so that it can't be found anymore, pretending the package wasn't installed
#  manually and data is downloaded from remote)


class TestExampleData:
    @pytest.mark.parametrize(
        "file_path, expected",
        [
            ("condition_list.csv", does_not_raise()),
            ("test.csv", pytest.raises(ValueError)),
        ],
    )
    def test_get_file_path_raises(self, file_path, expected):
        with expected:
            get_file_path(file_path)

    @pytest.mark.parametrize(
        "file_path",
        [
            "condition_list.csv",
        ],
    )
    def test_get_file_path(self, file_path):
        file_path = get_file_path(file_path)
        _assert_is_dtype(file_path, Path)

    def test_get_condition_list_example(self):
        data = get_condition_list_example()
        is_subject_condition_dataframe(data)

    @pytest.mark.parametrize(
        "sample_times, expected",
        [
            (None, does_not_raise()),
            ([-30, -1, 0, 10, 20, 30, 40], does_not_raise()),
            ([], pytest.raises(ValueError)),
            ([-30, -1, 0, 10, 20, 30, 40, 50], pytest.raises(ValueError)),
        ],
    )
    def test_get_saliva_example_raises(self, sample_times, expected):
        with expected:
            get_saliva_example(sample_times)

    def test_get_saliva_example(self):
        data = get_saliva_example()
        is_saliva_raw_dataframe(data, "cortisol")

    def test_get_saliva_example_plate_format(self):
        data = get_saliva_example_plate_format()
        _assert_is_dtype(data, pd.DataFrame)

    def test_get_saliva_mean_se_example(self):
        data = get_saliva_mean_se_example()
        _assert_is_dtype(data, dict)
        for key, df in data.items():
            assert key in ["cortisol", "amylase", "il6"]
            is_saliva_mean_se_dataframe(df)

    def test_get_hr_result_sample(self):
        data = get_hr_result_sample()
        _assert_is_dtype(data, pd.DataFrame)
        _assert_has_columns(data, [["HR"]])

    def test_get_hr_ensemble_sample(self):
        data = get_hr_ensemble_sample()
        _assert_is_dtype(data, dict)
        for key, df in data.items():
            _assert_is_dtype(key, str)
            _assert_is_dtype(df, pd.DataFrame)

    def test_get_mist_hr_example(self):
        data = get_mist_hr_example()
        is_hr_phase_dict(data)

    def test_get_hr_subject_data_dict_example(self):
        data = get_hr_subject_data_dict_example()
        is_hr_subject_data_dict(data)

    def test_get_ecg_path_example(self):
        path = get_ecg_path_example()
        assert path.exists()

    def test_get_car_watch_log_path_example(self):
        path = get_car_watch_log_path_example()
        assert path.exists()

    def test_get_car_watch_log_data_zip_path_example(self):
        path = get_car_watch_log_data_zip_path_example()
        assert path.exists()

    def test_get_car_watch_log_path_all_subjects_example(self):
        path = get_car_watch_log_path_all_subjects_example()
        assert path.exists()

    def test_get_ecg_example(self):
        data, fs = get_ecg_example()
        _assert_is_dtype(data, pd.DataFrame)
        _assert_has_columns(data, [["ecg"]])
        assert fs == 256.0

    def test_get_ecg_example_02(self):
        data, fs = get_ecg_example_02()
        is_ecg_raw_dataframe(data)
        assert fs == 256.0

    def test_get_ecg_processing_results_path_example(self):
        path = get_ecg_processing_results_path_example()
        assert path.exists()

    @pytest.mark.parametrize(
        "data_source, expected",
        [
            ("heart_rate", does_not_raise()),
            ("respiration_rate", does_not_raise()),
            ("sleep_state", does_not_raise()),
            ("snoring", does_not_raise()),
            ("data", pytest.raises(ValueError)),
        ],
    )
    def test_get_sleep_analyzer_raw_file_unformatted_raises(self, data_source, expected):
        with expected:
            get_sleep_analyzer_raw_file_unformatted(data_source)

    @pytest.mark.parametrize(
        "data_source",
        ["heart_rate", "respiration_rate", "sleep_state", "snoring"],
    )
    def test_get_sleep_analyzer_raw_file_unformatted(self, data_source):
        data = get_sleep_analyzer_raw_file_unformatted(data_source)
        _assert_is_dtype(data, pd.DataFrame)
        _assert_has_columns(data, [["start", "duration"]])

    @pytest.mark.parametrize(
        "data_source, expected",
        [
            ("heart_rate", does_not_raise()),
            ("respiration_rate", does_not_raise()),
            ("sleep_state", does_not_raise()),
            ("snoring", does_not_raise()),
            ("data", pytest.raises(ValueError)),
        ],
    )
    def test_get_sleep_analyzer_raw_file_raises(self, data_source, expected):
        with expected:
            get_sleep_analyzer_raw_file(data_source)

    @pytest.mark.parametrize(
        "data_source",
        ["heart_rate", "respiration_rate", "sleep_state", "snoring"],
    )
    def test_get_sleep_analyzer_raw_file(self, data_source):
        data = get_sleep_analyzer_raw_file(data_source)
        _assert_is_dtype(data, dict)
        for key, df in data.items():
            _assert_is_dtype(key, str)
            _assert_is_dtype(df, pd.DataFrame)
            _assert_has_columns(df, [[data_source]])
            _assert_has_index_levels(df, ["time"])

    @pytest.mark.parametrize(
        "split_into_nights",
        [True, False],
    )
    def test_get_sleep_analyzer_raw_example(self, split_into_nights):
        data = get_sleep_analyzer_raw_example(split_into_nights)
        if split_into_nights:
            _assert_is_dtype(data, dict)
            for key, val in data.items():
                _assert_is_dtype(key, str)
                _assert_is_dtype(val, pd.DataFrame)
        else:
            _assert_is_dtype(data, pd.DataFrame)

    def test_get_sleep_analyzer_summary_example(self):
        data = get_sleep_analyzer_summary_example()
        is_sleep_endpoint_dataframe(data)

    def test_get_sleep_imu_example(self):
        data, fs = get_sleep_imu_example()
        is_imu_dataframe(data)
        assert fs == 204.8

    def test_get_eeg_example(self):
        data, fs = get_eeg_example()
        _assert_is_dtype(data, pd.DataFrame)
        assert fs == 250.0

    def test_get_car_watch_log_data_example(self):
        data = get_car_watch_log_data_example()
        _assert_is_dtype(data, pd.DataFrame)

    def test_get_time_log_example(self):
        data = get_time_log_example()
        _assert_is_dtype(data, pd.DataFrame)

    def test_get_questionnaire_example(self):
        data = get_questionnaire_example()
        _assert_is_dtype(data, pd.DataFrame)
        # this should throw no error
        pss(find_cols(data, starts_with="PSS")[0])

    def test_get_questionnaire_example_wrong_range(self):
        data = get_questionnaire_example_wrong_range()
        _assert_is_dtype(data, pd.DataFrame)
        # this should throw an error because the PSS values have the wrong value range
        with pytest.raises(ValueRangeError):
            pss(find_cols(data, starts_with="PSS")[0])

    def test_get_stats_example(self):
        data = get_stats_example()
        _assert_is_dtype(data, pd.DataFrame)
