# pubrun overhead summary

Machines aggregated: 1
- `Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c`

Overhead is median wall time relative to the group baseline (a fresh Python process with no pubrun / no features).

| Machine | Group | Scenario | Median (ms) | p95 (ms) | vs baseline | Overhead (ms) | Overhead (%) |
|---|---|---|---:|---:|---|---:|---:|
| Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c | feature | feature-baseline | 241.37 | 262.29 | - | - | - |
| Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c | feature | feature-git | 343.1 | 360.89 | feature-baseline | 101.72 | 42.1 |
| Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c | feature | feature-hardware | 352.91 | 375.73 | feature-baseline | 111.53 | 46.2 |
| Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c | feature | feature-none | 361.01 | 378.04 | feature-baseline | 119.64 | 49.6 |
| Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c | feature | feature-packages-full | 446.14 | 480.45 | feature-baseline | 204.77 | 84.8 |
| Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c | feature | feature-packages-imported | 356.56 | 402.24 | feature-baseline | 115.19 | 47.7 |
| Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c | feature | feature-resources-15s | 366.78 | 411.07 | feature-baseline | 125.41 | 52.0 |
| Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c | feature | feature-resources-1s | 362.78 | 391.36 | feature-baseline | 121.41 | 50.3 |
| Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c | feature | feature-resources-tree | 371.48 | 409.65 | feature-baseline | 130.1 | 53.9 |
| Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c | feature | feature-subprocesses | 347.48 | 398.35 | feature-baseline | 106.1 | 44.0 |
| Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c | hotpath | hotpath-open-baseline | 53.29 | 62.93 | - | - | - |
| Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c | hotpath | hotpath-open-pubrun | 168.71 | 185.01 | hotpath-open-baseline | 115.42 | 216.6 |
| Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c | hotpath | hotpath-print-baseline | 21.66 | 23.96 | - | - | - |
| Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c | hotpath | hotpath-print-tee | 218.2 | 238.84 | hotpath-print-baseline | 196.54 | 907.4 |
| Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c | io_baseline | io-baseline-devnull | 39.09 | 45.83 | - | - | - |
| Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c | io_baseline | io-baseline-devshm | 49.04 | 55.49 | - | - | - |
| Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c | io_baseline | io-baseline-tmpdir | 51.71 | 59.63 | - | - | - |
| Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c | startup | baseline-noop | 18.27 | 21.56 | - | - | - |
| Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c | startup | import-auto | 162.76 | 172.75 | baseline-noop | 144.5 | 791.1 |
| Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c | startup | import-minimal | 113.0 | 137.86 | baseline-noop | 94.74 | 518.7 |
| Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c | startup | import-noauto | 102.75 | 119.46 | baseline-noop | 84.48 | 462.5 |
| Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c | startup | import-noconsole | 160.79 | 174.77 | baseline-noop | 142.52 | 780.3 |
| Linux/Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz/12c | startup | import-nopatch | 143.41 | 158.12 | baseline-noop | 125.14 | 685.1 |
