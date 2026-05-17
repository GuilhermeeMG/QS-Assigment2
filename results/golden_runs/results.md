# General notes

All golden runs where runned for 20 runs with 1_000_000 reps each
All the durations and fi_min and fi_max are in miliseconds
The fi_min should be 10%-20% of the mean duration (aiming ~15%)
The fi_max should be 80% of the mean duration
watchdog_dur should be 200%-300% of max duration (aiming ~250%)

**expected_len**: 10_000_000 bytes
"[1, 2, 3]" is 9 bytes
\n is 1 byte
total per line = 10 bytes
So for 1,000,000 reps: 10,000,000 bytes.

To create 

# Baseline (GoldenRun_Baseline)

| Min duration | Mean duration | Max duration | Total duration |
| --- | --- | --- | --- |
| 78380 | 100070 | 102360 | 2001460 |

fi_min = 15010 -> 15000
fi_max = 80056 -> 80000
watchdog_dur = 255900

# V1 (GoldenRun_FT_V1)

| Min duration | Mean duration | Max duration | Total duration |
| --- | --- | --- | --- |
| 101040 | 101360 | 106210 | 2027240 |

fi_min = 15204 -> 15200
fi_max = 81088 -> 81000
watchdog_dur = 265525

# V4 (GoldenRun_FT_V4)

| Min duration | Mean duration | Max duration | Total duration |
| --- | --- | --- | --- |
| 101050 | 101240 | 102880 | 2024760 |

fi_min = 15186 -> 15100
fi_max = 80992 -> 80900
watchdog_dur = 257200

# V5 (GoldenRun_FT_V5_1)

| Min duration | Mean duration | Max duration | Total duration |
| --- | --- | --- | --- |
| 101050 | 101110 | 101240 | 2022160 |

fi_min = 15166 -> 15100
fi_max = 80888 -> 80800
watchdog_dur = 253100
