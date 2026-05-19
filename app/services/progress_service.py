import time
from threading import Lock

TASKS = {}
_LOCK = Lock()

def create_task(task_id: str):
    with _LOCK:
        TASKS[task_id] = {
            "progress": 0,
            "message": "분석 준비 중",
            "start_time": time.time(),
            "eta": "-",
            "status": "running",
            "result_url": None,
            "result": None,
        }

def update_task(task_id: str, progress: int, message: str):
    with _LOCK:
        task = TASKS.get(task_id)
        if not task:
            return

        progress = max(0, min(100, int(progress)))
        elapsed = time.time() - task["start_time"]

        if progress > 0:
            total_estimated = elapsed / (progress / 100)
            remain = max(0, int(total_estimated - elapsed))
            if remain >= 60:
                task["eta"] = f"{remain // 60}분 {remain % 60}초"
            else:
                task["eta"] = f"{remain}초"
        else:
            task["eta"] = "-"

        task["progress"] = progress
        task["message"] = message

def finish_task(task_id: str, result_url: str):
    with _LOCK:
        task = TASKS.get(task_id)
        if not task:
            return

        task["progress"] = 100
        task["message"] = "분석 완료"
        task["eta"] = "0초"
        task["status"] = "done"
        task["result_url"] = result_url

def fail_task(task_id: str, message: str):
    with _LOCK:
        task = TASKS.get(task_id)
        if not task:
            return

        task["status"] = "error"
        task["message"] = message
        task["eta"] = "-"
