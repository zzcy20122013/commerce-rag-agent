from app.evaluation.failure_mining import export_negative_feedback


def main() -> None:
    rows = export_negative_feedback()
    print({"negative_feedback_count": len(rows)})


if __name__ == "__main__":
    main()
