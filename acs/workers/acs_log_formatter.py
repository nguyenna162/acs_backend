#!/usr/bin/env python
"""
ACS Industrial Log Formatter Worker
Transforms raw system logs into a standardized, separated-bracket uppercase format in 100% English.

Specification requested by user:
Given raw log:
  [2026-10-29 01:08:36,439] [INFO] [worker.acs_order_send.mqtt_send_suborder] Resending VDA5050 order to uagv/v2/SEVT/AMR_001/order (SubOrder: 3a6e7209-0884-421a-96d1-66b1464862c0)

Formatted output:
  [2026-10-29 01:08:36,439] [INFO] [ACS_ORDER_SEND] [MQTT_SEND_SUBORDER] Resending VDA5050 order to uagv/v2/SEVT/AMR_001/order (SubOrder: 3a6e7209-0884-421a-96d1-66b1464862c0)
"""

import os
import sys
import re
import time
import logging
from datetime import datetime
from typing import Optional, List

# Ensure Django environment is configured
if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "acs.settings")
    import django
    django.setup()

from django.conf import settings
from workers.worker_schema_class import WorkerThread
from acs.models import Log

# Path configurations
LOG_DIR = getattr(settings, "LOG_DIR", os.path.join(os.path.dirname(__file__), "..", "logs"))
os.makedirs(LOG_DIR, exist_ok=True)
RAW_LOG_PATH = os.path.join(LOG_DIR, "acs_system.log")
FORMATTED_LOG_PATH = os.path.join(LOG_DIR, "acs_formatted.log")
OFFSET_TRACKER_PATH = os.path.join(LOG_DIR, ".log_formatter_offset")

# Regex to match raw python logging line:
# [2026-10-29 01:08:36,439] [INFO] [worker.acs_order_send.mqtt_send_suborder] Message
LOG_LINE_REGEX = re.compile(
    r"^\[(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,\.]?\d*)\]\s+\[(?P<level>[A-Z]+)\]\s+\[(?P<logger>[\w\.\-]+)\]\s+(?P<message>.*)$"
)

# Vietnamese to English normalizer
VIETNAMESE_TRANSLATIONS = [
    (re.compile(r"Không tìm thấy lộ trình", re.I), "No reachable path found"),
    (re.compile(r"đơn hàng", re.I), "order"),
    (re.compile(r"thành công", re.I), "successfully"),
    (re.compile(r"thất bại", re.I), "failed"),
    (re.compile(r"lỗi", re.I), "error"),
    (re.compile(r"kết nối", re.I), "connection"),
    (re.compile(r"mất kết nối", re.I), "connection lost"),
    (re.compile(r"trạm đệm", re.I), "buffer station"),
    (re.compile(r"điểm đến", re.I), "target node"),
    (re.compile(r"điểm xuất phát", re.I), "source node"),
    (re.compile(r"khởi động", re.I), "starting"),
    (re.compile(r"hoàn thành", re.I), "completed"),
    (re.compile(r"đang chạy", re.I), "running"),
    (re.compile(r"hủy", re.I), "cancelled"),
]


def translate_to_english(text: str) -> str:
    """Normalize any Vietnamese phrases in log messages into English."""
    cleaned = text
    for pattern, replacement in VIETNAMESE_TRANSLATIONS:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned


def transform_logger_name(raw_name: str) -> str:
    """
    Transforms dot-separated logger names into separated uppercase bracketed tags.
    e.g. 'worker.acs_order_send.mqtt_send_suborder' -> '[ACS_ORDER_SEND] [MQTT_SEND_SUBORDER]'
         'worker.acs_order_master.order_master_processor' -> '[ACS_ORDER_MASTER] [ORDER_MASTER_PROCESSOR]'
         'worker.acs_supply_pairing.supply_request_pairing' -> '[ACS_SUPPLY_PAIRING] [SUPPLY_REQUEST_PAIRING]'
         'django.utils.autoreload' -> '[DJANGO] [AUTORELOAD]'
         'django.request' -> '[DJANGO] [REQUEST]'
    """
    clean = raw_name.strip("[]").strip()
    parts: List[str] = [p.strip() for p in clean.split(".") if p.strip()]

    # Remove generic 'worker' or 'workers' prefix
    if parts and parts[0].lower() in ("worker", "workers"):
        parts = parts[1:]

    # For django.utils.autoreload -> simplify to ['DJANGO', 'AUTORELOAD']
    if len(parts) >= 3 and parts[0].lower() == "django" and parts[1].lower() == "utils":
        parts = [parts[0], parts[-1]]

    if not parts:
        return f"[{clean.upper()}]"

    # Wrap each section in uppercase square brackets
    return " ".join([f"[{p.upper()}]" for p in parts])


def format_log_entry(timestamp_str: str, level_str: str, logger_str: str, message_str: str) -> str:
    """
    Combines parsed log segments into the exact user formula:
    [TIMESTAMP] [LEVEL] [MODULE] [COMPONENT] MESSAGE
    """
    transformed_tags = transform_logger_name(logger_str)
    english_message = translate_to_english(message_str.strip())
    return f"[{timestamp_str}] [{level_str}] {transformed_tags} {english_message}"


