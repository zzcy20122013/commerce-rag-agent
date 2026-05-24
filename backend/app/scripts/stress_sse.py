from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


DEFAULT_PROMPT = "推荐 300 以内适合通勤的鞋"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a lightweight concurrent SSE smoke test.")
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/chat/stream")
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--requests", type=int, default=10)
    parser.add_argument("--message", default=DEFAULT_PROMPT)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    started = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=max(args.concurrency, 1)) as executor:
        futures = [
            executor.submit(run_one_request, args.url, args.message, args.timeout, index)
            for index in range(args.requests)
        ]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(json.dumps(result, ensure_ascii=False))

    elapsed = time.perf_counter() - started
    ok_count = sum(1 for item in results if item["ok"])
    print(
        json.dumps(
            {
                "summary": {
                    "requests": args.requests,
                    "concurrency": args.concurrency,
                    "ok": ok_count,
                    "failed": len(results) - ok_count,
                    "elapsed_seconds": round(elapsed, 3),
                    "avg_seconds": round(sum(item["elapsed_seconds"] for item in results) / max(len(results), 1), 3),
                }
            },
            ensure_ascii=False,
        )
    )


def run_one_request(url: str, message: str, timeout: int, index: int) -> dict:
    started = time.perf_counter()
    body = json.dumps({"message": f"{message} #{index}"}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    chunks = 0
    done = False
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="ignore").strip()
                if line.startswith("event: message"):
                    chunks += 1
                elif line.startswith("event: done"):
                    done = True
        return {
            "index": index,
            "ok": done,
            "chunks": chunks,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "error": "",
        }
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return {
            "index": index,
            "ok": False,
            "chunks": chunks,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "error": str(error),
        }


if __name__ == "__main__":
    main()
