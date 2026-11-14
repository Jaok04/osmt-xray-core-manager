# Project Vision — Open Server Management Tools (OSMT)

**Make Linux VPS administration more approachable without hiding the system from the people who operate it.**

OSMT is an independent, early-stage open-source initiative to build practical tools that help people understand, deploy, secure, and operate Linux VPS environments. Its purpose is not to replace system knowledge with opaque automation. It is to make common operational work easier to understand, safer to perform, and simpler to repeat while keeping administrators informed and in control.

This document describes the project's purpose, intended users, product philosophy, and long-term direction. Product families and tools that are not identified as current implementations are proposals, not released capabilities.

## 1. The problem

Deploying software often introduces a second discipline: operating the server on which it runs.

People who are beginning their software careers—or learning independently—may need to understand Linux permissions, runtimes, reverse proxies, DNS, TLS, services, firewall policy, backups, logs, and recovery at the same time they are learning to build applications.

Command-line procedures are flexible and powerful, but a person unfamiliar with a system may not know which commands are safe, what files or services a change will affect, or how to recover if something fails. Large hosting control panels can also be excessive for someone managing a modest VPS who wants to understand and control the underlying system.

This creates an opportunity for focused utilities that guide users through well-defined tasks, explain what is happening, and make important decisions visible.

## 2. Mission

Build a growing collection of free and open-source tools that make common Linux VPS administration tasks easier to understand, safer to perform, and simpler to repeat.

OSMT is intended especially for:

- Students and self-taught developers preparing to deploy their first application.
- Junior developers beginning to work with cloud servers.
- Independent developers maintaining their own VPS infrastructure.
- Small teams that need repeatable operational workflows without a heavyweight platform.
- Experienced administrators who prefer focused, inspectable utilities.

The primary design audience is a beginner who can follow technical instructions but may not yet know Linux server conventions. The tools should reduce repetitive operational work without removing the user's ability to inspect, understand, and control the server.

## 3. Product philosophy: Guided Automation

Guided Automation is the central product principle of OSMT.

A tool should help users understand an operation as well as perform it. Automation should make a safe procedure repeatable—not make a dangerous procedure easier to trigger accidentally.

Where a tool performs system changes, its intended workflow is to:

1. **Explain** the task, prerequisites, and possible impact.
2. **Inspect** the current system before proposing changes.
3. **Preview** planned actions and affected files, services, or settings.
4. **Validate** inputs and generated configuration.
5. **Ask for approval** before privileged, disruptive, or destructive actions.
6. **Prepare recovery** through a backup or recovery point when appropriate.
7. **Apply changes** in controlled stages.
8. **Verify** the outcome and report what happened.
9. **Explain recovery** or undo steps where those capabilities are supported.

Not every tool needs every step. A read-only inspection tool should remain read-only. A tool must not imply that rollback, recovery, or verification is available unless it has actually implemented and tested that behavior.

The administrator remains the decision-maker. The tool's role is to make the operation clearer and more manageable.

## 4. Who OSMT is for

OSMT aims to serve people who want practical help with server operations without surrendering visibility or control.

### Learners and early-career developers

They need understandable explanations, clear prerequisites, safe defaults, and a way to learn why an operation is necessary—not just a command to copy.

### Independent developers and small teams

They need repeatable procedures for deploying and maintaining applications without adopting a large platform or building every operational script from scratch.

### Experienced administrators

They may value small, modular utilities that are inspectable, predictable, and easy to adapt to a particular environment.

The common need across these groups is clarity: what is being inspected, what is proposed, what will change, and what has been verified.

## 5. Product ecosystem

OSMT is envisioned as a collection of focused tools. Each tool should solve a bounded problem, be useful on its own, and integrate with other components only where that provides a clear benefit.

The following product families describe the intended direction. They are **candidate areas, not a claim that these tools have already been implemented or released**.

### 5.1 Server onboarding and fundamentals

Potential capabilities:
- VPS first-run checklist and read-only system inventory.
- Operating system, architecture, CPU, memory, storage, and network overview.
- Dependency and package-manager checks.
- SSH access review and basic service explanations.

**Intended outcome:** understand the server before changing it.

### 5.2 Application deployment

Potential capabilities:
- Guided deployment for selected application stacks.
- Runtime and dependency preparation.
- Environment-file templates that avoid exposing secrets.
- Reverse-proxy and TLS preflight checks.
- Deployment verification and rollback planning.

**Intended outcome:** move from source code to a running application through a documented, repeatable path.

### 5.3 Service management

Potential capabilities:
- systemd unit generation and validation.
- Service status and lifecycle assistance.
- Log inspection and health checks.
- Controlled update workflows.

**Intended outcome:** understand how an application runs, starts at boot, records errors, and recovers.

### 5.4 Networking and connectivity

Potential capabilities:
- DNS and port diagnostics.
- Reverse-proxy assistance.
- TLS certificate workflows.
- Local connectivity checks.

**Intended outcome:** understand how traffic reaches an application and where connectivity problems may occur.

### 5.5 Security and hardening

Potential capabilities:
- SSH configuration review.
- Exposed-port and listening-service inventory.
- Firewall posture and file-permission review.
- Evidence-based hardening guidance.

**Intended outcome:** recognize common risks and make deliberate, reversible improvements. Security tools must report evidence and limitations; they must never claim to guarantee security.

### 5.6 Backups and recovery

Potential capabilities:
- Backup scheduling and retention review.
- Integrity verification.
- Configuration snapshots.
- Restore rehearsal and recovery guidance.

**Intended outcome:** know what is backed up and how to restore it.

### 5.7 Monitoring and maintenance

