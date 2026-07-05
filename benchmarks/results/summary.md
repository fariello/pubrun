# pubrun overhead summary

Machines aggregated: 1
- `Linux/AMD Ryzen 7 3700X 8-Core Processor/16c`

Overhead is median wall time relative to the group baseline (a fresh Python process with no pubrun / no features).

| Machine | Group | Scenario | Median (ms) | p95 (ms) | vs baseline | Overhead (ms) | Overhead (%) |
|---|---|---|---:|---:|---|---:|---:|
| Linux/AMD Ryzen 7 3700X 8-Core Processor/16c | feature | feature-baseline | 131.58 | 139.91 | - | - | - |
| Linux/AMD Ryzen 7 3700X 8-Core Processor/16c | feature | feature-git | 218.47 | 255.51 | feature-baseline | 86.9 | 66.0 |
| Linux/AMD Ryzen 7 3700X 8-Core Processor/16c | feature | feature-hardware | 230.26 | 240.48 | feature-baseline | 98.68 | 75.0 |
| Linux/AMD Ryzen 7 3700X 8-Core Processor/16c | feature | feature-none | 236.94 | 263.82 | feature-baseline | 105.36 | 80.1 |
| Linux/AMD Ryzen 7 3700X 8-Core Processor/16c | feature | feature-packages-full | 369.28 | 381.35 | feature-baseline | 237.7 | 180.7 |
| Linux/AMD Ryzen 7 3700X 8-Core Processor/16c | feature | feature-packages-imported | 270.48 | 312.13 | feature-baseline | 138.9 | 105.6 |
| Linux/AMD Ryzen 7 3700X 8-Core Processor/16c | feature | feature-resources-15s | 228.9 | 279.51 | feature-baseline | 97.32 | 74.0 |
| Linux/AMD Ryzen 7 3700X 8-Core Processor/16c | feature | feature-resources-1s | 266.42 | 301.71 | feature-baseline | 134.84 | 102.5 |
| Linux/AMD Ryzen 7 3700X 8-Core Processor/16c | feature | feature-resources-tree | 231.21 | 248.71 | feature-baseline | 99.63 | 75.7 |
| Linux/AMD Ryzen 7 3700X 8-Core Processor/16c | feature | feature-subprocesses | 218.59 | 291.01 | feature-baseline | 87.01 | 66.1 |
| Linux/AMD Ryzen 7 3700X 8-Core Processor/16c | hotpath | hotpath-open-baseline | 43.81 | 50.74 | - | - | - |
| Linux/AMD Ryzen 7 3700X 8-Core Processor/16c | hotpath | hotpath-open-pubrun | 129.85 | 142.82 | hotpath-open-baseline | 86.04 | 196.4 |
| Linux/AMD Ryzen 7 3700X 8-Core Processor/16c | hotpath | hotpath-print-baseline | 18.54 | 20.64 | - | - | - |
| Linux/AMD Ryzen 7 3700X 8-Core Processor/16c | hotpath | hotpath-print-tee | 146.83 | 154.0 | hotpath-print-baseline | 128.29 | 692.0 |
| Linux/AMD Ryzen 7 3700X 8-Core Processor/16c | startup | baseline-noop | 17.48 | 20.18 | - | - | - |
| Linux/AMD Ryzen 7 3700X 8-Core Processor/16c | startup | import-auto | 149.28 | 169.94 | baseline-noop | 131.8 | 754.0 |
| Linux/AMD Ryzen 7 3700X 8-Core Processor/16c | startup | import-minimal | 107.25 | 114.53 | baseline-noop | 89.77 | 513.5 |
| Linux/AMD Ryzen 7 3700X 8-Core Processor/16c | startup | import-noauto | 108.76 | 141.8 | baseline-noop | 91.28 | 522.2 |
| Linux/AMD Ryzen 7 3700X 8-Core Processor/16c | startup | import-noconsole | 128.75 | 155.13 | baseline-noop | 111.27 | 636.6 |
| Linux/AMD Ryzen 7 3700X 8-Core Processor/16c | startup | import-nopatch | 143.87 | 156.96 | baseline-noop | 126.39 | 723.0 |
