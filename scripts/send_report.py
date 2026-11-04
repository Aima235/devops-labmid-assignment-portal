"""Convert pytest JUnit XML to evidence JSON, POST localhost, optional SMTP email."""
import json
import os
import smtplib
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XML = ROOT / "pytest-results.xml"


def make_report():
    tests = []
    if XML.exists():
        root = ET.parse(XML).getroot()
        for t in root.iter("testcase"):
            failure = t.find("failure")
            error = t.find("error")
            skipped = t.find("skipped")
            issue = failure if failure is not None else error
            state = "failed" if issue is not None else ("skipped" if skipped is not None else "passed")
            details = (issue.get("message") or (issue.text or "").strip()) if issue is not None else None
            tests.append({"name": f"{t.get('classname','')}.{t.get('name','')}", "result": state,
                          "failure_message": details if state == "failed" else None})
    else:
        tests.append({"name": "pytest_execution", "result": "failed", "failure_message": "pytest-results.xml was not created"})
    total = len(tests)
    passed = sum(t["result"] == "passed" for t in tests)
    failed = sum(t["result"] == "failed" for t in tests)
    skipped = sum(t["result"] == "skipped" for t in tests)
    overall = "passed" if failed == 0 and skipped == 0 and total > 0 else "failed"
    return {
        "repository": os.getenv("GITHUB_REPOSITORY", "local/manual-run"),
        "branch": os.getenv("GITHUB_REF_NAME", "local"),
        "commit_sha": os.getenv("GITHUB_SHA", "local-uncommitted"),
        "pipeline_run_id": os.getenv("GITHUB_RUN_ID", "local"),
        "pipeline_run_attempt": os.getenv("GITHUB_RUN_ATTEMPT", "1"),
        "execution_timestamp": datetime.now(timezone.utc).isoformat(),
        "tests": tests,
        "summary": {"total": total, "passed": passed, "failed": failed, "skipped": skipped,
                    "overall_status": overall},
    }


def email_report(report):
    if os.getenv("SEND_EMAIL", "").lower() != "true":
        print("Email bonus disabled (set repository variable SEND_EMAIL=true to enable).")
        return
    required = ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "REPORT_EMAIL_TO"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError("Email enabled but missing settings: " + ", ".join(missing))
    msg = EmailMessage()
    summary = report["summary"]
    msg["Subject"] = f"DevOps CI {summary['overall_status'].upper()} | {report['commit_sha'][:8]}"
    msg["From"] = os.getenv("REPORT_EMAIL_FROM") or os.environ["SMTP_USERNAME"]
    msg["To"] = os.environ["REPORT_EMAIL_TO"]
    lines = [f"Repository: {report['repository']}", f"Branch: {report['branch']}",
             f"Commit: {report['commit_sha']}", f"Run: {report['pipeline_run_id']}",
             f"Overall: {summary['overall_status']}",
             f"Total: {summary['total']}; Passed: {summary['passed']}; Failed: {summary['failed']}",
             "", "Individual tests:"]
    for t in report["tests"]:
        lines.append(f"- {t['name']}: {t['result']}" + (f" | {t['failure_message']}" if t['failure_message'] else ""))
    msg.set_content("\n".join(lines))
    msg.add_attachment(json.dumps(report, indent=2).encode("utf-8"), maintype="application",
                       subtype="json", filename="test-report.json")
    port = int(os.environ["SMTP_PORT"])
    if port == 465:
        with smtplib.SMTP_SSL(os.environ["SMTP_HOST"], port, timeout=20) as server:
            server.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
            server.send_message(msg)
    else:
        with smtplib.SMTP(os.environ["SMTP_HOST"], port, timeout=20) as server:
            server.starttls()
            server.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
            server.send_message(msg)
    print("Email report sent.")


def main():
    report = make_report()
    body = json.dumps(report, indent=2).encode("utf-8")
    (ROOT / "ci-test-report.json").write_bytes(body)
    print(json.dumps(report["summary"], indent=2))
    req = urllib.request.Request(
        os.getenv("REPORT_RECEIVER_URL", "http://127.0.0.1:8765/report"), data=body,
        headers={"Content-Type": "application/json", "X-Report-Token": os.getenv("REPORT_TOKEN", "")},
        method="POST")
    exit_code = 0
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            print("Local report receiver:", response.status, response.read().decode())
    except Exception as ex:
        print("ERROR: Could not deliver CI report to local receiver:", ex, file=sys.stderr)
        exit_code = 1
    try:
        email_report(report)
    except Exception as ex:
        print("ERROR: Email delivery failed:", ex, file=sys.stderr)
        exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
