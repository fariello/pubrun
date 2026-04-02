import argparse
import sys
import importlib.resources
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="runtrace context capture utility.")
    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create a default runtrace.toml in the current directory."
    )
    args = parser.parse_args()

    if args.create_config:
        try:
            # We look for default.toml inside src/runtrace/resources/
            resource_path = importlib.resources.files("runtrace").joinpath("resources", "default.toml")
            content = resource_path.read_text(encoding="utf-8")
            
            target_path = Path(".runtrace.toml")
            if target_path.exists():
                print(f"Error: {target_path} already exists. Refusing to overwrite.", file=sys.stderr)
                sys.exit(1)
                
            target_path.write_text(content, encoding="utf-8")
            print(f"Successfully created {target_path}")
            
        except Exception as e:
            print(f"Failed to create config: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
