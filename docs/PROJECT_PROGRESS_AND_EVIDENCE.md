# OSMT — Project Progress & Engineering Evidence

**Open Server Management Tools (OSMT)**  
**Learn. Deploy. Secure. Operate.**

*Institutional project brief · 14 November 2026*  
*Repository: [Jaok04/osmt-xray-core-manager](https://github.com/Jaok04/osmt-xray-core-manager)*

---

## 1. Executive summary

Open Server Management Tools (OSMT) is an independent, early-stage open-source initiative focused on making Linux VPS administration more understandable, safer to perform, and easier to repeat.

OSMT addresses a practical gap in the developer journey: learning to write software does not automatically prepare someone to deploy, secure, troubleshoot, back up, and maintain the Linux server on which that software runs. For students, self-taught developers, junior developers, independent builders, and small teams, this operational transition can be difficult. A single misunderstood command or configuration change can cause downtime, expose a service, or make recovery harder.

OSMT's approach is **Guided Automation**. Rather than hiding system behavior behind opaque automation, tools should explain the task, inspect the current state, show proposed changes, validate inputs, request approval for consequential operations, apply changes in controlled stages, and report what could and could not be verified.

The first implementation is **Xray Core Manager**, a modular Bash-based tool for Xray-core administration on Linux. Its current development baseline includes connection and VLESS user draft management, a version-specific VLESS-to-Xray adapter, controlled binary and geodata administration, centralized storage paths, atomic JSON persistence, shared locking, backup and guarded uninstallation workflows, and a documented test suite.

OSMT is not presented as a finished platform or a production-ready control panel. It is an active, early-stage initiative with a defined mission, an initial implementation, documented engineering decisions, recorded test evidence, known limitations, and an incremental roadmap.

The long-term ambition is to build a collection of focused, free and open-source tools that help more developers become capable and responsible operators of the systems their applications depend on.

## 2. Why this problem matters to developers who are just starting

A developer can learn a programming language, build an application, and still face a substantial barrier when it is time to make that application available to other people.

Operating a VPS introduces a different set of responsibilities:

- Understanding Linux users, groups, permissions, processes, and services.
- Installing runtimes and dependencies without damaging the existing environment.
- Configuring DNS, TLS certificates, reverse proxies, and network access.
- Managing service configuration, logs, updates, and failures.
- Protecting credentials, private keys, application data, and backups.
- Diagnosing problems when a deployment does not behave as expected.
- Planning how to undo or recover from a consequential change.

These tasks are often learned through fragmented tutorials, copied commands, trial and error, and tools designed for experienced administrators. That can leave beginners with two unsatisfactory choices: execute commands they do not fully understand, or avoid self-managed infrastructure because the operational learning curve feels too steep.

OSMT is intended to help bridge this gap.

### The potential benefit

OSMT aims to make server administration a more accessible part of the software-development learning journey:

1. **Reduce the gap between coding and deployment.** Give developers practical, focused tools for the operational work that follows writing an application.
2. **Turn operations into learning opportunities.** Explain what a tool is checking, why a setting matters, and what a proposed action will affect.
3. **Encourage safer habits early.** Make inspection, validation, least privilege, backups, explicit approval, and verification part of the normal workflow.
4. **Make common procedures repeatable.** Replace undocumented one-off command sequences with visible, documented workflows that can be tested and improved.
5. **Support independent builders and small teams.** Provide focused utilities without requiring a large commercial hosting panel or a particular cloud provider.
6. **Create a path from beginner use to deeper understanding.** Keep the underlying Linux behavior inspectable instead of concealing it behind a black box.

The intended benefit is broader than convenience. If beginners can understand and operate their deployment environments with greater confidence, they may be better equipped to publish projects, maintain services, learn infrastructure skills, and participate in open-source software beyond application code.

These are the project's intended outcomes and rationale. OSMT does not currently claim measured educational outcomes, a user base, adoption statistics, or demonstrated impact at scale. Those would require real-world use and evaluation.

## 3. Mission, audience, and product philosophy

### Mission

Build a growing collection of free and open-source tools that help people **learn, deploy, secure, and operate** Linux server environments through understandable and controlled workflows.

### Intended users

- Students learning software development and deployment.
- Self-taught developers moving from local projects to VPS hosting.
- Junior developers gaining practical Linux operations experience.
- Independent developers maintaining their own infrastructure.
- Small teams seeking focused, inspectable operational utilities.
- Experienced administrators who value transparent and narrowly scoped tools.

The primary design audience is a person who can follow technical instructions but may not yet understand the conventions and risks of Linux server administration.

### Guided Automation

Guided Automation is OSMT's shared product principle. Depending on the operation, a tool should:

1. Explain the task, prerequisites, and possible impact.
2. Inspect the current system before proposing changes.
3. Show the proposed actions and affected resources.
4. Validate inputs and generated configuration.
5. Ask for explicit approval before privileged, disruptive, or destructive actions.
6. Create a backup or recovery point where appropriate.
7. Apply changes in controlled stages.
8. Verify the result and report what happened.
9. Explain recovery options and remaining limitations.

Not every operation needs every step. Read-only inspection should remain read-only. A rollback or recovery guarantee must never be implied unless it has actually been implemented and tested.

This philosophy is not a claim that every current component already implements the complete workflow. It is the standard that guides current development and future tools.

## 4. Work completed: project foundation

The public repository contains more than a product description. It has an initial project structure and governance materials:

- Project README and executive overview.
- Project vision and ecosystem map.
- Phased product roadmap and candidate tools catalog.
- Technical decision record and storage architecture documentation.
- Stage documentation for Xray administration, connections, and VLESS users.
- VLESS generator design and version-specific adapter documentation.
- Contribution guidance, security policy, and code of conduct.
- MIT license.
- Issue and pull request templates.
- Initial visual identity assets.
- A GitHub Actions workflow for repository validation.

The repository is public so that its code, documentation, development direction, and future contributions can be inspected openly.

## 5. First implementation: Xray Core Manager

**Current development version:** 0.2.0-dev  
**Implementation:** Bash 5.2+  
**Reference platform:** Ubuntu 24.04 LTS, amd64  
**Version-specific Xray adapter:** 26.10.31

The current documented implementation baseline includes:

- Modular command-line launcher and administration menu.
- Catalog of 38 connection modes.
- Creation, listing, editing, and deletion of local connection records in `draft` state.
- Local VLESS user records associated with VLESS draft connections.
- UUID generation and administrative user limits.
- Neutral VLESS data model.
- Version-specific adapter that translates the neutral model into Xray 26.10.31 configuration.
- Controlled Xray binary and geodata package administration.
- Centralized filesystem paths and separated application data.
- Atomic JSON persistence and shared locking for operations spanning users and connections.
- Backup and guarded uninstallation workflows.
- Functional, integration, persistence-fault, concurrency, and port-collision test scripts.

These are documented implementation capabilities, not a statement that the whole application is production-ready.

### Important operational boundary

Connection and user records are currently drafts. Creating a record does not apply a configuration to a running Xray instance. The current tool does not yet complete the production lifecycle of configuration generation, transactional application, service activation, runtime verification, and rollback. It does not currently manage the systemd lifecycle or modify firewall, SSH, or general network settings.

This distinction is deliberate and is stated in the project's documentation.

## 6. Engineering problems addressed and corrections documented

The development record describes concrete issues, the engineering response, and the associated verification approach.

| Problem or risk identified | Documented engineering response |
|---|---|
| Storage paths were distributed across modules | Introduced `config/paths.sh` as the canonical path source and adapted key consumers. |
| JSON updates could expose incomplete data if interrupted | Added `lib/json_store.sh` using a same-directory temporary file, validation, file and directory synchronization, and atomic replacement. |
| Independent locks did not protect relationships between users and connections | Replaced separate critical sections with a shared integrity lock. |
| A connection could change between initial lookup and user creation | Revalidated the VLESS draft connection after acquiring the shared lock. |
| A connection with associated users could be deleted | Checked user associations under the shared lock before allowing deletion. |
| Concurrent operations could create duplicate or inconsistent records | Added process-level concurrency and cross-operation race tests. |
| A synchronization failure could occur after the atomic replacement was already visible | Defined a distinct return status for replacement applied but directory durability unconfirmed, so callers do not falsely report that no change occurred. |
| Uninstallation could remove resources outside the manager's verified scope | Restricted deletion to explicitly inventoried paths, added backup and confirmation steps, and blocked when a detected Xray systemd unit makes the operation unsafe. |

The work is documented in the stage records, especially [Storage Architecture](ARQUITECTURA_RUTAS_Y_ALMACENAMIENTO.md), [Stage 1 — Xray Administration](ETAPA_1_ADMIN_XRAY_IMPLEMENTACION.md), [Stage 2 — Connections](ETAPA_2_CONEXIONES.md), and [Stage 3 — VLESS Users](ETAPA_3_USUARIOS.md).

## 7. Test evidence recorded in the project documentation

The repository includes test scripts and technical records of previous test runs. The following results are reported in the project documentation, principally in the November 2026 engineering notes.

### Persistence and concurrency

- `tests/concurrency.sh`: 16 independent user creations, 16 edits, and 16 deletions in an isolated temporary environment. The documented checks include record counts, unique UUIDs, associations, state, and file permissions. The test is recorded as passing four consecutive runs.
- `tests/cross_race.sh`: forces both possible lock-acquisition orders between user creation and draft-connection deletion. The documented result is that no orphan user is created and a connection with a user association is not deleted. Five consecutive runs are recorded as passing.
- `tests/json_store_faults.sh`: injects failures around file and directory synchronization and terminates the commit process at controlled points before and after atomic replacement. Three consecutive runs are recorded as passing. The test checks that the visible destination remains complete JSON, while documenting that a directory-sync failure after replacement does not prove durability against power loss.
- `tests/port_collisions.sh`: tests simultaneous attempts to create or edit records using the same port, and checks detection of TCP and UDP listening sockets in an isolated environment. Five consecutive runs are recorded as passing.

### Xray and VLESS configuration validation

The project documentation records that:

- Xray-core 26.10.31 was obtained for validation and its SHA-256 was checked against the official release digest and the project's pinned value.
- A temporary VLESS RAW inbound fixture was accepted by the validation binary with `Configuration OK.`.
- `tests/xray_vless_integration.sh` generated temporary fixtures for all nine VLESS modes represented by the neutral model and version-specific adapter.
- The nine fixtures were accepted by `xray run -test`, including the XHTTP variants. Temporary certificates and keys were used for validation and removed after the test.
- These tests validated configuration syntax with the selected Xray binary. They did not establish end-to-end client connectivity, production certificate readiness, or live service operation.

### Scope and evidence qualification

The results above are historical results recorded in the repository's engineering documentation. They have not all been rerun as part of preparing this report. The existence of a test script is not proof that it currently passes on every platform or commit. OSMT intends to preserve exact test scope, environment, date, and outcome as validation becomes more systematic.

The documented tests use isolated temporary data for the relevant persistence and concurrency scenarios. They do not constitute proof against real power loss, kernel failure, physical filesystem corruption, or every possible race with unrelated external processes.

## 8. Current status and known limitations

OSMT is early-stage and actively developing. Xray Core Manager is version 0.2.0-dev and is not represented as production-ready.

Known boundaries and pending work include:

- Complete the configuration lifecycle: build, validate, preview, back up, apply, verify, and recover.
- Implement carefully scoped systemd service integration with explicit contracts and tests.
- Complete persistence consumers for profiles, domains, certificates, preferences, and history.
- Complete and validate the configuration path under `/etc/xray`.
- Expand installation, upgrade, interruption, uninstallation, and recovery testing in disposable VPS environments.
- Validate permissions and access boundaries for future service users and certificate handling.
- Define a tested support matrix and release criteria.
- Keep the Xray adapter tied to its explicitly supported version until another adapter is implemented and validated.

The current port check is observational: it checks sockets reported by `ss` and logical reservations in the manager's own records. It does not reserve a socket against an unrelated process. The current uninstallation implementation has not been exercised as a real destructive uninstall on a production VPS.

These limitations are part of the project record and should remain visible to users and potential collaborators.

## 9. Roadmap and measurable direction

OSMT is following an incremental roadmap. The immediate priority is to mature the first component before broadening the ecosystem.

### Priority 1 — Mature Xray Core Manager

- Complete the supported configuration lifecycle.
- Implement controlled systemd integration.
- Complete profiles, certificate, domain, and history workflows.
- Expand isolated installation, upgrade, failure, and recovery tests.
- Publish clear prerequisites and a tested support matrix.
- Prepare a tagged release only after release criteria are met.

**Acceptance direction:** supported workflows are reproducible in isolation, failures are visible, state is not silently corrupted, and supported and unsupported behavior is explicit.

### Priority 2 — VPS First-Run Assistant

A beginner-focused, read-only tool that inventories operating system, architecture, CPU, memory, storage, network, package manager, services, and basic system readiness, then produces a local report in plain language.

**Acceptance direction:** inspection changes nothing and clearly separates observed facts from recommendations.

### Longer-term candidate tools

- App Deploy Assistant.
- Service Desk for Linux.
- Domain & TLS Assistant.
- VPS Security Baseline.
- Backup & Restore Assistant.
- VPS Health Monitor.
- Linux Troubleshooting Guide.

These are proposed future tools, not released products. Each must have a bounded use case, test plan, documentation, and maintenance strategy before being treated as an implementation.

## 10. Why this can be valuable as an open-source initiative

OSMT's potential value comes from combining practical infrastructure tooling with an educational approach.

Many developers learn application development before they learn the operational responsibilities that make software reliable in the real world. OSMT seeks to make those responsibilities more approachable by building tools that do not merely perform tasks, but explain them and expose their operational boundaries.

The open-source model matters to this goal:

- **Inspectability:** users and educators can examine how operations are performed.
- **Adaptability:** developers can learn from, modify, and extend tools for their own environments.
- **Shared improvement:** reproducible issues, tests, and documentation can help contributors improve common workflows.
- **Lower entry barriers:** focused tools can be useful without requiring a large proprietary control panel or a specific cloud provider.
- **Transferable learning:** concepts such as permissions, services, networking, validation, backups, and recovery apply beyond one application or hosting company.
- **Responsible defaults:** safety and transparency are intended to be design requirements rather than optional documentation added after implementation.

OSMT cannot claim that these benefits have already been achieved at scale. Its opportunity is to build and evaluate them through usable tools, beginner feedback, documented examples, contributions, and evidence from real deployments when those become available.

## 11. Why collaboration with OpenAI could help

OSMT is independent of any AI provider. Its core mission and tools should remain useful without requiring an AI service.

However, AI-assisted development tools could help a small open-source effort work more effectively, particularly in areas where careful review and documentation matter:

- Reviewing Bash changes and identifying edge cases.
- Generating and improving regression tests from reproducible bugs.
- Helping analyze failure logs and explain root causes.
- Maintaining consistency between code, tests, and documentation.
- Supporting contributors who are still learning the relevant engineering concepts.
- Accelerating research and implementation of new, carefully scoped tools.

Codex and related developer tools could be useful as development accelerators, not as substitutes for maintainers, testing, or engineering judgment. Any AI-assisted feature in OSMT itself would be optional, transparent, and subject to the same administrator-control principles. It must not silently execute privileged changes.

A collaboration or support opportunity could therefore help OSMT strengthen its engineering practices, improve the quality and accessibility of its documentation, expand test coverage, and build tools that serve developers earlier in their careers.

The project is not asking OpenAI to validate unsupported claims of adoption or production maturity. It is presenting an existing body of work, a defined public-interest problem, and a credible path for continued development.

## 12. Development infrastructure and current CI status

A GitHub Actions workflow was added at `.github/workflows/ci.yml` to run static checks and functional tests on Ubuntu 24.04 for pushes to `main`, pull requests, and manual dispatch.

The first workflow run did not start a runner. GitHub reported that the account was locked due to a billing issue. Therefore, that run did **not** execute Bash syntax checks, ShellCheck, shfmt, or the test suite. This is an external account-level infrastructure restriction, not a test failure in OSMT's code.

Until the account restriction is resolved, the project can continue with local or isolated validation. The workflow file remains in the repository so that hosted CI can be used when execution is available.

## 13. Project integrity and commitments

OSMT intends to grow through evidence rather than inflated claims.

The project commits to:

- Distinguish implemented functionality from proposals.
- Distinguish historical test records from newly executed tests.
- Document supported platforms, versions, prerequisites, and limitations.
- Avoid destructive or privileged operations without clear scope and approval.
- Keep secrets and production credentials out of source control and test output.
- Prefer isolated test environments for installation, recovery, and destructive workflows.
- Publish reproducible bug reports and meaningful regression tests.
- Avoid claiming production readiness, security guarantees, adoption, or educational impact without evidence.

The project's MIT license and public repository are intended to make inspection, learning, and collaboration possible. Its technology choices remain independent and pragmatic; future components may use different languages when that better serves their purpose.

## 14. Repository evidence and further reading

The following documents provide implementation-level detail:

- [README — project entry point](../README.md)
- [Project overview](PROJECT_OVERVIEW.md)
- [Project vision](PROJECT_VISION.md)
- [Roadmap](ROADMAP.md)
- [Tools catalog](TOOLS_CATALOG.md)
- [Ecosystem map](ECOSYSTEM_MAP.md)
- [Technical decisions](DECISIONES_TECNICAS.md)
- [Storage architecture and persistence](ARQUITECTURA_RUTAS_Y_ALMACENAMIENTO.md)
- [Stage 1 — Xray administration](ETAPA_1_ADMIN_XRAY_IMPLEMENTACION.md)
- [Stage 2 — protocols and connections](ETAPA_2_CONEXIONES.md)
- [Stage 3 — VLESS user management](ETAPA_3_USUARIOS.md)
- [VLESS generator design and adapter validation](GENERADOR_VLESS_DISENO.md)
- [Changelog](../CHANGELOG.md)
- [Contribution guide](../CONTRIBUTING.md)
- [Security policy](../SECURITY.md)
- [CI workflow](../.github/workflows/ci.yml)

---

## Closing statement

OSMT starts from a simple observation: making software is only part of building useful software. Developers also need to understand how to deploy, secure, operate, and recover the systems that run it.

The initiative aims to make that operational knowledge more accessible through free, focused, inspectable tools and Guided Automation. Xray Core Manager is the first implementation, and its development record already includes concrete architecture, code, documented corrections, and test evidence. The work is not finished, and its limitations are explicit.

The long-term goal is to help more people move from being developers who can build an application to developers who can confidently and responsibly operate it.

**OSMT — Learn. Deploy. Secure. Operate.**
