# DevOps Lab Mid | CSC418 | AssignmentHub

A complete assignment submission portal with automated pytest CI, local JSON report delivery, conditional GitHub Pages deployment, and optional SMTP test emails.

**Important:** GitHub Actions for the required report runs on a Windows **self-hosted runner on your own PC**. The test receiver is reachable at `http://127.0.0.1:8765/report` from that same PC. A GitHub-hosted runner would have a different localhost and would NOT meet the lab requirement. Do **not** run untrusted pull requests or arbitrary third-party code on your self-hosted runner.

## Files

- `app.py`: Flask server, input validation, SQLite persistence.
- `templates/index.html`, `static/style.css`: portal interface.
- `tests/test_portal.py`: six pytest cases, including all three explicitly required tests.
- `receiver.py`: localhost-only report receiver; atomically writes `test-report.json`.
- `scripts/send_report.py`: parses actual pytest JUnit XML, adds GitHub metadata, posts JSON, optionally emails it.
- `.github/workflows/ci.yml`: every-push CI, local delivery in pass/fail situations, conditional GitHub Pages deployment.
- `pages/index.html`: purely static GitHub Pages demo (data is browser-local, not the Flask SQLite database).

## Prerequisites

Install Git, Python 3.12, and a GitHub account. On Windows, use **Command Prompt (CMD)** for steps below. Ensure both `python --version` and `git --version` work.

## First run (Windows CMD)

Unzip the project to a simple location such as `C:\Users\Admin\DevOps_LabMid_Complete`. Open **CMD**, then:

```bat
cd /d C:\Users\Admin\DevOps_LabMid_Complete
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python app.py
```

Go to `http://127.0.0.1:5000`. Submit valid details. Open a second CMD in the same project and run:

```bat
cd /d C:\Users\Admin\DevOps_LabMid_Complete
.venv\Scripts\activate.bat
python -m pytest -q tests --junitxml=pytest-results.xml
```

Expected when code is unmodified: 6 passed. This expected output is an illustration, **not** evidence of a GitHub CI run.

## Local report receiver

Open a **third CMD**, inside the project folder:

```bat
.venv\Scripts\activate.bat
python receiver.py
```

Leave it running. Check `http://127.0.0.1:8765/health` in your browser. Run the following in another CMD to create a test JSON from your just-executed local pytest output and send it automatically:

```bat
.venv\Scripts\activate.bat
python scripts\send_report.py
```

The receiver creates or replaces `test-report.json` in the project directory. The CI workflow also runs `send_report.py` **automatically after every pushed test execution**, even if the test fails. Do not upload the generated JSON to GitHub unless specifically asked.

## Create your GitHub repo

Create an **empty** GitHub repository named `devops-labmid-assignment-portal`, without an auto-generated README or `.gitignore`. In CMD:

```bat
cd /d C:\Users\Admin\DevOps_LabMid_Complete
git init
git branch -M main
git add .
git commit -m "Initial assignment portal with CI and localhost reports"
git remote add origin https://github.com/YOUR_USERNAME/devops-labmid-assignment-portal.git
```

Replace `YOUR_USERNAME` in the remote URL. **Before the first push, configure the runner below.** Then:

```bat
git push -u origin main
```

## Connect a Windows self-hosted runner (required for the localhost task)

1. In your GitHub repository choose **Settings → Actions → Runners → New self-hosted runner**.
2. Choose **Windows** and **x64**. GitHub shows the current official download URL, archive name, registration token, and exact setup commands. Copy **those live commands** (do not use a token pasted from an online tutorial).
3. Install the runner **outside the project** (for example `C:\actions-runner`), follow GitHub's instructions in the provided PowerShell terminal, and configure it for this repository.
4. Start it using `run.cmd` from its runner folder. Leave this terminal open. Look for **Listening for Jobs**. Check that GitHub shows **Idle** (online).
5. Keep `python receiver.py` in its other CMD open. The first push triggers the workflow on the Windows machine. The pipeline can now POST to its own `localhost`.

The CI job uses `runs-on: [self-hosted, windows, x64]` and needs Python 3.12 plus Git available to the runner. `actions/setup-python` supplies Python, while you install Git on the PC. **Do not place the runner inside your Git repository.** On a shared PC, protect runner access and secrets.

## Mandatory evidence sequence (pass → fail → fix)

Ensure both receiver CMD and self-hosted runner terminal remain open. In the GitHub **Actions** tab:

