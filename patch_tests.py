import glob
import os

files = glob.glob(r"c:\Users\gabri\OneDrive\Projects\pubrun\examples\*.py")
for f in files:
    name = os.path.basename(f)
    if name in ["00_auto_start.py", "verify_all.py"]:
        continue
    
    with open(f, "r", encoding="utf-8") as fd:
        content = fd.read()
    
    if "PUBRUN_AUTO_START" not in content:
        lines = content.split("\n")
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('"""') and i > 2:
                insert_idx = i + 1
                break
        
        new_lines = lines[:insert_idx] + ["import os", 'os.environ["PUBRUN_AUTO_START"] = "false"'] + lines[insert_idx:]
        
        with open(f, "w", encoding="utf-8") as fd:
            fd.write("\n".join(new_lines))
