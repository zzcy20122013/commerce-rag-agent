from app.evaluation.runner import run_all_evaluations


def main() -> None:
    summary = run_all_evaluations()
    print(summary)


if __name__ == "__main__":
    main()
