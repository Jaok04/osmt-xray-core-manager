# Open Server Management Tools
### Open-source tools for Linux VPS administration, deployment, security and automation.

**Starting with Xray Core Manager.**

---

## Overview

Open Server Management Tools is an emerging open-source initiative focused on making Linux VPS administration more accessible, consistent and manageable.

The initiative aims to build a collection of modular tools that help server administrators deploy applications, manage services, strengthen security and automate recurring operational tasks.

The project is starting with **Xray Core Manager**, a Bash-based administration tool for Xray-core. This first component establishes the engineering foundations and development principles for the broader initiative.

> Xray Core Manager is the starting point, not the final destination. The long-term goal is to develop practical, well-documented open-source tools that reduce the complexity of administering Linux VPS environments.

## Mission

Provide practical, transparent and modular software that simplifies common VPS administration tasks while preserving administrator control over the system.

## Vision

Build an extensible ecosystem of open-source tools for Linux server operations, covering service management, application deployment, security, monitoring, maintenance and automation.

The initiative is at an early stage. Xray Core Manager is the first project under active development; the other areas described below are directions for future development, not claims of currently available products.

## The project ecosystem

### 1. Xray Core Manager — First project

A modular Bash-based administration tool for Xray-core on Linux.

Its purpose is to provide a structured interface and a controlled foundation for managing Xray-core versions, connection definitions and VLESS user records.

Current implementation includes:

- Modular command-line menu and administration modules.
- Catalog of 38 connection modes.
- Local connection records maintained as drafts.
- VLESS user records associated with draft connections.
- Neutral VLESS data model and a version-specific adapter for Xray-core 26.10.31.
- Controlled Xray binary and geodata package administration.
- Centralized paths and separated application data.
- Atomic JSON persistence and shared locking for related operations.
- Backup and guarded uninstallation workflows.
- Functional, integration, persistence and concurrency tests.

**Important implementation boundary:** connection and user records are not automatically applied to a running Xray instance. The project does not currently create or manage systemd units, start or restart Xray, or modify firewall, SSH or network settings.

