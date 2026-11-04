# ADR-002: No scraping or unattended control of consumer AI websites

- **Status:** Accepted for MVP
- **Date:** 2026-11-03

## Context

Mosaic must coordinate normal consumer chat interfaces without APIs or work-mode agents. Automated extraction and browser control can be fragile, privacy-invasive, and restricted by provider terms.

## Decision

The guaranteed path is official user-requested exports and manual copy/paste. The optional browser companion is outbound-only: it may display/copy a context packet and open a provider URL after a user action. It must not inspect provider DOM, read session data, scrape content, auto-fill, or auto-submit.

## Consequences

Positive:
- provider-independent manual fallback;
- smaller permission surface;
- less brittle than DOM automation;
- easier to reason about consent and attribution.

Trade-offs:
- response return remains manual;
- no background coordination;
- user must switch between Mosaic and provider pages.

## Revisit when

A provider offers a documented, authorised integration and a separate policy/security review approves the exact operation.