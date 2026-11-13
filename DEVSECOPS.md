# CYBER VIPER DevSecOps

This project includes a local integrated stack for the application, SonarQube,
Prometheus and Grafana. Trivy and automated tests run in GitHub Actions.

## Start the complete local stack

From PowerShell in the repository root:

```powershell
.\devops-tools\start-devops.ps1
```

This builds and starts the CYBER VIPER application and the existing DevOps
services together. It does not remove persistent Docker volumes. Use this
integrated Compose stack rather than starting the root `docker-compose.yml`
at the same time; both define the same application container name.

| Service | URL | Purpose |
|---|---|---|
| CYBER VIPER | http://localhost:8000 | Game application |
| SonarQube | http://localhost:9000 | Code quality |
| Prometheus | http://localhost:9090 | Metrics collection |
| Grafana | http://localhost:3000 | Provisioned dashboards |

The first Grafana login for a new volume is `admin` / `admin`; Grafana asks
you to change the password. Existing Grafana credentials are retained because
the existing `grafana_data` volume is reused.

The application exposes:
- `/health` and `/healthz` for health checks
- `/metrics` for Prometheus metrics

Prometheus automatically scrapes the `web:8000` application service every
15 seconds. Grafana automatically provisions the Prometheus datasource and
the **CYBER VIPER - Application Overview** dashboard.

## Run SonarQube locally

The SonarQube server is local and is not reachable by GitHub-hosted runners.
For a one-off local analysis, run:

```powershell
.\devops-tools\run-sonar-scan.ps1
```

It securely prompts for a SonarQube token and passes it to the scanner
container without writing it to a project file.

## GitHub Actions automation

The workflow `.github/workflows/docker-build-push.yml` runs on pushes to
`main`, pull requests targeting `main`, and manual workflow dispatch.

It automatically:
1. Compiles the Python application and runs the application test suite.
2. Lints and renders the Helm chart.
3. Runs Trivy filesystem scanning for vulnerabilities, misconfigurations and
   secrets.
4. Builds the Docker image and scans it with Trivy for HIGH/CRITICAL
   vulnerabilities.
5. Publishes Trivy JSON reports as a workflow artifact.

### Enable SonarQube in GitHub Actions

To run SonarQube analysis automatically on pushes to `main`, the computer
hosting the local SonarQube instance must also have a GitHub Actions
self-hosted Windows runner installed and online.

In GitHub repository Settings:
- Add repository secret `SONAR_TOKEN` containing a newly generated
  SonarQube user token.
- Add repository variable `SONARQUBE_LOCAL` with value `true`.

Keep the local DevSecOps stack running on that computer. The self-hosted
runner job uses the Docker network `devops-tools_default` to reach
`http://sonarqube:9000`. Do not expose the local SonarQube port publicly.
SonarQube Community Build runs main-branch analysis; pull requests still run
the test, Helm and Trivy checks on GitHub-hosted runners.

## Stop the local stack

```powershell
.\devops-tools\stop-devops.ps1
```

This stops containers but preserves application data, SonarQube data,
Prometheus history and Grafana configuration. Do not use `docker compose down
-v` unless you intentionally want to delete those volumes.
