![Open Server Management Tools](assets/brand/brand-banner.svg)

# Open Server Management Tools

**Practical open-source tools that help developers learn, deploy, secure and operate Linux VPS environments.**

Starting with **Xray Core Manager**.

[Project vision](docs/PROJECT_VISION.md) · [Roadmap](docs/ROADMAP.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

## Why this project exists

Developers beginning their careers often face a second discipline as soon as they deploy an application: server administration. Linux permissions, runtimes, reverse proxies, DNS, TLS, services, firewalls, backups and logs can create a steep learning curve.

**Open Server Management Tools (OSMT)** is an early-stage open-source initiative to make common Linux VPS tasks easier to understand, safer to perform and simpler to repeat—especially for students, junior developers, self-taught developers and independent builders.

The goal is not to hide how servers work. It is to make routine operations more approachable while keeping users informed and in control.

## A toolkit that grows with the developer

OSMT is planned as a collection of focused, interoperable tools. Each should explain what it will change, validate inputs and provide recovery paths where practical.

| Area | Planned tools and capabilities | Intended benefit |
|---|---|---|
| Server foundations | VPS first-run assistant, system inventory, dependency checker, SSH review | Understand and prepare a new server |
| Application deployment | Guided app deployment, runtime installers, environment templates, container helper | Move from source code to a running service |
| Service operations | systemd unit builder, service controls, log viewer, health checks | Understand and operate application services |
| Networking and domains | DNS diagnostics, reverse-proxy assistant, TLS certificate helper | Configure application connectivity |
| Security and hardening | SSH audit, firewall review, permission audit, exposed-port inventory | Recognize and reduce common risks |
| Backups and recovery | Backup scheduler, restore assistant, configuration snapshots | Protect data and rehearse recovery |
| Monitoring and maintenance | Resource dashboard, service monitoring, disk alerts, update reports | Understand server health |
| Learning and diagnostics | Guided troubleshooting, command explanations, config validator | Learn while solving operational problems |

These are **product directions, not released features**. See the [roadmap](docs/ROADMAP.md).

## First project: Xray Core Manager

Xray Core Manager is the first component: a modular Bash-based administration tool for Xray-core on Linux.

### Current implementation

- Modular command-line launcher and administration menu.
- Catalog of 38 connection modes.
- Local connection records stored as drafts.
- VLESS user records associated with draft connections.
- Neutral VLESS data model and a version-specific adapter for Xray-core 26.10.31.
- Controlled Xray binary and geodata package administration.
- Centralized filesystem paths and separated application data.
- Atomic JSON persistence and shared locking for related operations.
- Backup and guarded uninstallation workflows.
- Functional, integration, persistence-fault and concurrency tests.

### Important operational boundaries

This is an early development version, **not a production-ready control panel**.

- Creating or editing a draft does not apply a configuration to a running Xray instance.
- The project does not currently create or manage systemd units, or start/restart Xray.
- It does not modify firewall, SSH or network settings.
- Port checks are observations and logical reservations; they do not reserve a socket against external processes.
- The VLESS adapter targets Xray-core 26.10.31.
- The uninstallation workflow needs broader end-to-end recovery testing in an isolated environment.
- Profiles, domains, certificates and history have centralized planned paths, but several storage consumers remain to be implemented.

The docs directory contains implementation notes, decisions, contracts and limitations. Isolated test success is not proof of production readiness or end-to-end connectivity.

## Design principles

1. **Beginner-friendly, not opaque:** explain operations and consequences.
2. **Administrator control:** privileged or destructive changes require explicit intent.
3. **Validate before applying:** check inputs and generated configuration.
4. **Safe by default:** prefer least privilege, backups and rollback.
5. **Transparent status:** distinguish implemented, experimental, planned and unsupported behavior.
6. **Modular architecture:** keep tools focused and independently testable.
7. **Reproducible operations:** document procedures that can be repeated and audited.
8. **Evidence-based claims:** tests and security claims must be supported by evidence.

## Technology

The first component currently uses Bash 5.2+, Linux, Ubuntu 24.04 LTS as its reference platform, JSON for local records and Xray-core 26.10.31 for its version-specific adapter. ShellCheck, shfmt and shell-based tests are used in development.

The wider initiative is not restricted to one language. Future tools may use the technology best suited to their purpose.

## Repository layout

| Path | Purpose |
|---|---|
| bin/ | Application entry point |
| config/ | Configuration, paths, protocol catalog and Xray version |
| lib/ | Shared utilities and persistence |
| modules/ | Connections, users, Xray administration and uninstallation |
| docs/ | Architecture, decisions, vision and roadmap |
| tests/ | Functional, integration, persistence and concurrency tests |
| assets/brand/ | Project identity assets |

## Validation

From the repository root:

```bash
bash -n bin/xray-manager config/paths.sh lib/*.sh modules/*.sh tests/*.sh
shellcheck -x bin/xray-manager config/paths.sh lib/*.sh modules/*.sh tests/*.sh
shfmt -d bin/xray-manager config/paths.sh lib/*.sh modules/*.sh tests/*.sh

for test in tests/*.sh; do
  bash "$test"
done
```

The Xray VLESS integration test requires a validation Xray binary supplied through XRAY_BIN or available in the configured validation cache. Read each test and its documentation for prerequisites and scope.

## Roadmap

The first priority is to mature Xray Core Manager before expanding into additional tools.

- [x] Modular Xray Manager foundation.
- [x] Draft connection and VLESS user record workflows.
- [x] Version-specific VLESS adapter and isolated configuration validation.
- [x] Initial controlled binary administration.
- [x] Atomic persistence and concurrency safeguards.
- [ ] Complete runtime configuration generation, validation, application and rollback.
- [ ] Implement controlled systemd service lifecycle management.
- [ ] Complete certificate, domain, profile and history workflows.
- [ ] Expand isolated installation, recovery and upgrade testing.
- [ ] Design and release the first beginner-focused VPS deployment utility.
- [ ] Develop security, backup, monitoring and troubleshooting tools as separate projects.

See [docs/ROADMAP.md](docs/ROADMAP.md). Roadmap items are plans, not implemented features.

## Open source and contributions

OSMT is intended to be developed in the open, with contribution paths that welcome people who are learning. Bug reports, documentation improvements, reproducible tests and focused proposals are valuable contributions.

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Report security issues using [SECURITY.md](SECURITY.md).

## Project status

**Stage:** Early-stage initiative / active development  
**First component:** Xray Core Manager  
**Reference platform:** Ubuntu 24.04 LTS, amd64  
**Development branch:** main

This project does not claim an established user base, adoption metrics or production deployment record. Its current value is the problem it addresses, the implementation already present, documented engineering constraints and a commitment to incremental, testable development.

**Make server operations more approachable, one useful open-source tool at a time.**
