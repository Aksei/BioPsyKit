import json
import warnings
from typing import Dict, Sequence, Optional, Union

import numpy as np
import pandas as pd

from datetime import datetime

import biopsykit.log_data.log_actions as log_actions
import biopsykit.log_data.log_extras as log_extras
from biopsykit.utils import tz

subject_conditions: Dict[str, str] = {
    'UNDEFINED': "Undefined",
    'KNOWN_ALARM': "Known Alarm",
    'UNKNOWN_ALARM': "Unknown Alarm",
    'SPONTANEOUS': "Spontaneous Awakening"
}

smartphone_models: Dict[str, str] = {
    'Nexus 7': "Google Nexus 7",
    'HTC 10': "HTC 10",
    'ALE-L21': "Huawei P8 Lite",
    'VTR-L29': "Huawei P10",
    'VOG-L29': "Huawei P30 Pro",
    'FIG-LX1': "Huawei P Smart",
    'MEDION S5004': "MEDION S5004",
    'Moto G (4)': "Motorola Moto G4",
    'Moto G (5)': "Motorola Moto G5",
    'ONEPLUS A6013': "OnePlus 6T",
    'Redmi Note 7': "Redmi Note 7",
    'SM-G920F': "Samsung Galaxy S6",
    'SM-G930F': "Samsung Galaxy S7",
    'SM-G950F': "Samsung Galaxy S8",
    'SM-G973F': "Samsung Galaxy S10",
    'SM-G970F': "Samsung Galaxy S10e",
    'SM-A750FN': "Samsung Galaxy A7",
    'SM-A205F': "Samsung Galaxy A20",
    'SM-A520F': "Samsung Galaxy A5",
    'SM-A500FU': "Samsung Galaxy A5",
    'Mi A1': "Xiaomi Mi A1"
}


class LogDataInfo:

    def __init__(self, subject_id: str, condition: str, log_days: Optional[Sequence[datetime]] = None):
        self.subject_id: str = subject_id
        self.condition: str = condition
        if log_days is None:
            log_days = []
        self.log_days: Sequence[datetime] = log_days

        self.app_metadata: Dict[str, Union[int, str]] = {
            log_extras.app_version_code: 10000,
            log_extras.app_version_name: "1.0.0"
        }
        self.phone_metadata: Dict[str, str] = {
            log_extras.brand: "",
            log_extras.manufacturer: "",
            log_extras.model: "",
            log_extras.version_sdk_level: 0,
            log_extras.version_security_patch: "",
            log_extras.version_release: ""
        }

    @property
    def app_version_code(self) -> int:
        return self.app_metadata[log_extras.app_version_code]

    @property
    def app_version_name(self) -> str:
        return self.app_metadata[log_extras.app_version_name]

    @property
    def model(self) -> str:
        return self.phone_metadata[log_extras.model] if self.phone_metadata else "n/a"

    @property
    def manufacturer(self) -> str:
        return self.phone_metadata[log_extras.manufacturer] if self.phone_metadata else "n/a"

    @property
    def android_version(self) -> int:
        return self.phone_metadata[log_extras.version_sdk_level] if self.phone_metadata else 0


