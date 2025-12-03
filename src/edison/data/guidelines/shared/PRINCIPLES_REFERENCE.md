# Edison Critical Principles Reference

## Authoritative Source

**`CLAUDE.md` in the project root is the single source of truth for Critical Principles.**

All Edison development (Orchestrators, Agents, Validators) must follow the **16 Non-Negotiable Principles** defined there.

## The 16 Principles (Summary)

1. **STRICT TDD** - Write failing test FIRST, then implement
2. **NO MOCKS** - Test real behavior, real code, real libs
3. **NO LEGACY** - Delete old code completely, no backward compatibility
4. **NO HARDCODED VALUES** - All config from YAML
5. **100% CONFIGURABLE** - Every behavior configurable via YAML
6. **DRY** - Zero code duplication
7. **SOLID** - Single Responsibility, Open/Closed, Liskov, Interface Segregation, Dependency Inversion
8. **KISS** - Keep It Simple, Stupid
9. **YAGNI** - You Aren't Gonna Need It
10. **LONG-TERM MAINTAINABLE** - Code must be maintainable for years
11. **UN-DUPLICATED & REUSABLE** - Don't reinvent the wheel
12. **STRICT COHERENCE AND UNITY** - Follow existing patterns exactly
13. **ROOT CAUSE FIXES** - Fix underlying issues, never apply dirty fixes
14. **REFACTORING ESSENTIALS** - Update ALL callers when refactoring
15. **SELF VALIDATION** - Re-analyze everything before marking done
16. **GIT SAFETY** - Never use destructive git commands

## Full Documentation

For complete details, examples, and enforcement guidelines:

1. **Primary**: `CLAUDE.md` (project root)
2. **Detailed**: `.edison/guidelines/edison/CRITICAL_PRINCIPLES.md`

## Token Efficiency

This reference file prevents duplication of the full principle list (200+ tokens) across multiple constitution files, saving ~600+ tokens per agent session while maintaining the same mandatory read requirements.
