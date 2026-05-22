import argparse

from app.evaluation.runner import run_all_evaluations, run_smoke_evaluation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run commerce agent evaluations.")
    parser.add_argument("--suite", choices=["all", "smoke"], default="all", help="Evaluation suite to run.")
    parser.add_argument("--report-dir", default=None, help="Optional report output directory.")
    args = parser.parse_args()

    if args.suite == "smoke":
        summary = run_smoke_evaluation(report_dir=args.report_dir) if args.report_dir else run_smoke_evaluation()
    else:
        summary = run_all_evaluations(report_dir=args.report_dir) if args.report_dir else run_all_evaluations()
    print(summary)


if __name__ == "__main__":
    main()
