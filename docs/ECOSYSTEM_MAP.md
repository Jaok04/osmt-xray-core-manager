# OSMT Ecosystem Map

The diagram shows the intended relationship between the initiative's shared principles and candidate tools. It is a product vision, not a diagram of currently released software.

```mermaid
flowchart TB
    DEV["Developer / VPS beginner"]
    OSMT["Open Server Management Tools"]
    CORE["Shared principles\nGuided workflows · validation · user control\nleast privilege · recovery · clear documentation"]
    XRAY["Xray Core Manager\nFirst component · early development"]
    ONBOARD["VPS First-Run Assistant\nCandidate"]
    DEPLOY["App Deploy Assistant\nCandidate"]
    SERVICE["Service Desk for Linux\nCandidate"]
    NETWORK["Domain & TLS Assistant\nCandidate"]
    SECURITY["VPS Security Baseline\nCandidate"]
    BACKUP["Backup & Restore Assistant\nCandidate"]
    MONITOR["VPS Health Monitor\nCandidate"]
    LEARN["Linux Troubleshooting Guide\nCandidate"]

    DEV --> OSMT
    OSMT --> CORE
    CORE --> XRAY
    CORE --> ONBOARD
    CORE --> DEPLOY
    CORE --> SERVICE
    CORE --> NETWORK
    CORE --> SECURITY
    CORE --> BACKUP
    CORE --> MONITOR
    CORE --> LEARN
    ONBOARD --> DEPLOY
    DEPLOY --> SERVICE
    SERVICE --> NETWORK
    NETWORK --> SECURITY
    SECURITY --> BACKUP
    BACKUP --> MONITOR
    MONITOR --> LEARN
```

## How to read this map

- **Xray Core Manager** is the first implementation in the repository.
- All other boxes are candidate tools for future development.
- Shared principles are intended to create a consistent experience across independent utilities.
- The sequence represents a possible learning and operations journey, not a required dependency chain.
- Each tool should remain useful on its own and clearly document its supported platforms and limitations.
