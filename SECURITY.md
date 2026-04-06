# Security Policy

## Supported Versions

This is a personal portfolio project. The latest commit on `main` is the only actively supported version.

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please open a GitHub Issue with the label `security`.

For sensitive disclosures that should not be public, please describe the issue privately via GitHub's [private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability) feature.

Please include:
- A description of the vulnerability
- Steps to reproduce (if applicable)
- Potential impact

## Security Practices

- All pull requests are scanned automatically for known CVEs in Python and Node.js dependencies
- Dependencies are monitored continuously for newly published vulnerabilities
- Static analysis is run on Python source code on every pull request
- Secrets and API keys are never committed — all credentials are managed via environment variables

## Disclosure Policy

Vulnerabilities will be acknowledged within 48 hours and addressed based on severity. Critical and high severity issues are prioritized.
