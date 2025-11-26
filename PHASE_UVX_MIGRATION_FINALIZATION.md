It seems the tests are still creating files in the root edison folder under .project and .edison instead of temporary folders in the user's computer's tmp folder. please analyse DEEPLY ALL places where that could happen and exactly the ROOT CAUSE of why that happens, and fix it. Please also analaye DEEPLY why tests are taking so long to execute and if this is normal, or if we have an issue somewhere, and if we have an issue somwhere please fix it (while still retaining ALL tests/implementation/logic and NO-MOCKS and REAL tests against tmp project folders)

then continue running the tests and fixing ALL remaining root causes/issues until EVERYTHING works exactly as expected and ALL tests pass and we have NO skipped tesks/mocked tests/etc

also it seems some subagents have bootstraped the edison project as an edison project and created an .edison folder, and symlinked some files to previous locations to "fix" some issues, WHICH IS DEEPLY WRONG!!! we must ALWAYS remove/refactor ALL legacy implementation/handling and NEVER use workarounds like this!! as CLEARLY indicated multiple times, ALL tests MUST be executed on TEST LOCATIONS/PATHS/FOLDERS and NOT on our real edison repository or any other real projects!!

"Fix e2e rules tests" agent output in question:
<agent_output_in_cause>
1. **Missing .edison Directory Structure** (CRITICAL)
   - The Edison repository itself needs to be bootstrapped as an Edison project
   - Created `scripts/bootstrap_edison_repo.py` to set up the `.edison` structure
   - Symlinked `src/edison/data/` to `.edison/core/` for rules, guidelines, and packs
</agent_output_in_cause>

Please check, delegate analyses for ALL issues reported, and then delegate subagents to FIX them ALL reliably using DETAILLED instructions, then re-run the tests and fixing ROOT ISSUES until EVERYTHING is corectly fixed. re-read the ~/.claude/plans/shimmying-toasting-waterfall.md original plan as well to refresh your mind if necessary

Remember our non-negotiable rules:
🎯 CRITICAL PRINCIPLES (NON-NEGOTIABLE)
Every Task Must Follow:
1. ✅ STRICT TDD: Write failing test FIRST (RED), then implement (GREEN), then refactor
2. ✅ NO MOCKS: Test real behavior, real code, real libs - NO MOCKS EVER
3. ✅ NO LEGACY: Delete old code completely - NO backward compatibility, NO fallbacks
4. ✅ NO HARDCODED VALUES: All config from YAML - NO magic numbers/strings in code
5. ✅ 100% CONFIGURABLE: Every behavior must be configurable via YAML
6. ✅ DRY: Zero code duplication - extract to shared utilities
7. ✅ SOLID: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
8. ✅ KISS: Keep It Simple, Stupid - no over-engineering
9. ✅ YAGNI: You Aren't Gonna Need It - remove speculative features
10. ✅ LONG-TERM MAINTAINABLE
11. ✅ UN-DUPLICATED & REUSABLE: DON'T REINVENT THE WHEEL. Before implementing any logic/lib/etc, analyse the current source code and look for potential already existing feature/implementation/function/class/lib that you could reuse/extend instead.
12. ✅ STRICT COHERENCE: Our WHOLE code/lib/implementation/structure should be and stay coherent. BEFORE implementing anything, look for similar patterns in our implementation/files/structure and understand EXACTLY how our current project/code/files/libs/scripts are structured and implemented, and implement it in a same/similar way, ensuring that anyone looking at our code/structure can easily understand everything and that our full implementation is looking like ONE coherent system
13. ✅ ALWAYS FINDING AND FIXING ROOT ISSUES/ROOT CAUSES: We should NEVER apply dirty fixes or remove/simplify some logic/tests JUST to make some tests pass or bypass an issue. We must ALWAYS find the ROOT CAUSES of all issues and FIX THEM instead.
You, as the Orchestrator MUST
1. Delegate to multiple subagents to apply/perform each tasks completely end-to-end following strict TDD, NO MOCKS, NO LEGACY, NO HARDCODED VALUES and then monitor their work/success
2. Reading/analysing every subagent report/output to make them continue their work end-to-end using continuation_id when appropriate/applicable
3. Making SURE the agents perform their task end-to-end and COMPLETELY, and making them continue until then
4. Delegating new tasks/fixes/followups to new subagents if relevant/necessary and if reported by the sub-agents
5. Making sure you continue continue this whole loop and delegating any remaining tasks/issues/follow-ups and following the COMPLETE PLAN until everything is done, completed, comprehensive, 100% configurable, 100% coherent and cohesive, un-duplicated, long-term maintainable, re-structured, re-organized, DRY, SOLID, KISS, FAIL-SAFE and beautifuly+clearly organized for clarity and long-term maintainability and coherence.

Preserve your main context to the maximum for delegation/orchestration/decision/delegation/management/validation/verification and give very precise and detailled instructions to the subagents and make them read the complete plan so they have the whole context in mind as well

It seems the tests are still creating files in the root edison folder under .project and .edison instead of temporary folders in the user's computer's tmp folder. please analyse DEEPLY ALL places where that could happen and exactly the ROOT CAUSE of why that happens, and fix it. Please also analaye DEEPLY why tests are taking so long to execute and if this is normal, or if we have an issue somewhere, and if we have an issue somwhere please fix it (while still retaining ALL tests/implementation/logic and NO-MOCKS and REAL tests against tmp project folders)

 then continue running the tests and fixing ALL remaining root causes/issues until EVERYTHING works exactly as expected and ALL tests pass and we have NO skipped tesks/mocked tests/etc

also it seems some subagents have bootstraped the edison project as an edison project and created an .edison folder, and symlinked some files to previous locations to "fix" some issues, WHICH IS DEEPLY WRONG!!! we must ALWAYS remove/refactor ALL legacy implementation/handling and NEVER use workarounds like this!! as CLEARLY indicated multiple times, ALL tests MUST be executed on TEST LOCATIONS/PATHS/FOLDERS and NOT on our real edison repository or any other real projects!!

Please check, delegate analyses for ALL issues reported, and then delegate subagents to FIX them ALL reliably using DETAILLED instructions, then re-run the tests and fixing ROOT ISSUES until EVERYTHING is corectly fixed. re-read the ~/.claude/plans/shimmying-toasting-waterfall.md original plan as well to refresh your mind if necessary