class LogData:
    log_actions: Dict[str, Sequence[str]] = {
        log_actions.app_metadata: [log_extras.app_version_code, log_extras.app_version_name],
        log_actions.phone_metadata: [log_extras.brand, log_extras.manufacturer, log_extras.model,
                                     log_extras.version_sdk_level, log_extras.version_security_patch,
                                     log_extras.version_release],
        log_actions.subject_id_set: [log_extras.subject_id, log_extras.subject_condition],
        log_actions.alarm_set: [log_extras.alarm_id, log_extras.timestamp, log_extras.is_repeating,
                                log_extras.is_hidden, log_extras.hidden_timestamp],
        log_actions.timer_set: [log_extras.alarm_id, log_extras.timestamp],
        log_actions.alarm_cancel: [log_extras.alarm_id],
        log_actions.alarm_ring: [log_extras.alarm_id, log_extras.saliva_id],
        log_actions.alarm_snooze: [log_extras.alarm_id, log_extras.snooze_duration, log_extras.source],
        log_actions.alarm_stop: [log_extras.alarm_id, log_extras.source, log_extras.saliva_id],
        log_actions.alarm_killall: [],
        log_actions.evening_salivette: [log_extras.alarm_id],
        log_actions.barcode_scan_init: [],
        log_actions.barcode_scanned: [log_extras.alarm_id, log_extras.saliva_id, log_extras.barcode_value],
        log_actions.invalid_barcode_scanned: [log_extras.barcode_value],
        log_actions.duplicate_barcode_scanned: [log_extras.barcode_value, log_extras.other_barcodes],
        log_actions.spontaneous_awakening: [log_extras.alarm_id],
        log_actions.lights_out: [],
        log_actions.day_finished: [log_extras.day_counter],
        log_actions.service_started: [],
        log_actions.service_stopped: [],
        log_actions.screen_off: [],
        log_actions.screen_on: [],
        log_actions.user_present: [],
        log_actions.phone_boot_init: [],
        log_actions.phone_boot_complete: []
    }

    def __init__(self, df: pd.DataFrame, error_handling: Optional[str] = 'ignore'):
        self.df: pd.DataFrame = df
        self.error_handling: str = error_handling
        self.selected_day = None
        self.selected_action = None
        self.info: LogDataInfo = self.extract_info()

    def extract_info(self) -> LogDataInfo:
        # Subject Information
        subject_dict = get_extras(self, log_actions.subject_id_set)
        subject_id: str = ""
        condition: str = subject_conditions['UNDEFINED']

        if subject_dict:
            subject_id = subject_dict[log_extras.subject_id]

            condition_str = subject_dict[log_extras.subject_condition]
            if condition_str in subject_conditions:
                condition = subject_conditions[condition_str]
            else:
                condition = subject_conditions['UNDEFINED']
        elif self.error_handling == 'warn':
            warnings.warn("Action 'Subject ID Set' not found – Log Data may be invalid!")

        # App Metadata
        app_dict = get_extras(self, log_actions.app_metadata)
        # Phone Metadata
        phone_dict = get_extras(self, log_actions.phone_metadata)
        if log_extras.model in phone_dict and phone_dict[log_extras.model] in smartphone_models:
            phone_dict[log_extras.model] = smartphone_models[phone_dict[log_extras.model]]

        # Log Info
        # print(self.df.index)
        log_days = np.array([ts.date() for ts in self.df.index.normalize().unique()])
        log_info = LogDataInfo(subject_id, condition, log_days)
        log_info.log_days = log_days
        log_info.phone_metadata = phone_dict
        if app_dict:
            log_info.app_metadata = app_dict
        return log_info

    @property
    def subject_id(self) -> str:
        return self.info.subject_id

    @property
    def condition(self) -> str:
        return self.info.condition

    @property
    def android_version(self) -> int:
        return self.info.android_version

    @property
    def app_version(self) -> str:
        return self.info.app_version_name.split('_')[0]

    @property
    def manufacturer(self) -> str:
        return self.info.manufacturer

    @property
    def model(self) -> str:
        return self.info.model

    @property
    def finished_days(self) -> Sequence[datetime.date]:
        return get_action(self, log_actions.day_finished).index

    @property
    def num_finished_days(self) -> int:
        return len(self.finished_days)

    @property
    def log_dates(self) -> Sequence[datetime.date]:
        return self.info.log_days

    @property
    def start_date(self) -> datetime.date:
        if self.log_dates and len(self.log_dates) > 0:
            return self.log_dates[0]
        return None

    @property
    def end_date(self) -> datetime.date:
        if self.log_dates and len(self.log_dates) > 0:
            return self.log_dates[-1]
        return None


def filtered_logs(log_data: 'LogData') -> pd.DataFrame:
    return get_action(log_data, log_action=log_data.selected_action, selected_day=log_data.selected_day)


def get_logs_for_date(log_data: Union['LogData', pd.DataFrame], date: Union[str, datetime.date]) -> pd.DataFrame:
    if isinstance(log_data, pd.DataFrame):
        df = log_data
    else:
        df = log_data.df

    date = pd.Timestamp(date).tz_localize(tz)

    if date is pd.NaT:
        return df

    return df.loc[df.index.normalize() == date]


def split_nights(log_data: Union['LogData', pd.DataFrame], diff_hours: Optional[int] = 12) -> Sequence[pd.DataFrame]:
    if isinstance(log_data, pd.DataFrame):
        df = log_data
    else:
        df = log_data.df

    idx_split = np.where(np.diff(df.index, prepend=df.index[0]) > pd.Timedelta(diff_hours, 'hours'))[0]
    list_nights = np.split(df, idx_split)
    return list_nights


def get_action(log_data: Union['LogData', pd.DataFrame], log_action: str,
               selected_day: Optional[datetime] = None,
               rows: Optional[Union[str, int, Sequence[int]]] = None) -> Union[pd.DataFrame, pd.Series]:
    if isinstance(log_data, pd.DataFrame):
        df = log_data
    else:
        df = log_data.df

    if selected_day is not None:
        df = get_logs_for_date(df, date=selected_day)

    if log_action is None:
        return df
    elif log_action not in LogData.log_actions:
        return pd.DataFrame()

    if rows:
        actions = df[df['action'] == log_action].iloc[rows, :]
    else:
        actions = df[df['action'] == log_action]
    return actions


def get_extras(log_data: Union['LogData', pd.DataFrame], log_action: str) -> Dict[str, str]:
    row = get_action(log_data, log_action, rows=0)
    if row.empty:
        # warnings.warn("Log file has no action {}!".format(log_action))
        return {}

    return json.loads(row['extras'].iloc[0])
