# Context Impact Analysis Toolkit

**Comprehensive testing framework to measure, analyze, and optimize context consumption across AI-automated development workflows.**

## 🎯 Purpose

This toolkit provides **real**, **no-mocks** analysis of how much LLM context is consumed by:
- Mandatory guideline files loaded on every session
- Task-specific guides triggered by file patterns
- Sub-agent prompts during delegation
- Validator prompts during QA
- CLI outputs (like `session next`)

## 📊 Key Findings

Based on analysis of the current project `.agents/` structure:

### Current State
- **Baseline (mandatory files)**: ~23,300 tokens (11.7% of 200K Claude context)
- **Average task scenario**: ~46,000-52,000 tokens (23-26% of context)
- **Largest single file**: `TDD_GUIDE.md` at 9,635 tokens
- **Highest duplication**: 96% similarity between `codex-global.md` and `claude-global.md`

### Potential Optimization
- **Estimated savings**: ~41,000 tokens (79.5% reduction possible)
- **Target average task**: ~30,000 tokens (15% of context window)

## 🚀 Quick Start

### Installation

```bash
# Optional: Install tiktoken for accurate token counting
python3 -m pip install --user tiktoken --break-system-packages

# The toolkit works without tiktoken using estimation
```

### Running Analysis

```bash
# From repository root
cd /path/to/{PROJECT_NAME}

# Full analysis (recommended first run)
python3 .agents/scripts/tests/context/context_impact_analyzer.py

# Or use the wrapper script
python3 << 'EOF'
import sys
sys.path.insert(0, '.agents/scripts/tests/context')
from context_impact_analyzer import ContextImpactAnalyzer

analyzer = ContextImpactAnalyzer()
results = analyzer.run_full_analysis()
EOF

# Baseline only
python3 << 'EOF'
import sys
sys.path.insert(0, '.agents/scripts/tests/context')
from baseline_profiler import BaselineProfiler

profiler = BaselineProfiler()
print(profiler.generate_report())
EOF

# Bloat detection only
python3 << 'EOF'
import sys
sys.path.insert(0, '.agents/scripts/tests/context')
from bloat_detector import BloatDetector

detector = BloatDetector()
print(detector.generate_report())
EOF
```

## 📁 Module Structure

```
.agents/scripts/tests/context/
├── README.md                      # This file
├── __init__.py                    # Package exports
├── analyze                        # CLI wrapper script
├── token_counter.py               # Token counting (tiktoken + fallback)
├── baseline_profiler.py           # Mandatory files analysis
├── scenario_simulator.py          # Task scenario simulation
├── bloat_detector.py              # Bloat detection & recommendations
└── context_impact_analyzer.py     # Main orchestrator CLI
```

## 🔧 Modules

### 1. `token_counter.py`
**Purpose**: Accurate token counting using tiktoken (with fallback estimation)

**Key Features**:
- Uses tiktoken `cl100k_base` encoding (same as GPT-4/Claude)
- Fallback estimation if tiktoken unavailable (~95% accurate)
- Supports text, files, directories, and JSON structure analysis

**Example**:
```python
from token_counter import TokenCounter

counter = TokenCounter()
file_info = counter.count_file(".agents/AGENTS.md")
print(f"Tokens: {file_info['tokens']}")  # e.g., 1,383
```

### 2. `baseline_profiler.py`
**Purpose**: Profile REAL mandatory files from `.agents/manifest.json`

**Key Features**:
- Loads actual mandatory file list from manifest
- Categorizes files (guidelines, configs, workflows, etc.)
- Breaks down JSON configs by section
- Estimates context budget usage across different LLMs

**Example**:
```python
from baseline_profiler import BaselineProfiler

profiler = BaselineProfiler()
baseline = profiler.profile_mandatory_core()
print(f"Total mandatory tokens: {baseline['total_tokens']:,}")
```

**Output**: Markdown report showing mandatory file costs by category

### 3. `scenario_simulator.py`
**Purpose**: Simulate REAL task scenarios based on actual trigger rules

**Key Features**:
- Uses REAL `.agents/manifest.json` trigger rules
- Detects which guides are loaded for each task type
- Determines validator roster from `.agents/validators/config.json`
- Simulates complete context loading (mandatory + guides + agent + validators)

**Example**:
```python
from scenario_simulator import ScenarioSimulator

simulator = ScenarioSimulator()
result = simulator.simulate_scenario(
    "API Route",
    task_type="api-route",
    file_paths=["apps/example-app/src/app/api/leads/route.ts"]
)
print(f"Total tokens for API route: {result['total_tokens']:,}")
```

**Scenarios Tested**:
1. UI Component (Button.tsx) - ~46K tokens
2. API Route (leads route) - ~47K tokens
3. Full-Stack Feature - ~52K tokens
4. Database Schema - ~50K tokens
5. Test Suite - ~46K tokens

### 4. `bloat_detector.py`
**Purpose**: Identify context bloat and optimization opportunities

**Key Features**:
- Detects oversized files (>3K tokens or >800 lines)
- Finds duplicate/similar content (using difflib)
- Analyzes config file bloat by section
- Identifies rarely-used mandatory files

**Example**:
```python
from bloat_detector import BloatDetector

detector = BloatDetector()

# Find oversized files
oversized = detector.detect_oversized_files()
for file in oversized[:5]:
    print(f"{file['path']}: {file['tokens']:,} tokens")

# Find duplicates
duplicates = detector.detect_duplicate_content()
for dup in duplicates:
    print(f"{dup['similarity']:.0%} similar: {dup['file1']} ↔ {dup['file2']}")
```

