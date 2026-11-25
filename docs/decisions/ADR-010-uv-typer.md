# ADR-010: uv + Typer CLI instead of make

- Status: accepted
- Date: 2026-11-25

**Decision.** `uv` manages Python 3.12 and the dependencies (lock file committed); a Typer CLI (`sgraph`) replaces a
Makefile so every step runs the same way in PowerShell, bash and CI.
