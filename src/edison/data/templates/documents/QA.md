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

<!-- /EXTENSIBLE: ValidationDimensions -->

<!-- EXTENSIBLE: AutomatedChecks -->
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

<!-- /EXTENSIBLE: AutomatedChecks -->

<!-- EXTENSIBLE: TDDReview -->
## TDD Evidence Review

### RED Phase
- [ ] Failing test created before implementation
- Evidence: 

### GREEN Phase
- [ ] Test passes with minimal implementation
- Evidence: 

### REFACTOR Phase
- [ ] Code refactored without breaking tests
- Evidence: 

<!-- /EXTENSIBLE: TDDReview -->

<!-- EXTENSIBLE: ValidatorVerdicts -->
## Validator Verdicts

<!-- Record verdict from each validator -->

### Round {{round}} Verdicts

| Validator | Verdict | Blocking | Notes |
|-----------|---------|----------|-------|
| | | | |

<!-- /EXTENSIBLE: ValidatorVerdicts -->

<!-- EXTENSIBLE: Findings -->
## Findings

### Issues Found
<!-- List any issues or concerns -->

### Strengths
<!-- List positive aspects -->

### Recommendations
<!-- List recommendations for improvement -->

<!-- /EXTENSIBLE: Findings -->

<!-- EXTENSIBLE: EvidenceLinks -->
## Evidence Links

<!-- Links to validation evidence files -->
- Bundle: 
- Validator Reports: 

<!-- /EXTENSIBLE: EvidenceLinks -->

<!-- EXTENSIBLE: ApprovalStatus -->
## Approval Status

**Approved:** ❌ No
**Approved By:** 
**Approval Date:** 

<!-- /EXTENSIBLE: ApprovalStatus -->

<!-- EXTENSIBLE: FollowUpTasks -->
## Follow-up Tasks

<!-- Tasks created as result of validation -->

<!-- /EXTENSIBLE: FollowUpTasks -->

<!-- EXTENSIBLE: Notes -->
## Notes

<!-- Additional notes from validation -->

<!-- /EXTENSIBLE: Notes -->
