# Anti-Performance Throttling Booster

A local Windows-oriented dashboard for monitoring CPU, memory, processes, and
network use, detecting suspected throttling, and applying only confirmed,
reversible priority reductions to eligible background processes.

## Run locally

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python dashboard.py
```

The dashboard uses a dark theme with purple accents. Monitoring data stays on
the machine. It reads aggregate network statistics only; it does not inspect
network content. Select the workload you want to protect before any safe
optimization can be applied.

## GitHub Actions CI/CD

Continuous integration and delivery is configured in
`.github/workflows/ci-cd.yml`. It runs on every pull request and every push to
`main`, then installs dependencies, compile-checks the application, runs the
test suite, packages a numbered Windows ZIP, and publishes that ZIP as a
GitHub Actions artifact.

After pushing the project to GitHub, open the repository's **Actions** tab,
select **PulseBoost CI/CD**, and download the package from the successful run's
**Artifacts** section. The workflow can also be started manually from the
Actions tab using **Run workflow**.

`Jenkinsfile` remains available only as an optional self-hosted alternative;
GitHub Actions is the recommended CI/CD path for this project.
