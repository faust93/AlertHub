import threading
import queue
import time
import json
import logging
from functools import wraps
from datetime import datetime
from zoneinfo import ZoneInfo
from utils.alert_dsl import AlertDSL
import config

TZ = ZoneInfo(config.TZ)

CACHE_TIMEOUT = 15
def ttl_cache(seconds):
    def decorator(func):
        cache = {}
        lock = threading.Lock()

        @wraps(func)
        def wrapper(*args, **kwargs):
            if len(args) > 0 and hasattr(args[0], '__class__'):
                cache_args = args[1:]
            else:
                cache_args = args
            key = str(cache_args) + str(sorted(kwargs.items()))
            with lock:
                if key in cache:
                    result, timestamp = cache[key]
                    if time.time() - timestamp < seconds:
                        logging.debug(f"Cache hit for {func}")
                        return result
            result = func(*args, **kwargs)
            with lock:
                cache[key] = (result, time.time())
            return result
        wrapper.clear_cache = lambda: cache.clear()
        return wrapper
    return decorator

class AlertPipeline:
    def __init__(self, db_handler, num_workers=10):
        self.db = db_handler
        self.num_workers = num_workers
        self.threads = []
        self.thread_timeout = 20
        self.task_queue = queue.Queue()

    def start(self):
        for _ in range(self.num_workers):
            t = threading.Thread(target=self.worker, daemon=True)
            t.start()
            self.threads.append(t)

    def stop(self):
        for _ in range(self.num_workers):
            self.task_queue.put(None)
        self.task_queue.join()
        for t in self.threads:
            t.join(self.thread_timeout)

    def add_task(self, task_id, param):
        self.task_queue.put((task_id, param))

    def worker(self):
        while True:
            task = self.task_queue.get()
            if task is None:
                self.task_queue.task_done()
                break
            elif task[0] == "alert":
                logging.info("Spawning alert dsl pipeline..")
                self.alert_pipeline(task[1])
                self.task_queue.task_done()
            else:
                logging.warning("Unknown task id")
                self.task_queue.task_done()

    def alert_pipeline(self, alert):
        # logging.debug(f"alert_pipeline: {alert}")
        schedules = self.get_matching_schedules()
        maintenance = []
        if len(schedules) > 0:
            maintenance = self.get_matching_maintenance()
        for sch in schedules:
            p_id = sch.get("pipeline_id", None)
            s_name = sch.get("name", None)
            if not p_id or not s_name:
                continue
            p_name, p_yaml = self.get_yaml_pipeline(p_id)
            logging.info(f"Pipeline name: {p_name}, Schedule: {s_name}")
            # logging.debug("YAML: %s", p_yaml)
            dsl = AlertDSL(self.db, alert, sch, maintenance)
            if dsl is None:
                logging.error("Pipeline YAML parser error")
                continue
            ctx = dsl.run_dsl(p_yaml)
            # logging.debug(ctx)

    @ttl_cache(CACHE_TIMEOUT)
    def get_yaml_pipeline(self, pid):
        row = self.db.getPipeline(pid)
        if not row:
            return "", "---"
        name = row[1] or ""
        yaml = row[3] or "---"
        return name, yaml

    @ttl_cache(CACHE_TIMEOUT)
    def get_matching_schedules(self):
        rows = self.db.getMatchingSchedules()
        scheds = []
        if rows is None:
            return []
        for s in rows:
            scheds.append({
                "name": s[1],
                "group": s[2],
                "group_id": s[3],
                "starts_at": datetime.fromtimestamp(s[4], tz=TZ).isoformat(),
                "ends_at": datetime.fromtimestamp(s[5], tz=TZ).isoformat(),
                "mute_starts": s[6],
                "mute_ends": s[7],
                "people": s[8],
                "pipeline_id": s[9]
            })
        return scheds

    @ttl_cache(CACHE_TIMEOUT)
    def get_matching_maintenance(self):
        rows = self.db.getMatchingMaintenance()
        if rows is None:
            return []
        maint = [
            {
                "name": r[1],
                "description": r[2],
                "filter": r[3],
                "oncall_groups": r[4],
                "starts_at": datetime.fromtimestamp(r[5], tz=TZ).isoformat(),
                "ends_at": datetime.fromtimestamp(r[6], tz=TZ).isoformat()
            }
            for r in rows
        ]
        return maint