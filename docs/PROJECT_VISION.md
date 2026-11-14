# Project Vision — Open Server Management Tools

**Make Linux VPS administration more approachable without hiding the system from the people who operate it.**

## The problem

Developers who are new to professional software work often encounter a second discipline when they deploy an application: server administration. Linux permissions, runtimes, reverse proxies, DNS, TLS, services, firewall policy, backups, logs and recovery can create a steep learning curve.

Raw command-line procedures are flexible, but beginners may not know which commands are safe, what a configuration changes or how to recover from failure. Large hosting panels can be excessive for someone who wants to understand and control a modest VPS.

## Mission

Create a growing collection of free and open-source tools that make common Linux VPS administration tasks easier to understand, safer to perform and simpler to repeat—especially for students, junior developers, self-taught developers and independent builders.

The tools should reduce repetitive operational work without removing the user's ability to inspect, understand and control the server.

## Product philosophy: guided automation

A tool should help users understand an operation as well as perform it. A typical workflow should:

1. Explain the task and prerequisites.
2. Inspect the current system before proposing changes.
3. Show planned actions and affected files or services.
4. Validate inputs and configuration.
5. Request explicit approval for privileged or disruptive changes.
6. Create a backup or recovery point when appropriate.
7. Apply changes in controlled stages.
8. Verify the result and report what happened.
9. Explain undo or recovery steps when supported.

Automation should make a safe procedure repeatable—not make a dangerous procedure easier to trigger accidentally.

## Who we want to help

- Students and self-taught developers preparing to deploy their first application.
- Junior developers beginning to work with cloud servers.
- Independent developers maintaining their own VPS infrastructure.
- Small teams that need repeatable operational workflows without a heavyweight platform.
- Experienced administrators who prefer focused, auditable utilities.

The primary design audience is a beginner who can follow technical instructions but may not yet know Linux server conventions.

## Product families

### 1. Server onboarding and fundamentals
Potential tools: VPS first-run checklist, read-only system inventory, dependency checker, SSH access review and basic service explainer.

**Beginner outcome:** understand the server before changing it.

### 2. Application deployment
Potential tools: guided deployment for selected application stacks, runtime installers, reverse-proxy assistant, domain/TLS workflow, environment-file templates, container deployment helper and rollback assistant.

**Beginner outcome:** move from source code to a running application through a documented path.

### 3. Service management
Potential tools: systemd unit generator and validator, service lifecycle controls, log inspection, health checks and safe update workflows.

**Beginner outcome:** understand how an application runs, starts at boot, logs errors and recovers.

### 4. Networking and connectivity
Potential tools: DNS and port diagnostics, reverse-proxy manager, TLS certificate assistant and local connectivity checks.

**Beginner outcome:** understand how traffic reaches an application.

### 5. Security and hardening
Potential tools: SSH audit, exposed-port inventory, firewall review, permission audit and hardening checklist.

**Beginner outcome:** recognize common risks and apply deliberate, reversible improvements. Security tools must report evidence and limitations; they must not claim to guarantee security.

### 6. Backups and recovery
Potential tools: backup scheduler, integrity verification, restore rehearsal, configuration snapshots and retention review.

**Beginner outcome:** know what is backed up and how to restore it.

### 7. Monitoring and maintenance
Potential tools: resource overview, service monitoring, disk/certificate alerts, update reports and cleanup assistant.

**Beginner outcome:** identify problems early and understand routine maintenance.

### 8. Learning and troubleshooting
Potential tools: guided diagnostic bundles, error explanations, configuration validators, risk-labelled command references and incident reports.

**Beginner outcome:** learn from operational problems instead of blindly copying commands.

## First component: Xray Core Manager

Xray Core Manager is the first implementation. It is a modular Bash-based foundation for administering Xray-core. Current code includes a menu, connection catalog, local draft records, VLESS user records, a neutral VLESS model, a version-specific Xray adapter, controlled binary administration, atomic JSON persistence, locking and tests.

It is intentionally not described as a finished control panel. Runtime application, systemd lifecycle management, firewall/SSH/network changes and several certificate/profile workflows remain outside the current operational scope or are pending.

The first objective is to mature this component carefully. Future tools may use different languages or deployment models where appropriate.

## Shared engineering standards

Every tool should aim for:
- Clear prerequisites and supported-platform declarations.
- Beginner-oriented documentation and terminology.
- Read-only inspection before mutation.
- Explicit previews for impactful operations.
- Least privilege and minimal permissions.
- Safe handling of secrets and credentials.
- Input validation and clear error messages.
- Backups, rollback or documented recovery where practical.
- Idempotent behavior where feasible.
- Tests for normal paths, invalid inputs and failures.
- Transparent compatibility and security limitations.
- No telemetry or external network calls without clear documentation and user consent.

## What success means

Useful evidence includes beginners completing tasks with fewer errors, clear documentation, reproducible workflows, issues leading to verified fixes, contributions from people learning server administration, regression tests and releases with documented limitations.

Stars are not the only measure of value. Metrics should be reported only when they can be measured honestly.

## Long-term direction

1. Mature Xray Core Manager and document its supported workflows.
2. Establish contribution, release, security and testing practices.
3. Design one small deployment tool around a clearly defined beginner use case.
4. Validate it in real, isolated test environments.
5. Expand into service operations, security, backups and monitoring based on demonstrated needs.

The objective is not to promise a large suite immediately. It is to build a trustworthy ecosystem incrementally.