**A. PASS**: Push the unmodified project. Click the run. Confirm `Run actual pytest test cases` passes, `Automatically send report` succeeds, and `test-report.json` is created with `"overall_status": "passed"` and `"failed": 0`. Save screenshots of the run, test logs, and local JSON.

**B. FAIL**: Open `app.py`. In `validate_submission`, find:

```python
if not cleaned[field]:
```

Temporarily change to:

```python
if not cleaned[field] and field != "registration_number":
```

This deliberately disables the required-registration check. Save; then in CMD:

```bat
git add app.py
git commit -m "Demonstration: intentionally break registration validation"
git push
```

`test_missing_registration_number_is_rejected` should now fail. Despite the red CI run, the **report-delivery step still runs** and the local `test-report.json` should show a failing test with its failure message and an updated commit SHA/run ID. Save screenshots of all three.

**C. FIX**: Restore the **original** line `if not cleaned[field]:` in `app.py`, then:

```bat
git add app.py
git commit -m "Fix registration validation"
git push
```

Confirm the new green run, `test-report.json` updated to passing, and the new commit SHA. Save screenshots.

Do not force tests to pass or modify the tests to hide the defect. The red run is intentionally needed for the assignment.

## GitHub Pages bonus (5 marks)

1. Repository → **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. The `deploy_pages` job runs on `ubuntu-latest`, **only after `test_and_report` succeeds** on `main`.
3. After your first successful push, get the deployed URL from the `deploy_pages` job (usually `https://YOUR_USERNAME.github.io/devops-labmid-assignment-portal/`). Verify the URL. The failing push **must not deploy**, so the previously published version remains.
4. The GitHub Pages page is a **static localStorage demo**; the real Flask app remains the main portal backed by SQLite.

## Email bonus (5 marks)

The workflow includes optional SMTP support on **both passing and failing runs**. In repository **Settings → Secrets and variables → Actions**, create:

| Type | Name | Example |
| --- | --- | --- |
| Variable | `SEND_EMAIL` | `true` |
| Variable | `SMTP_HOST` | `smtp.gmail.com` |
| Variable | `SMTP_PORT` | `465` |
| Variable | `REPORT_EMAIL_TO` | your destination email |
| Variable | `REPORT_EMAIL_FROM` | optional from address |
| Secret | `SMTP_USERNAME` | your SMTP login email |
| Secret | `SMTP_PASSWORD` | an app password, **never** a personal account password |
| Secret | `REPORT_TOKEN` | optional; set **the same** local environment variable on the receiver |

The email contains commit SHA, status, total/passed/failed counts, individual test names and outcomes, plus the full JSON attachment. After configuring the above, push to trigger a workflow and retain screenshot evidence of delivered emails on both pass and fail runs. If using Gmail, your account needs an eligible app password or alternative SMTP provider. Never commit credentials, tokens, or `.env` files. For simplest setup, leave `REPORT_TOKEN` unset on both sides; the receiver is bound strictly to loopback.

## Evidence and submission checklist

1. Repository URL showing complete source, workflow, tests, receiver, and README.
2. Screenshot of Flask submission form, saved valid submission, rejected missing registration, rejected bad URL.
3. GitHub Actions screenshots from three distinct commits: **pass, fail, fix/pass**.
4. Local `test-report.json` screenshots from passing and failing runs with test details and GitHub metadata.
5. Runner terminal `Listening for Jobs`, receiver terminal POST logs.
6. Pages deployed URL and screenshot, plus proof failing run did not deploy (bonus).
7. Email screenshots for both success and failure (bonus).

**Do not invent a repository URL, workflow run ID, screenshots, or delivered email confirmation.** These require your own GitHub account and actual execution.

## Troubleshooting

- Workflow stuck **Queued**: runner is offline, mislabeled, or not registered to this repository. Check `Settings → Actions → Runners` and `run.cmd`.
- Receiver connection refused: start `python receiver.py`, verify its health URL, and make sure runner is on the **same Windows PC**.
- Failing workflow without failure report: inspect steps `Run actual pytest`, `Automatically send report`, and receiver logs. Ensure `pytest-results.xml` exists or read the synthetic error entry.
- Pages does not deploy: set Pages source to GitHub Actions and make sure test job was green and on main.
- `python` unrecognized: install Python 3.12 and check **Add Python to PATH** in installer.
- SMTP fails: verify port, account app password, sender, network restrictions, and enabled SEND_EMAIL variable.
