"""List of all log data actions available in the CARWatch App."""
app_metadata: str = "app_metadata"
phone_metadata: str = "phone_metadata"
subject_id_set: str = "subject_id_set"
alarm_set: str = "alarm_set"
timer_set: str = "timer_set"
alarm_cancel: str = "alarm_cancel"
alarm_ring: str = "alarm_ring"
alarm_snooze: str = "alarm_snooze"
alarm_stop: str = "alarm_stop"
alarm_killall: str = "alarm_killall"
evening_salivette: str = "evening_salivette"
barcode_scan_init: str = "barcode_scan_init"
barcode_scanned: str = "barcode_scanned"
invalid_barcode_scanned: str = "invalid_barcode_scanned"
duplicate_barcode_scanned: str = "duplicate_barcode_scanned"
spontaneous_awakening: str = "spontaneous_awakening"
lights_out: str = "lights_out"
day_finished: str = "day_finished"
service_started: str = "service_started"
service_stopped: str = "service_stopped"
screen_off: str = "screen_off"
screen_on: str = "screen_on"
user_present: str = "user_present"
phone_boot_init: str = "phone_boot_init"
phone_boot_complete: str = "phone_boot_complete"

# TODO add further log actions
