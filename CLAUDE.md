## 🎯 CRITICAL PRINCIPLES (NON-NEGOTIABLE)
1. ✅ **STRICT TDD**: Write failing test FIRST (RED), then implement (GREEN), then refactor
2. ✅ **NO MOCKS**: Test real behavior, real code, real libs - NO MOCKS EVER
3. ✅ **NO LEGACY**: Delete old code completely - NO backward compatibility, NO fallbacks
4. ✅ **NO HARDCODED VALUES**: All config from YAML - NO magic numbers/strings in code
5. ✅ **100% CONFIGURABLE**: Every behavior must be configurable via YAML
6. ✅ **DRY**: Zero code duplication - extract to shared utilities
7. ✅ **SOLID**: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
8. ✅ **KISS**: Keep It Simple, Stupid - no over-engineering
9. ✅ **YAGNI**: You Aren't Gonna Need It - remove speculative features
10. ✅ **LONG-TERM MAINTAINABLE**
11. ✅ **UN-DUPLICATED & REUSABLE**: DON'T REINVENT THE WHEEL. Before implementing any logic/lib/etc, analyse the current source code and look for potential already existing feature/implementation/function/class/lib that you could reuse/extend instead.
12. ✅ **STRICT COHERENCE**: Our WHOLE code/lib/implementation/structure should be and stay coherent. BEFORE implementing anything, look for similar patterns in our implementation/files/structure and understand EXACTLY how our current project/code/files/libs/scripts are structured and implemented, and implement it in a same/similar way, ensuring that anyone looking at our code/structure can easily understand everything and that our full implementation is looking like ONE coherent system
13. ✅ **ALWAYS FINDING AND FIXING ROOT ISSUES/ROOT CAUSES**: We should NEVER apply dirty fixes or remove/simplify some logic/tests JUST to make some tests pass or bypass an issue. We must ALWAYS find the ROOT CAUSES of all issues and FIX THEM instead.

### You, as the Orchestrator MUST
1. Delegate to multiple subagents to apply/perform each tasks completely end-to-end following strict TDD, NO MOCKS, NO LEGACY, NO HARDCODED VALUES and then monitor their work/success
2. Reading/analysing every subagent report/output to make them continue their work end-to-end using continuation_id when appropriate/applicable
3. Making SURE the agents perform their task end-to-end and COMPLETELY, and making them continue until then
4. Delegating new tasks/fixes/followups to new subagents if relevant/necessary and if reported by the sub-agents
5. Making sure you continue continue this whole loop and delegating any remaining tasks/issues/follow-ups and following the COMPLETE PLAN until everything is done, completed, comprehensive, 100% configurable, 100% coherent and cohesive, un-duplicated, long-term maintainable, re-structured, re-organized, DRY, SOLID, KISS, FAIL-SAFE and beautifuly+clearly organized for clarity and long-term maintainability and coherence.