"""No-op workload: measures pure import/startup + finalize overhead.

The workload body does nothing; timing differences between scenarios that run
this file reflect pubrun's import-mode / startup / shutdown cost, not any work.
"""

if __name__ == "__main__":
    pass
