# Security policy

Mosaic is currently a local-first, single-user application in early development. It is not designed for public-network exposure or multi-user hosting.

## Reporting a vulnerability

Please do not publish sensitive exploit details in a public issue. Contact the repository owner privately through GitHub's security reporting feature if enabled, or request a private disclosure channel.

## Security boundaries

- The API must bind to loopback only.
- Imported content and model responses are untrusted data.
- No provider cookies, session tokens, or passwords are collected.
- Archive readers must enforce size, entry, path, and compression-ratio limits.
- Candidate knowledge must be source-grounded and cannot be promoted by a model.
- Cross-provider transfers require explicit user permission and outbound secret redaction.
- Local model endpoints must be loopback-only by default.
- Never commit personal conversation exports, source archives, local databases, secrets, or private fixtures.

The threat model is maintained in `docs/security/threat-model.md`.
