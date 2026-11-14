# Security Policy

## Scope

This repository contains Open Server Management Tools (OSMT) documentation and the Xray Core Manager component. Security reports are welcome for vulnerabilities in code maintained here.

## Reporting a vulnerability

**Please do not disclose exploitable vulnerabilities in public issues.**

Use GitHub's private vulnerability reporting feature for this repository, if enabled. If private reporting is unavailable, contact the repository owner through the private contact method listed on the GitHub profile and request a secure channel. Do not include secrets or live server credentials in an initial message.

A useful report includes:
- A concise description of the suspected vulnerability.
- Affected version, commit and component.
- Preconditions and impact.
- Reproduction steps or a minimal proof of concept.
- Suggested mitigation, if known.

Do not test against systems you do not own or have explicit authorization to assess.

## Response expectations

The maintainer will acknowledge reports as reasonably possible, investigate reproducibility and impact, and coordinate a fix and disclosure timeline with the reporter. No fixed response or remediation SLA is promised at this early stage.

## Safe-use boundaries

- Test administrative tools in disposable or isolated environments first.
- Review commands and proposed changes before running them with elevated privileges.
- Keep API tokens, passwords, private keys and production configuration out of source control.
- Do not assume a successful syntax or integration test proves a server is secure.
- Do not expose administrative APIs or management interfaces to untrusted networks.

## Supported versions

Security fixes will be prioritized for actively maintained versions. The project's release and support policy is still being established; check the README and release notes for current status.
