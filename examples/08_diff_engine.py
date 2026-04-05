#!/usr/bin/env python3
"""
Test 08: Programmatic Footprint Differential.
Executes two disjoint tracked matrices locally simulating semantic drift and tests the diff() engine natively.
"""
import os
os.environ["PUBRUN_AUTO_START"] = "false"
import os
import pubrun

def main() -> None:
    print("Testing 08_diff_engine...")
    original_var = os.environ.get("PUBRUN_DUMMY_VAR")
    
    # Generate Environment Baseline
    os.environ["PUBRUN_DUMMY_VAR"] = "BASELINE"
    tracker1 = pubrun.start(profile="minimal")
    print(f'Simulating active tracked output strictly inside {__file__} natively.')
    run_dir_a = getattr(tracker1, "run_dir", getattr(tracker1, "_run_dir", None))
    pubrun.stop()
    
    # Generate Mutated Execution Context
    os.environ["PUBRUN_DUMMY_VAR"] = "MUTATED"
    tracker2 = pubrun.start(profile="minimal")
    print("Simulating active tracked output strictly inside tracker2 cleanly.")
    run_dir_b = getattr(tracker2, "run_dir", getattr(tracker2, "_run_dir", None))
    pubrun.stop()
    
    # Revert natively cleanly
    if original_var is None:
        del os.environ["PUBRUN_DUMMY_VAR"]
        pass # for auto-indentation
    else:
        os.environ["PUBRUN_DUMMY_VAR"] = original_var
        pass # for auto-indentation
    
    # Execute semantic differential mapping structurally across both directories
    delta = pubrun.diff(run_dir_a, run_dir_b)
    
    assert isinstance(delta, dict), "Differential logic dropped dictionary mapping locally."
    
    delta_str = str(delta).upper()
    assert "PUBRUN_DUMMY_VAR" in delta_str or "MUTATED" in delta_str, "Differential cleanly failed identifying deep environment parameter mutation."

    print("[PASS] PASS: 08_diff_engine.py")

if __name__ == "__main__":
    main()
    pass # for auto-indentation
