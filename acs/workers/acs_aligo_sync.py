import os
import sys
import time
import logging
from datetime import datetime, timezone, timedelta
import django

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "acs.settings")
    django.setup()

from acs.models import SupplyRequest
from buffer.models import Buffer
from integrations.aligo_client import default_aligo_client
from workers.worker_schema_class import WorkerThread

logger = logging.getLogger("workers.acs_aligo_sync")


class AligoSyncWorker(WorkerThread):
    """Syncs robot and CNC production line state with Aligo MES every 3-5 seconds."""

    def __init__(self, thread_name="aligo_sync_worker", worker_name="acs_aligo_sync", loop_sleep_s=4.0):
        super().__init__(thread_name, worker_name, loop_sleep_s)
        self.client = default_aligo_client

    def task(self):
        # 1. Poll CNC line status
        line_data = self.client.get_line_status("CNC_2G")
        if line_data:
            self.logger.debug(f"Synced Aligo CNC 2G status: {line_data.get('status')}")

        # 2. Ingest pending supply commands
        commands = self.client.fetch_supply_commands()
        for cmd in commands:
            cmd_id = cmd.get("command_id")
            line_id = cmd.get("line_id", "CNC_2G")
            buffer_rssid = cmd.get("buffer_rssid")
            material_id = cmd.get("material_id", "MAT_RAW_01")
            priority = int(cmd.get("priority", 5))

            # Match buffer
            buffer_obj = Buffer.objects.filter(rssid=buffer_rssid).first()
            if not buffer_obj:
                buffer_obj = Buffer.objects.first()

            if buffer_obj:
                # Create SupplyRequest if not already existing
                sla_minutes = int(cmd.get("sla_minutes", 15))
                sla_time = datetime.now(timezone.utc) + timedelta(minutes=sla_minutes)

                SupplyRequest.objects.get_or_create(
                    line_id=line_id,
                    buffer=buffer_obj,
                    material_id=material_id,
                    defaults={
                        "priority": priority,
                        "sla_deadline": sla_time,
                        "status": SupplyRequest.Status.PENDING,
                    },
                )
                self.logger.info(f"Ingested Supply Command {cmd_id} for Line {line_id}")


def main():
    worker = AligoSyncWorker()
    worker.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        worker.stop()
        worker.join(timeout=3)


if __name__ == "__main__":
    main()
