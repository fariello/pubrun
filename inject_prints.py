import glob
import os
files = glob.glob(r"c:\Users\gabri\OneDrive\Projects\pubrun\examples\*.py")
for f in files:
    name = os.path.basename(f)
    if name in ["00_auto_start.py", "01_minimal_start_stop.py", "02_context_manager.py", "verify_all.py", "09_cli_methods.py"]:
        continue
    
    with open(f, "r", encoding="utf-8") as fd:
         lines = fd.readlines()
         
    # Inject right after tracking initiates
    for i, line in enumerate(lines):
        if "pubrun.start" in line or "pubrun.tracked_run()" in line or "pubrun.audit_run()" in line:
            lines.insert(i+1, " " * (len(line) - len(line.lstrip())) + "print(f'Simulating active tracked output strictly inside {__file__} natively.')\n")
            break
            
    with open(f, "w", encoding="utf-8") as fd:
        fd.writelines(lines)
