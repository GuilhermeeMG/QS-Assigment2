import sys
import time

from fr1_scheduler import schedule_tasks
from fr2_checksum import checksum

REPS = 1_000_000

SCHEDULE_TASKS_MAX_SECONDS = 0.01
CHECKSUM_MAX_SECONDS = 0.01


def _timed_call(func: callable, *args, **kwargs):
    start = time.perf_counter()
    result = func(*args, **kwargs)
    duration = time.perf_counter() - start
    return result, duration


def _report_watchdog_issues(
    func_name: str, issues: list, timings: list, max_seconds: float
) -> None:
    timing_str = ", ".join(f"{t:.6f}s" for t in timings)
    issue_str = ", ".join(issues)
    print(
        f"[watchdog] {func_name} issues: {issue_str}. timings=[{timing_str}] max={max_seconds:.6f}s",
        file=sys.stderr,
    )


def ft_redundance(func: callable, *args, max_seconds: float | None = None, **kwargs):
    issues = []
    timings = []

    # First two calls to check for consistency and timing.
    result1, t1 = _timed_call(func, *args, **kwargs)
    timings.append(t1)
    if max_seconds is not None and t1 > max_seconds:
        issues.append("call1_timeout")
    result2, t2 = _timed_call(func, *args, **kwargs)
    timings.append(t2)
    if max_seconds is not None and t2 > max_seconds:
        issues.append("call2_timeout")

    # If results differ, do a third call to break the tie.
    if result1 != result2:
        issues.append("result_mismatch_12")
        result3, t3 = _timed_call(func, *args, **kwargs)
        timings.append(t3)
        if max_seconds is not None and t3 > max_seconds:
            issues.append("call3_timeout")

        # Determine the majority result among the three calls.
        if result1 == result3:
            result = result1
        elif result2 == result3:
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


def schedule_tasks_ft(tasks, current_time) -> bool:
    return ft_redundance(
        schedule_tasks,
        tasks,
        current_time,
        max_seconds=SCHEDULE_TASKS_MAX_SECONDS,
    )


def checksum_ft(payload, n: int, received_checksum: int) -> bool:
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
        # checksum_ft(bytes([i % 256 for i in range(10)]), 10, 0)
