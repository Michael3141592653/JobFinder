import argparse


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="jobfinder")
    parser.add_argument("command", choices=["run"])
    args = parser.parse_args(argv)

    if args.command == "run":
        print("jobfinder: nothing to run yet")
