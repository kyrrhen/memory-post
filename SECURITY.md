# Security Policy

## Supported versions

The latest release is supported with security fixes.

## Reporting a vulnerability

Please do not open a public issue for a vulnerability that could affect users who open untrusted bundles or images.

Report it privately to the repository maintainer, including:

- affected version
- reproduction steps
- a minimal sample file if safe to share
- expected impact

## Scope and notes

- Memory Post processes images and ZIP bundles locally.
- The app does not send telemetry and does not require network access at runtime.
- The Windows executable is currently unsigned, so Windows SmartScreen may warn about an unknown publisher.
- Only open bundles from sources you trust.
