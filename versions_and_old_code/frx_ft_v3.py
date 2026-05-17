import multiprocessing as mp
import sys
import time

from fr1_scheduler import schedule_tasks
from fr2_checksum import checksum

REPS = 1_000_000

SCHEDULE_TASKS_MAX_SECONDS = 0.09
CHECKSUM_MAX_SECONDS = 0.09


def _worker(queue: mp.Queue, func: callable, args: tuple, kwargs: dict) -> None:
    """Worker function to execute the given function with arguments and put the result in the queue."""
    try:
        queue.put(("ok", func(*args, **kwargs)))
    except Exception as exc:
        queue.put(("err", exc))


def _timed_call(func: callable, args: tuple, kwargs: dict, max_seconds: float) -> tuple:
    """
    Call the given function with arguments and measure the time taken.
    If it exceeds max_seconds, return a timeout indication.
    """
    
    # Use multiprocessing to run the function in a separate process with a timeout.
    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    process = ctx.Process(target=_worker, args=(queue, func, args, kwargs))

    # Start the process and wait for it to finish or timeout
    start = time.perf_counter()
    process.start()
    process.join(max_seconds)

    # If the process is still alive after the timeout, terminate it
    if process.is_alive():
        process.terminate()
        process.join()
        duration = time.perf_counter() - start
        return None, duration, True

    # Process finished within the time limit, get the result and duration
    duration = time.perf_counter() - start
    if queue.empty():
        raise RuntimeError("Worker finished without returning a result")

    # Get the result from the queue and check for exceptions
    status, payload = queue.get()
    if status == "err":
        raise payload

    # Return the payload, duration, and a flag indicating whether it timed out
    return payload, duration, False


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
            result = None
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
        schedule_tasks_ft([(1, 0, 10, 50), (2, 2, 5, 50), (3, 3, 3, 50)], 0)
        #checksum_ft(bytes([i % 256 for i in range(10)]), 10, 0)
