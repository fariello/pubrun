import subprocess
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        try:
            # Retrieve latest git commit hash referencing the project root
            commit = subprocess.check_output(
                ["git", "-C", self.root, "rev-parse", "HEAD"], text=True
            ).strip()
            with open("src/pubrun/COMMIT", "w", encoding="utf-8") as f:
                f.write(commit + "\n")
        except Exception:
            # If not building inside a git repository, fallback gracefully
            pass
