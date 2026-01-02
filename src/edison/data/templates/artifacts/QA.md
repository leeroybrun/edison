---
id: "{{id}}"
task_id: "{{task_id}}"
title: "{{title}}"
round: {{round}}
validator_owner: {{validator_owner}}
session_id: {{session_id}}
validators: {{validators}}
evidence: {{evidence}}
created_at: {{created_at}}
updated_at: {{updated_at}}
state_history: {{state_history}}
---

# {{title}}

<!-- EXTENSIBLE: ValidationScope -->
## Validation Scope

**Task:** {{task_id}}
**Round:** {{round}}
**Validator:** {{validator_owner}}

<!-- /EXTENSIBLE: ValidationScope -->

<!-- EXTENSIBLE: ValidationDimensions -->
<!-- REQUIRED FILL: ValidationDimensions -->
## Validation Dimensions

<!-- Validators check these dimensions -->
| Dimension | Status | Score | Notes |
|-----------|--------|-------|-------|
| Architecture | ⏳ Pending | - | |
| Code Quality | ⏳ Pending | - | |
| Testing | ⏳ Pending | - | |
| Documentation | ⏳ Pending | - | |
| Error Handling | ⏳ Pending | - | |
| Performance | ⏳ Pending | - | |
| Security | ⏳ Pending | - | |

<<FILL: update validation dimension statuses/scores/notes>>

<!-- /EXTENSIBLE: ValidationDimensions -->

<!-- EXTENSIBLE: AutomatedChecks -->
<!-- REQUIRED FILL: AutomatedChecks -->
## Automated Checks

### Build Status
- [ ] Build passes

### Type Checking
- [ ] Type checking passes

### Linting
- [ ] Linting passes

### Tests
- [ ] All tests pass
- [ ] Coverage meets threshold

<<FILL: record automated check results and links>>

<!-- /EXTENSIBLE: AutomatedChecks -->

<!-- EXTENSIBLE: TDDReview -->
<!-- REQUIRED FILL: TDDReview -->
## TDD Evidence Review

### RED Phase
- [ ] Failing test created before implementation
- Evidence: <<FILL: link or summary>>

### GREEN Phase
- [ ] Test passes with minimal implementation
- Evidence: <<FILL: link or summary>>

### REFACTOR Phase
- [ ] Code refactored without breaking tests
- Evidence: <<FILL: link or summary>>

<!-- /EXTENSIBLE: TDDReview -->

<!-- EXTENSIBLE: ValidatorVerdicts -->
<!-- REQUIRED FILL: ValidatorVerdicts -->
## Validator Verdicts

<!-- Record verdict from each validator -->

### Round {{round}} Verdicts

| Validator | Verdict | Blocking | Notes |
|-----------|---------|----------|-------|
| <<FILL: validator>> | <<FILL: verdict>> | <<FILL: blocking>> | <<FILL: notes>> |

<!-- /EXTENSIBLE: ValidatorVerdicts -->

<!-- EXTENSIBLE: Findings -->
<!-- REQUIRED FILL: Findings -->
## Findings

### Issues Found
<<FILL: issues found>>

### Strengths
<<FILL: strengths>>

### Recommendations
<<FILL: recommendations>>

<!-- /EXTENSIBLE: Findings -->

<!-- EXTENSIBLE: EvidenceLinks -->
<!-- REQUIRED FILL: EvidenceLinks -->
## Evidence Links

<!-- Links to validation evidence files -->
- Bundle: <<FILL: path>>
- Validator Reports: <<FILL: paths>>

<!-- /EXTENSIBLE: EvidenceLinks -->

