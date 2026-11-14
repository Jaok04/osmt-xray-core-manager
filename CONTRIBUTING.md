# Contributing

Thank you for considering a contribution to Open Server Management Tools (OSMT).

The project welcomes experienced administrators and people who are learning Linux server operations. Bug reports, documentation improvements, reproducible tests and focused feature proposals are valuable contributions.

## Before you start

1. Read the root README and docs/PROJECT_VISION.md.
2. Check docs/ROADMAP.md and existing issues.
3. For Xray Core Manager, read the relevant stage documents in docs/.
4. Never include passwords, API tokens, private keys, client credentials or production configuration in an issue or pull request.

## Ways to contribute

- Report a reproducible bug.
- Improve installation or troubleshooting documentation.
- Add tests for existing behavior.
- Improve error messages and beginner-facing explanations.
- Propose a narrowly scoped feature.
- Review compatibility and security implications.

## Bug reports

Include the operating system/version, tool version or commit, exact command or menu path, expected and actual behavior, sanitized logs, reproduction steps and whether the issue occurs in a disposable test environment.

Remove IP addresses, hostnames, usernames, tokens and other sensitive information where appropriate.

## Feature proposals

Describe the user problem, who benefits, proposed behavior and alternatives, required privileges and system changes, failure modes and recovery strategy, and how the feature can be tested. A proposal is not a commitment to implement it.

## Development expectations

For the current Bash component:
- Keep scripts compatible with the documented Bash baseline.
- Quote variable expansions unless intentional word splitting is required.
- Validate external input and command availability.
- Avoid destructive commands without explicit scope and confirmation.
- Prefer temporary test directories and isolated fixtures.
- Do not modify a developer's live Xray service during tests.
- Add regression tests for bug fixes.
- Keep documentation aligned with actual behavior.

Run the available checks from the repository root:

```bash
bash -n bin/xray-manager config/paths.sh lib/*.sh modules/*.sh tests/*.sh
shellcheck -x bin/xray-manager config/paths.sh lib/*.sh modules/*.sh tests/*.sh
shfmt -d bin/xray-manager config/paths.sh lib/*.sh modules/*.sh tests/*.sh
for test in tests/*.sh; do bash "$test"; done
```

Some integration tests require a validation Xray binary. Read each test and its documentation before running it.

## Pull requests

A good pull request solves one focused problem, explains the motivation and user-visible change, lists affected files and operational behavior, includes actual test results, documents prerequisites and limitations, identifies privileged/destructive/network-facing behavior and avoids unrelated refactoring.

Do not claim tests passed unless you ran them and can report the result.

## Review approach

Reviews focus on correctness, safety, clarity, maintainability and whether a beginner can understand the workflow. Constructive questions and requests for clarification are part of the process.

By contributing, you agree to follow CODE_OF_CONDUCT.md.
