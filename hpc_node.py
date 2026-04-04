import os
import runtrace

# Mock the environment variable a Slurm array would set
os.environ["RUNTRACE_META_REF"] = "meta.json"

print("Starting node...")
tracker = runtrace.start(overrides={"core":{"profile":"minimal"}})
print("Doing work...")
runtrace.annotate("work", iterations=100)
print("Finished!")
