import argparse

from app.evaluation.run_guide_eval import run_guide_evaluation
from app.evaluation.run_feedback_loop_eval import run_feedback_loop_evaluation
from app.evaluation.runner import run_all_evaluations, run_smoke_evaluation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run commerce agent evaluations.")
    parser.add_argument(
        "--suite",
        choices=["all", "smoke", "guide", "feedback"],
        default="all",
        help="Evaluation suite to run.",
    )
    parser.add_argument("--report-dir", default=None, help="Optional report output directory.")
    args = parser.parse_args()

    if args.suite == "feedback":
        summary = run_feedback_loop_evaluation(report_dir=args.report_dir) if args.report_dir else run_feedback_loop_evaluation()
    elif args.suite == "guide":
        summary = run_guide_evaluation(report_dir=args.report_dir) if args.report_dir else run_guide_evaluation()
    elif args.suite == "smoke":
        summary = run_smoke_evaluation(report_dir=args.report_dir) if args.report_dir else run_smoke_evaluation()
    else:
        summary = run_all_evaluations(report_dir=args.report_dir) if args.report_dir else run_all_evaluations()
    print(summary)


if __name__ == "__main__":
    main()