**Thresholds**:
- Oversized: >3,000 tokens OR >800 lines
- Duplicate: >70% content similarity

### 5. `context_impact_analyzer.py`
**Purpose**: Main orchestrator combining all analyses

**Key Features**:
- Runs all analyses in sequence
- Generates comprehensive Markdown reports
- Provides actionable recommendations (immediate/medium/long-term)
- Supports CI mode with budget enforcement

**CLI Arguments**:
```
--scenario {all,baseline,scenarios,bloat}   # Which analysis to run
--output PATH                                # Output file path
--format {markdown,json}                     # Output format
--ci-mode                                    # CI budget check mode
--threshold TOKENS                           # Max tokens for CI (default: 80K)
```

**Example - CI Budget Check**:
```bash
python3 context_impact_analyzer.py --ci-mode --threshold 50000
# Exits with error if max scenario exceeds 50K tokens
```

## 📈 Report Sections

The comprehensive report includes:

1. **Executive Summary**
   - Baseline token count
   - Maximum scenario load
   - Top bloat sources

2. **Baseline Profile**
   - Mandatory files by category
   - Config file breakdowns
   - Budget usage across LLMs

3. **Scenario Simulations**
   - Token breakdown per layer (mandatory/guides/agent/validators)
   - File-by-file analysis
   - Percentage contributions

4. **Bloat Detection**
   - Oversized files with recommendations
   - Duplicate content pairs
   - Config bloat sections
   - Rarely-used mandatory files

5. **Optimization Recommendations**
   - Immediate wins (high impact, low effort)
   - Medium-term improvements
   - Long-term transformations
   - Estimated savings per recommendation

## 🎯 Optimization Recommendations

### Immediate (High Impact, Low Effort)

1. **Create `TDD_CHECKLIST.md`** - Condensed 200-line version of TDD_GUIDE
   - Current: 9,635 tokens → Target: 4,800 tokens
   - Savings: ~4,817 tokens

2. **Deduplicate global validators** - Extract common checklist
   - `codex-global.md` + `claude-global.md` are 96% identical
   - Savings: ~5,000 tokens

3. **Split `TESTING_GUIDE.md`** - Separate unit/integration/e2e guides
   - Current: 7,196 tokens → Target: 3 × 2,000 tokens
   - Savings: ~3,598 tokens (when only needed guide loads)

4. **Modularize `delegation/config.json`**
   - Split into: `file-patterns.json`, `task-types.json`, `zen-mcp.json`
   - Enable lazy loading (load only what's needed)
   - Savings: ~1,500 tokens per task

### Medium-Term (High Impact, Medium Effort)

1. **Lazy-load extended guides**
   - Don't load `TDD_GUIDE.md` unless task explicitly requires TDD
   - Don't load `VALIDATION_GUIDE.md` unless in validation phase
   - Savings: ~3,000 tokens average

2. **Extract validator specs**
   - Move detailed checklists to separate files
   - Keep only metadata in `validators/config.json`
   - Savings: ~1,000 tokens

3. **Cache session next output**
   - Don't re-expand same rules on every call
   - Store expanded rules in session JSON
   - Savings: ~2,000 tokens per subsequent call

### Long-Term (Transformative)

1. **Implement RAG for guides**
   - Semantic search instead of full file loading
   - Query-based retrieval of relevant sections only
   - Savings: ~10,000 tokens

2. **Context budget enforcement**
   - Fail if total context exceeds 50K tokens
   - Force optimization decisions
   - Prevention, not reduction

3. **Smart context pruning**
   - Relevance scoring per section
   - Auto-remove low-relevance content
   - Savings: ~8,000 tokens

## 🧪 Testing

### Unit Tests (Planned)

```bash
# Run unit tests
python3 -m pytest .agents/scripts/tests/context/test_*.py
```

### Integration Test

The analyzer itself IS the integration test - it operates on REAL files with NO mocks.

## 🔄 CI Integration

### GitHub Actions Example

```yaml
# .github/workflows/context-budget.yml
name: Context Budget Check
on: [pull_request]
jobs:
  check-context:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install tiktoken
        run: pip install tiktoken
      - name: Run Context Analyzer
        run: |
          python3 .agents/scripts/tests/context/context_impact_analyzer.py \
            --ci-mode \
            --threshold 80000 \
            --output context-report.md
      - name: Upload Report
        uses: actions/upload-artifact@v3
        with:
          name: context-impact-report
          path: context-report.md
```

## 📚 FAQ

**Q: Why not use mocks?**
A: Mocks don't reflect reality. This toolkit tests ACTUAL files, CLIs, and configurations to give you REAL measurements.

**Q: What if tiktoken isn't installed?**
A: The toolkit includes a fallback estimator (~95% accurate) using word count and character-based heuristics.

**Q: How often should I run this?**
A: Run on every major `.agents/` change, or weekly as part of maintenance.

**Q: What's a good context budget target?**
A: For 200K context window, aim for <50K tokens per task (~25%) to leave room for actual code.

**Q: Can this test session next CLI?**
A: Yes, but it requires a valid session structure. Currently skipped in isolated tests.

## 🤝 Contributing

To add new analysis features:

1. Create a new module in `.agents/scripts/tests/context/`
2. Import it in `context_impact_analyzer.py`
3. Add to `run_full_analysis()` method
4. Update this README

## 📄 License

Same as project application repository.

## 📞 Support

Issues: See `.agents/scripts/tests/context/` module docstrings
Questions: Review generated reports for insights