See the [Xray Core Manager implementation details](#xray-core-manager-status-and-scope) below and the `docs/` directory for stage-level documentation.

### 2. VPS Deployment Tools — Planned

Future tools may help administrators:

- Deploy web applications and backend services.
- Configure application runtimes and dependencies.
- Standardize repeatable deployment procedures.
- Manage service configuration and lifecycle.
- Automate routine installation and update tasks.

### 3. VPS Security Tools — Planned

Future work may focus on:

- Linux server security checks and configuration audits.
- System hardening recommendations and controlled application.
- Firewall and access-control management.
- Security-oriented service configuration.
- Logging, diagnostics and security monitoring.

Security changes must be explicit, documented and reversible wherever practical.

### 4. Server Operations Tools — Planned

Potential areas include:

- Resource and service monitoring.
- Backup and recovery workflows.
- System health checks and diagnostics.
- Maintenance automation.
- Operational reporting and inventory.

These areas represent the initiative's direction. They are not currently released products.

## Engineering principles

The initiative follows a set of principles intended to keep administration tools predictable and maintainable:

1. **Administrator control:** privileged or disruptive operations must be explicit.
2. **Validation before application:** validate inputs and generated configuration before changing a running service.
3. **Separation of concerns:** keep application code, configuration, state, logs, cache and backups separate.
4. **Safe persistence:** prefer validated, atomic updates for important state.
5. **Transparent operation:** document what a tool does, what it does not do and what remains unverified.
6. **Modular architecture:** separate functionality into components with clear responsibilities.
7. **Testable behavior:** use isolated tests for validation, failure handling and concurrency.
8. **No silent assumptions:** do not invent defaults for security-sensitive settings or present missing measurements as zero.

## Technology direction

The first project currently uses:

- Bash 5.2+
- Linux
- Ubuntu 24.04 LTS (reference platform)
- Xray-core 26.10.31 (version targeted by the current adapter)
- JSON for local records
- ShellCheck and shfmt for static checks
- Shell-based functional and integration tests

Future tools may use other technologies when they provide a clear technical benefit. No single implementation language is mandated for the entire initiative.

---

## Xray Core Manager: status and scope

### Current status

**Development version:** `0.2.0-dev`  
**Primary platform:** Ubuntu 24.04 LTS, amd64  
**Shell requirement:** Bash 5.2 or newer  
**Development branch:** `main`

The repository contains a working modular implementation and a growing test suite. It is an early-stage project and is not presented as a production-ready, fully integrated server control panel.

### Implemented foundations

- Main launcher and modular menu.
- Connection catalog and local draft records.
- VLESS user record management.
- Neutral VLESS model and Xray 26.10.31 adapter.
- Controlled binary and geodata installation/reinstallation workflow.
- Centralized filesystem path definitions.
- Atomic JSON storage and shared integrity locking.
- Backup and guarded uninstallation logic.
- Functional, integration, fault-injection and concurrency tests.

### Current limitations

The following boundaries are important when evaluating the current implementation:

- Creating or editing a draft does not generate and apply a live runtime configuration automatically.
- Xray service lifecycle and systemd unit management are not implemented.
- Firewall, SSH and network configuration are not modified.
- Port checks are observations and logical reservations; they do not reserve a socket against external processes.
- The VLESS adapter targets Xray-core 26.10.31.
- The uninstallation workflow still requires broader end-to-end recovery testing in an isolated environment before it can be considered operationally validated for real installations.
- Profiles, domains, certificates and history have centralized planned paths, but several storage consumers remain to be implemented.
- Static and isolated tests do not establish production readiness or end-to-end connectivity.

### Repository structure

| Directory | Responsibility |
|---|---|
| `bin/` | Application entry point |
| `config/` | General configuration, paths, catalog and Xray version |
| `lib/` | Shared utilities and persistence |
| `modules/` | Connections, users, Xray administration and uninstallation |
| `docs/` | Architecture, technical decisions and implementation stages |
| `tests/` | Functional, integration, persistence and concurrency tests |

### Validation

From the repository root:

```bash
bash -n bin/xray-manager config/paths.sh lib/*.sh modules/*.sh tests/*.sh
shellcheck -x bin/xray-manager config/paths.sh lib/*.sh modules/*.sh tests/*.sh
shfmt -d bin/xray-manager config/paths.sh lib/*.sh modules/*.sh tests/*.sh

for test in tests/*.sh; do
  bash "$test"
done
```

The `tests/xray_vless_integration.sh` test requires a validation Xray binary supplied through `XRAY_BIN` or available in the configured validation cache.

The repository documentation describes the exact scope and prerequisites of each test. A successful test run should not be interpreted as proof of production deployment readiness.

## Roadmap

The roadmap is directional and subject to design review, implementation and testing.

### Xray Core Manager

- [x] Modular foundation and command-line menu.
- [x] Connection catalog and draft records.
- [x] VLESS user record management.
- [x] Version-specific VLESS adapter and isolated configuration validation.
- [x] Initial controlled binary administration.
- [x] Atomic persistence and concurrency safeguards.
- [ ] Complete runtime configuration generation and validation workflow.
- [ ] Transactional configuration application and rollback.
- [ ] Controlled systemd service lifecycle management.
- [ ] Certificate and domain workflows.
- [ ] Profiles, history and operational reporting.
- [ ] Full recovery and installation testing on disposable VPS environments.

### Broader initiative

- [ ] Define a reusable foundation for deployment tools.
- [ ] Develop application deployment and service management utilities.
- [ ] Design security audit and hardening tools.
- [ ] Develop monitoring, backup and maintenance utilities.
- [ ] Establish shared documentation, testing and release practices across tools.

A roadmap item is not an implemented feature. Progress will be reflected in the repository as functionality is developed and validated.

## Open source and contributions

The project is being developed as an open-source effort. As the implementation and documentation mature, contributions, issue reports, design feedback and reproducible test cases will help guide its evolution.

Before contributing:

1. Review the implementation notes in `docs/`.
2. Check the current code and tests before proposing a change.
3. Describe the behavior being changed and its security implications.
4. Include tests for new behavior and failure cases where practical.
5. Avoid submitting secrets, private keys, server credentials or production configuration.

Contribution guidelines and licensing details should be published explicitly as the project prepares for wider public collaboration.

## Project status and transparency

This is a new project with a long-term objective. It does not claim an established user base, adoption metrics or production deployment record.

Its value proposition is the problem it seeks to address, the technical foundation already developed and a clear commitment to incremental, testable and documented implementation.

The first milestone is to mature Xray Core Manager. The broader objective is to grow from that starting point into a set of useful tools for Linux VPS administrators.

---

**Project:** Open Server Management Tools  
**First component:** Xray Core Manager  
**Repository:** `xray-core-manager`  
**Development status:** Early stage / active development
