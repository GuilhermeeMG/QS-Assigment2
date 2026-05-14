from fr1_scheduler import schedule_tasks
from fr2_checksum import checksum

REPS = 1_000_000


if __name__ == "__main__":

    for i in range(REPS):
        result = schedule_tasks([(1, 0, 10, 50), (2, 2, 5, 50), (3, 3, 3, 50)], 0)
        print(result, flush=True)
