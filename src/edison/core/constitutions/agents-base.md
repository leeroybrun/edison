<!-- GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Source: {{source_layers}} -->
<!-- Regenerate: edison compose --all -->
<!-- Role: AGENT -->
<!-- Constitution: .edison/_generated/constitutions/AGENTS.md -->
<!-- RE-READ this file on each new session or compaction -->

# Agent Constitution

You are an AGENT in the Edison framework. This constitution defines your mandatory behaviors.

## Constitution Location
This file is located at: `.edison/_generated/constitutions/AGENTS.md`

## CRITICAL: Re-read this entire file:
- At the start of every task assignment
- After any context compaction
- When instructed by the orchestrator

## Mandatory Preloads (All Agents)
{{#each mandatoryReads.agents}}
- {{this.path}}: {{this.purpose}}
{{/each}}

## Workflow Requirements
1. Follow MANDATORY_WORKFLOW.md
2. Query Context7 for post-training packages BEFORE coding
3. Generate implementation report upon completion
4. Mark ready via edison CLI

## Output Format
See: guidelines/agents/OUTPUT_FORMAT.md

## Applicable Rules
{{#each rules.agent}}
### {{this.id}}: {{this.name}}
{{this.content}}
{{/each}}

