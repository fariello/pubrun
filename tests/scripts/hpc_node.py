import os
import pubrun

# Mock the environment variable a Slurm array would set
os.environ["PUBRUN_META_REF"] = "meta.json"

print("Starting node...")
tracker = pubrun.start(overrides={"core":{"profile":"minimal"}})
print("Doing work...")
pubrun.annotate("work", iterations=100)
print("Finished!")
