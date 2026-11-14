# OSMT Tools Catalog

This catalog turns the project vision into candidate tools. Every item below is a proposal unless explicitly marked as the current first component. A concept becomes an implementation only after its scope, tests, support matrix and maintenance plan are approved.

## Current first component

### Xray Core Manager
**User:** administrators who operate Xray-core on a Linux VPS.  
**Purpose:** provide a modular command-line foundation for Xray-core administration.  
**Current state:** early development. See the root README and stage documents for implemented behavior and limitations.

## Candidate tools

| Candidate | Primary user problem | First useful scope | Beginner-friendly output |
|---|---|---|---|
| VPS First-Run Assistant | "What is on this server, and is it ready?" | Read-only OS, architecture, CPU, memory, disk, network and package inventory | Plain-language readiness report |
| App Deploy Assistant | "How do I deploy this app reliably?" | One supported stack, dependency checks, deployment plan, service and reverse-proxy preflight | Step-by-step deployment summary |
| Service Desk for Linux | "Why is my app not running?" | Inspect systemd status, recent logs and common failure conditions | Explain status, logs and safe next checks |
| Domain & TLS Assistant | "How do I connect a domain securely?" | DNS checks, reverse-proxy preflight and certificate status | Checklist showing missing records and certificate state |
| VPS Security Baseline | "What common server risks should I review?" | Read-only SSH, listening-port, permission and firewall inventory | Evidence-based findings and remediation guidance |
| Backup & Restore Assistant | "Can I recover if something breaks?" | Backup target checks, archive verification and restore rehearsal | Backup status and tested recovery instructions |
| VPS Health Monitor | "Is the server running out of resources?" | CPU, memory, disk and selected service checks | Local health report and threshold warnings |
| Linux Troubleshooting Guide | "What does this error mean?" | Collect sanitized diagnostics and match documented failure patterns | Guided explanations and next steps |

## Shared behavior expected from every tool

- Inspect before modifying.
- Explain prerequisites and expected impact.
- Show a plan before privileged changes.
- Ask for explicit approval for destructive or externally visible actions.
- Avoid collecting or printing secrets.
- Keep logs useful but sanitized.
- Validate configuration before applying it.
- Create backups or recovery points where practical.
- Report what changed and what could not be verified.
- Provide tests and a documented support matrix.

## Suggested implementation order

1. Complete and validate Xray Core Manager.
2. Build VPS First-Run Assistant as a read-only project with a small, testable scope.
3. Build App Deploy Assistant for one explicitly supported stack.
4. Add service diagnostics and lifecycle support.
5. Add domain/TLS assistance.
6. Add security, backup, monitoring and troubleshooting tools as independently maintainable projects.

This sequence prioritizes beginner value while limiting operational risk. It is a proposal, not a delivery commitment.
