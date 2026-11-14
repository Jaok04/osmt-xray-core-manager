# Product Roadmap

This roadmap describes intended direction. A planned item is not an implemented or released feature. Status changes should be supported by code, tests and documentation.

## Current baseline: Xray Core Manager

**State:** early development, version 0.2.0-dev.

Implemented foundations:
- Modular Bash launcher and menu.
- Connection catalog and draft records.
- VLESS user draft records.
- Neutral VLESS model and Xray 26.10.31 adapter.
- Controlled binary/geodata administration.
- Centralized paths, atomic JSON persistence and shared locking.
- Backup and guarded uninstallation workflows.
- Functional, integration, fault-injection and concurrency tests.

Runtime configuration application and systemd service management are not yet implemented. See the root README and stage documents for all operational boundaries.

## Phase 1 — Mature the first tool
**Priority: highest**

- [ ] Complete configuration lifecycle: build, validate, preview, backup, apply, verify and rollback.
- [ ] Implement controlled systemd integration after service contracts and recovery behavior are defined.
- [ ] Complete certificate and domain workflows.
- [ ] Complete profiles and history persistence.
- [ ] Test install, upgrade, failure and recovery on disposable VPS instances.
- [ ] Publish prerequisites and a tested support matrix.
- [ ] Prepare a tagged release only after release criteria are met.

**Acceptance:** workflows are reproducible in isolation, failures do not silently corrupt state, and supported/unsupported behavior is explicit.

## Phase 2 — VPS First-Run Assistant
A beginner-focused, read-only onboarding utility.

Candidate scope:
- OS, architecture, CPU, memory, storage and network inventory.
- Package manager and service manager detection.
- Time synchronization, disk space and basic update checks.
- Plain-language explanations and a local report.
- Optional remediation steps, each separately confirmed.

**Acceptance:** inspection is safe by default, changes nothing, and distinguishes facts from recommendations.

## Phase 3 — App Deploy Assistant
A guided deployment utility, starting with one carefully selected application stack.

Candidate scope:
- Dependency and runtime checks.
- Source preparation and deployment profiles.
- Environment-file templates without collecting or logging secrets.
- Reverse-proxy and TLS preflight.
- systemd unit preview.
- Deployment verification and rollback plan.

**Acceptance:** support one documented stack and deployment path before expanding compatibility.

## Phase 4 — Service Desk for Linux
Candidate scope:
- Inspect systemd services and explain status.
- Show recent journal logs.
- Generate and validate unit files.
- Preview changes and confirm before mutation.
- Verify restart and boot behavior.

**Acceptance:** clear privilege boundaries, no blind restarts, tests for malformed or unsafe unit definitions.

## Phase 5 — VPS Security Baseline
Candidate scope:
- Read-only SSH configuration review.
- Listening-port and exposed-service inventory.
- Firewall posture review.
- File permission and ownership checks.
- Security update status.
- Evidence-based findings and remediation guidance.

**Acceptance:** remediation is opt-in; findings include evidence and limitations; no claim of guaranteed security.

## Phase 6 — Backup, recovery and monitoring
Candidate tools:
- Backup and Restore Assistant.
- VPS Health Monitor.
- Certificate and Domain Watch.
- Maintenance Planner.

Candidate scope:
- Backup schedules, retention and integrity checks.
- Restore rehearsals.
- Resource and service health checks.
- Disk and certificate-expiration alerts.
- Update and maintenance reports.

**Acceptance:** failure states are visible and recovery is tested, not assumed.

## Cross-project release standards

Before public release, each tool should have:
- [ ] Clear problem statement and intended user.
- [ ] Supported OS/platform matrix.
- [ ] Installation and removal instructions.
- [ ] Read-only inspection or dry-run where applicable.
- [ ] Explicit confirmation for privileged/destructive operations.
- [ ] Secret-handling review.
- [ ] Automated and isolated integration tests.
- [ ] Failure and recovery documentation.
- [ ] Security reporting instructions.
- [ ] License and third-party dependency review.
- [ ] Versioned release notes and known limitations.

## Prioritization

Prioritize problems that occur frequently for new VPS administrators, are error-prone when manual, can be automated without hiding important decisions, have a bounded testable scope and can be maintained responsibly.

This roadmap is a planning document, not a delivery promise. Scope and sequencing may change with user feedback and engineering evidence.
