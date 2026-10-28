import logging
import re
import time
from typing import List

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
         'workers.acs_order_master' -> '[ACS_ORDER_MASTER]'
         'worker.acs_order_master.order_master_processor' -> '[ACS_ORDER_MASTER] [ORDER_MASTER_PROCESSOR]'
         'worker.acs_supply_pairing.supply_request_pairing' -> '[ACS_SUPPLY_PAIRING] [SUPPLY_REQUEST_PAIRING]'
         'django.utils.autoreload' -> '[DJANGO] [AUTORELOAD]'
         'django.request' -> '[DJANGO] [REQUEST]'
         'django.server' -> '[DJANGO] [SERVER]'
         'root' -> '[ACS_SYSTEM]'
    """
    clean = raw_name.strip("[]").strip()
    parts: List[str] = [p.strip() for p in clean.split(".") if p.strip()]

    # Remove generic 'worker' or 'workers' prefix
    if parts and parts[0].lower() in ("worker", "workers"):
        parts = parts[1:]

    # For django.utils.autoreload -> simplify to ['DJANGO', 'AUTORELOAD']
    if len(parts) >= 3 and parts[0].lower() == "django" and parts[1].lower() == "utils":
        parts = [parts[0], parts[-1]]

    if not parts or (len(parts) == 1 and parts[0].lower() in ("root", "")):
        return "[ACS_SYSTEM]"

    # Wrap each section in uppercase square brackets
    return " ".join([f"[{p.upper()}]" for p in parts])


class IndustrialLogFormatter(logging.Formatter):
    """
    Custom Logging Formatter directly applied to Python logging handlers.
    Outputs log lines directly as:
    [TIMESTAMP] [LEVEL] [MODULE] [COMPONENT] MESSAGE
    """

    def formatTime(self, record: logging.LogRecord, datefmt: str = None) -> str:
        ct = self.converter(record.created)
        t = time.strftime("%Y-%m-%d %H:%M:%S", ct)
        return f"{t},{int(record.msecs):03d}"

    def format(self, record: logging.LogRecord) -> str:
        record_time = self.formatTime(record)
        transformed_tags = transform_logger_name(record.name)
        level_str = record.levelname
        msg = record.getMessage()

        # Translate any Vietnamese phrases to English
        eng_msg = translate_to_english(msg)

        formatted = f"[{record_time}] [{level_str}] {transformed_tags} {eng_msg}"

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            formatted = f"{formatted}\n{record.exc_text}"
        if record.stack_info:
            formatted = f"{formatted}\n{self.formatStack(record.stack_info)}"

        return formatted
