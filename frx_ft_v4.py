import multiprocessing as mp
import queue
import sys
import time

from fr1_scheduler import schedule_tasks
from fr2_checksum import checksum

REPS = 1_000_000

SCHEDULE_TASKS_MAX_SECONDS = 0.08
CHECKSUM_MAX_SECONDS = 0.08


def _worker_loop(task_queue: mp.Queue, result_queue: mp.Queue) -> None:
    while True:
        task = task_queue.get()
        if task is None:
            return

        task_id, func, args, kwargs = task
        try:
            result_queue.put((task_id, "ok", func(*args, **kwargs)))
        except Exception as exc:
            result_queue.put((task_id, "err", exc))


class _WatchdogWorker:
    def __init__(self) -> None:
        self._ctx = mp.get_context("spawn")
        self._task_queue = self._ctx.Queue()
        self._result_queue = self._ctx.Queue()
        self._process = self._ctx.Process(
            target=_worker_loop,
            args=(self._task_queue, self._result_queue),
        )
        self._process.start()
        self._next_task_id = 1

    def run(self, func: callable, args: tuple, kwargs: dict, max_seconds: float | None):
        task_id = self._next_task_id
        self._next_task_id += 1
        self._task_queue.put((task_id, func, args, kwargs))

        try:
            if max_seconds is None:
                result_id, status, payload = self._result_queue.get()
            else:
                result_id, status, payload = self._result_queue.get(timeout=max_seconds)
        except queue.Empty:
            self._restart()
            return None, True

        if result_id != task_id:
            self._restart()
            return None, True

        if status == "err":
            raise payload

        return payload, False

    def _restart(self) -> None:
        if self._process.is_alive():
            self._process.terminate()
        self._process.join()
        self._task_queue.close()
        self._result_queue.close()
        self._task_queue = self._ctx.Queue()
        self._result_queue = self._ctx.Queue()
        self._process = self._ctx.Process(
            target=_worker_loop,
            args=(self._task_queue, self._result_queue),
        )
        self._process.start()


_WATCHDOG_WORKER = None


def _get_worker() -> _WatchdogWorker:
    global _WATCHDOG_WORKER
    if _WATCHDOG_WORKER is None:
        _WATCHDOG_WORKER = _WatchdogWorker()
    return _WATCHDOG_WORKER


def _timed_call(func: callable, args: tuple, kwargs: dict, max_seconds: float | None) -> tuple:
    """
    Call the given function with arguments and measure the time taken.
    If it exceeds max_seconds, return a timeout indication.
    """
    if max_seconds is None:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration = time.perf_counter() - start
        return result, duration, False

    start = time.perf_counter()
    result, timed_out = _get_worker().run(func, args, kwargs, max_seconds)
    duration = time.perf_counter() - start
    return result, duration, timed_out


def _report_watchdog_issues(
    func_name: str, issues: list, timings: list, max_seconds: float
) -> None:
    """Report any watchdog issues detected during the redundant calls, including timing information."""
    timing_str = ", ".join(f"{t:.6f}s" for t in timings)
    issue_str = ", ".join(issues)
    print(
        f"[watchdog] {func_name} issues: {issue_str}. timings=[{timing_str}] max={max_seconds:.6f}s",
        file=sys.stderr,
    )


def ft_redundance(func: callable, *args, max_seconds: float | None = None, **kwargs):
    """Calls the given function multiple times to check for consistency and timing, and report any issues detected."""
    issues = []
    timings = []

    # First two calls to check for consistency and timing.
    result1, t1, timed_out1 = _timed_call(func, args, kwargs, max_seconds=max_seconds)
    timings.append(t1)
    if timed_out1:
        issues.append("call1_timeout")
    result2, t2, timed_out2 = _timed_call(func, args, kwargs, max_seconds=max_seconds)
    timings.append(t2)
    if timed_out2:
        issues.append("call2_timeout")

    # If results differ, do a third call to break the tie.
    if timed_out1 or timed_out2 or result1 != result2:
        issues.append("result_mismatch_12")
        result3, t3, timed_out3 = _timed_call(func, args, kwargs, max_seconds=max_seconds)
        timings.append(t3)
        if timed_out3:
            issues.append("call3_timeout")

        # Determine the majority result among the three calls.
        if not timed_out1 and not timed_out3 and result1 == result3:
            result = result1
        elif not timed_out2 and not timed_out3 and result2 == result3:
            result = result2
        else:
            issues.append("result_mismatch_123")
            result = "ERROR_TMR"
    else:
        result = result1

    # Reporting issues if any.
    if issues and max_seconds is not None:
        _report_watchdog_issues(func.__name__, issues, timings, max_seconds)

    return result


def schedule_tasks_ft(tasks, current_time):
    return ft_redundance(
        schedule_tasks,
        tasks,
        current_time,
        max_seconds=SCHEDULE_TASKS_MAX_SECONDS,
    )


def checksum_ft(payload, n: int, received_checksum: int):
    return ft_redundance(
        checksum,
        payload,
        n,
        received_checksum,
        max_seconds=CHECKSUM_MAX_SECONDS,
    )


if __name__ == "__main__":
    for i in range(REPS):
        result = schedule_tasks_ft([(1, 0, 10, 50), (2, 2, 5, 50), (3, 3, 3, 50)], 0)
        # flush=True so output is not lost if the process is killed mid-iteration.
        print(result, flush=True)