Potential capabilities:
- Resource and service overview.
- Disk and certificate-expiration alerts.
- Update and maintenance reports.
- Cleanup guidance.

**Intended outcome:** identify operational issues early and understand routine maintenance.

### 5.8 Learning and troubleshooting

Potential capabilities:
- Guided diagnostic collection.
- Error and log explanations.
- Configuration validation.
- Risk-labelled command references and incident reports.

**Intended outcome:** learn from operational problems instead of blindly copying commands.

## 6. First implementation: Xray Core Manager

Xray Core Manager is the first implementation within OSMT. It is a modular, Bash-based foundation for administering Xray-core on Linux.

The current development baseline includes a command-line launcher and menu, a catalog of connection modes, local draft connection records, VLESS user records, a neutral VLESS data model, a version-specific adapter for Xray-core 26.10.31, controlled binary and geodata administration, atomic JSON persistence, locking, backup and guarded uninstallation workflows, and shell-based test scripts.

It is intentionally not described as a finished control panel or production-ready service manager.

Current operational boundaries include:
- Creating or editing a draft does not apply a configuration to a running Xray instance.
- systemd unit creation and service lifecycle management are not currently implemented.
- Firewall, SSH, and general network settings are not modified.
- Port checks are observations and logical reservations; they do not reserve a socket against external processes.
- The VLESS adapter targets Xray-core 26.10.31.
- The uninstallation workflow still needs broader end-to-end recovery testing in an isolated environment.
- Several profile, domain, certificate, and history workflows remain pending.

The first objective is to mature this component carefully, document its supported workflows, and validate its behavior before treating it as a stable release. Future OSMT tools may use different languages or deployment models where appropriate.

## 7. Shared engineering standards

Every OSMT tool should aim for the following standards:

- **Clear scope:** explain the problem, intended user, prerequisites, and supported platforms.
- **Understandable documentation:** use beginner-oriented terminology and explain important system concepts.
- **Read-only first:** inspect before mutating system state.
- **Visible impact:** preview consequential operations and identify affected resources.
- **Explicit approval:** require user confirmation for privileged, disruptive, or destructive changes.
- **Least privilege:** request only the permissions required for the task.
- **Secret protection:** avoid collecting, exposing, or logging credentials and sensitive values.
- **Validation:** check inputs and generated configuration before applying changes.
- **Recovery:** provide backups, rollback, or documented recovery paths where practical.
- **Predictability:** prefer idempotent behavior where feasible.
- **Testing:** cover normal paths, invalid inputs, and failure conditions.
- **Honest reporting:** distinguish observed facts, recommendations, and unverified assumptions.
- **Transparent limitations:** document compatibility, security boundaries, and unsupported behavior.
- **Respect for privacy:** do not add telemetry or external network calls without clear documentation and user consent.

These are shared design goals. Each implementation must demonstrate which standards it meets; listing a standard here does not mean every current component already satisfies it.

## 8. Technology and implementation approach

OSMT is technology-neutral. Each tool should use the language, architecture, and deployment model best suited to its scope and maintenance needs.

The first component, Xray Core Manager, currently uses Bash 5.2+, Linux, Ubuntu 24.04 LTS amd64 as its reference platform, JSON for local records, and Xray-core 26.10.31 for its version-specific adapter. ShellCheck, shfmt, and shell-based tests are part of its development workflow.

Future tools are not required to use Bash or share a single runtime. Modularity and clear operational contracts matter more than uniformity for its own sake.

## 9. AI and external services

OSMT's mission does not depend on a particular AI provider, cloud platform, or commercial service. Core tools should remain useful for their documented tasks without requiring an AI service.

AI-assisted features may be considered where they solve a clearly defined problem—for example, explaining diagnostic output or helping a user understand a proposed operation. Such features should be optional, transparent about what information is sent to an external service, and designed so that the administrator retains approval and control.

An AI assistant must not silently execute privileged operations or substitute an unverified explanation for system evidence. External integrations should be documented, and sensitive server data must not be transmitted without clear user awareness and consent.

## 10. What progress and success mean

OSMT is an early-stage initiative. Its progress should be judged by useful, verifiable outcomes rather than unsupported popularity claims.

Evidence of progress may include:
- Beginners completing documented tasks with fewer avoidable errors.
- Reproducible procedures and clear support boundaries.
- Tests that cover normal operation and failure conditions.
- Issues resolved through fixes that can be reproduced and verified.
- Documentation improvements and contributions from people learning server administration.
- Releases with clear change notes, prerequisites, and known limitations.
- Recovery procedures demonstrated in isolated environments.

Stars, downloads, and other adoption metrics should be reported only when they can be measured honestly. The project does not claim an established user base or production deployment record.

## 11. Long-term direction

The intended sequence is incremental:

1. Mature Xray Core Manager and document its supported workflows.
2. Establish consistent contribution, testing, security, and release practices.
3. Design a small, read-only VPS First-Run Assistant around a clearly defined beginner use case.
4. Validate that tool in real, isolated test environments.
5. Develop deployment and service-operation assistance based on demonstrated needs.
6. Expand into networking, security, backups, monitoring, and troubleshooting as each scope can be implemented and maintained responsibly.

The roadmap is a planning guide, not a delivery promise. Priorities may change with user feedback, technical evidence, and maintenance capacity.

## 12. The principle behind the project

A useful server tool should do more than execute a command. It should help the person operating the system understand what is happening, why a change is proposed, what could go wrong, and how to verify the result.

OSMT aims to make that kind of practical, transparent assistance available through focused open-source tools—one useful problem at a time.

**Learn. Deploy. Secure. Operate.**