class IndustrialLogFormatter(logging.Formatter):
    """
    Custom Formatter usable directly with Python's logging module handlers.
    """

    def format(self, record: logging.LogRecord) -> str:
        record_time = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S,%03d") % int(record.msecs)
        msg = record.getMessage()
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
            if record.exc_text:
                exc_summary = record.exc_text.strip().split("\n")[-1]
                msg = f"{msg} | Exception: {exc_summary}"

        return format_log_entry(record_time, record.levelname, record.name, msg)


class LogFormatterWorker(WorkerThread):
    """
    Background worker that continuously watches raw log files (acs_system.log)
    and database Log records, formats them to the standard formula in 100% English,
    and writes them to acs_formatted.log.
    """

    def __init__(
        self,
        thread_name: str = "log_formatter_worker",
        worker_name: str = "acs_log_formatter",
        loop_sleep_s: float = 1.0,
    ):
        super().__init__(thread_name, worker_name, loop_sleep_s)
        self.raw_log_file = RAW_LOG_PATH
        self.formatted_log_file = FORMATTED_LOG_PATH
        self.offset_file = OFFSET_TRACKER_PATH
        self.last_read_offset = self._load_last_offset()
        self.last_db_log_id = 0

    def _load_last_offset(self) -> int:
        if os.path.exists(self.offset_file):
            try:
                with open(self.offset_file, "r", encoding="utf-8") as f:
                    return int(f.read().strip())
            except Exception:
                return 0
        return 0

    def _save_last_offset(self, offset: int):
        self.last_read_offset = offset
        try:
            with open(self.offset_file, "w", encoding="utf-8") as f:
                f.write(str(offset))
        except Exception:
            pass

    def reformat_entire_history(self):
        """Re-formats the entire raw log file from beginning to create formatted log."""
        if not os.path.exists(self.raw_log_file):
            return 0

        self.logger.info("Re-formatting entire raw system log into standard English formula...")
        count = 0
        with open(self.raw_log_file, "r", encoding="utf-8", errors="ignore") as in_f:
            with open(self.formatted_log_file, "w", encoding="utf-8") as out_f:
                for line in in_f:
                    formatted = self._parse_and_format_line(line)
                    if formatted:
                        out_f.write(formatted + "\n")
                        count += 1
                self._save_last_offset(in_f.tell())

        self.logger.info(f"Re-formatting complete: {count} entries written to {self.formatted_log_file}")
        return count

    def _parse_and_format_line(self, raw_line: str) -> Optional[str]:
        """
        Parse raw Python logging line:
        [2026-10-29 01:08:36,439] [INFO] [worker.acs_order_send.mqtt_send_suborder] Message
        """
        line = raw_line.strip()
        if not line:
            return None

        # Filter out raw multi-line Python traceback clutter
        if (
            line.startswith("File \"")
            or line.startswith("Traceback (most")
            or line.startswith("~")
            or line.startswith("^")
            or line.startswith("self.")
            or line.startswith("timeout_threshold =")
            or line.startswith("AttributeError:")
        ):
            return None

        match = LOG_LINE_REGEX.match(line)
        if match:
            ts = match.group("timestamp")
            lvl = match.group("level")
            logger_name = match.group("logger")
            msg = match.group("message")
            return format_log_entry(ts, lvl, logger_name, msg)

        return None

    def task(self):
        """Continuous execution loop to tail and re-format logs."""
        # 1. Process new raw file lines
        if os.path.exists(self.raw_log_file):
            file_size = os.path.getsize(self.raw_log_file)
            if file_size < self.last_read_offset:
                self.last_read_offset = 0

            if file_size > self.last_read_offset:
                new_formatted_lines = []
                with open(self.raw_log_file, "r", encoding="utf-8", errors="ignore") as f:
                    f.seek(self.last_read_offset)
                    for line in f:
                        formatted = self._parse_and_format_line(line)
                        if formatted:
                            new_formatted_lines.append(formatted)
                    self._save_last_offset(f.tell())

                if new_formatted_lines:
                    with open(self.formatted_log_file, "a", encoding="utf-8") as out_f:
                        for fl in new_formatted_lines:
                            out_f.write(fl + "\n")

        # 2. Reformat and English-normalize any new database Log entries
        new_db_logs = Log.objects.filter(id__gt=self.last_db_log_id).order_by("id")[:50]
        for db_log in new_db_logs:
            self.last_db_log_id = db_log.id
            eng_msg = translate_to_english(db_log.message)
            if eng_msg != db_log.message:
                db_log.message = eng_msg
                db_log.save(update_fields=["message"])


def main():
    print("================================================================")
    print("   ACS INDUSTRIAL LOG FORMATTER WORKER                         ")
    print("   Separating tags to uppercase brackets: [MODULE] [COMPONENT] ")
    print("================================================================")

    worker = LogFormatterWorker()
    if not os.path.exists(FORMATTED_LOG_PATH) or os.path.getsize(FORMATTED_LOG_PATH) == 0:
        worker.reformat_entire_history()

    worker.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        worker.stop()
        worker.join(timeout=3)
        print("Log Formatter Worker stopped cleanly.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--reformat-all":
        worker = LogFormatterWorker()
        worker.reformat_entire_history()
    else:
        main()
