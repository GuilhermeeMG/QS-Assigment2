from fr1_scheduler import schedule_tasks
from fr2_checksum import checksum

REPS = 1_000_000


if __name__ == "__main__":
    # Same workload, prints, and REPS as frx_ft_v4.py so ucXception campaigns
    # against this baseline and the FT version are directly comparable.
    for i in range(REPS):
        result = schedule_tasks([(1, 0, 10, 50), (2, 2, 5, 50), (3, 3, 3, 50)], 0)
        print(result, flush=True)
        #result = checksum(bytes([i % 256 for i in range(10)]), 10, 0)
        #print(result, flush=True)
