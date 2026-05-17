from fr1_scheduler import schedule_tasks
from fr2_checksum import checksum

REPS = 1_000_000

# Timing Redundancy

def ft_redundance(func: callable, *args, max_seconds: float | None = None, **kwargs):
    # First two calls to check for consistency.
    result1 = func(*args, **kwargs)
    result2 = func(*args, **kwargs)

    # If results differ, do a third call to break the tie.
    if result1 != result2:
        result3 = func(*args, **kwargs)

        # Determine the majority result among the three calls.
        if result1 == result3:
            return result1
        elif result2 == result3:
            return result2
    else:
        return result1


def schedule_tasks_ft(tasks, current_time) -> bool:
    return ft_redundance(schedule_tasks, tasks, current_time)


def checksum_ft(payload, n: int, received_checksum: int) -> bool:
    return ft_redundance(checksum, payload, n, received_checksum)


if __name__ == "__main__":
    for i in range(REPS):
        result = schedule_tasks_ft([(1, 0, 10, 50), (2, 2, 5, 50), (3, 3, 3, 50)], 0)
        print(result, flush=True)
        #checksum_ft(bytes([i % 256 for i in range(10)]), 10, 0)
