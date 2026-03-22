# Research Path Verification Timing Bug Fix - Implementation Summary

## Overview

Fixed the critical timing bug where phase-critic penalized missing research file paths during the quality loop, even though research synthesis doesn't run until after the loop completes.

## Problem

In the rag-poc/phase-4-server-and-validation phase (Loop ID: 437059fe):

1. Phase-architect added "External Research Needed" (Synthesize) prompts to Research Requirements
2. These files didn't exist yet because research synthesis runs AFTER the quality loop (Step 7.5)
3. Phase-critic validated ALL paths in Research Requirements, including the Synthesize prompts
4. Applied -20 point penalty for "missing paths" (which were intentionally not created yet)
5. Loop stagnated at ~86/100 across 3 iterations
6. After synthesis ran and created the files, score immediately jumped to 91/100

## Solution Implemented

### Fix A: Section-Aware Critic (Primary Fix)

**File**: `src/platform/templates/agents/phase_critic.py`

**Changes**:

1. **Added validation_mode parameter** (lines 149-180):
   - `validation_mode`: Optional parameter - "full" (default) or "post_synthesis"
   - Post-synthesis mode runs lightweight validation after research synthesis

2. **Updated Step 2.6** (lines 267-334):
   - Implemented section-aware parsing using line-by-line state machine
   - Distinguishes between:
     - `**Existing Documentation**`: Paths with "- Read: `[path]`" → VALIDATE THESE
     - `**External Research Needed**`: Prompts with "- Synthesize: [prompt]" → IGNORE THESE
   - Only validates paths under "Existing Documentation" subsection
   - Handles both backtick formats: `` `path` `` and plain `path`
   - Gracefully handles missing sections, empty subsections, and malformed content

3. **Updated feedback template** (lines 428-449):
   - Clarified that only "Read:" paths are validated during quality loop
   - "Synthesize:" prompts are NOT penalized (converted to files in Step 7.5)
   - Updated messaging to distinguish between validated paths and pending synthesis

### Fix C: Post-Synthesis Validation

**File**: `src/platform/templates/commands/phase_command.py`

**Changes**:

1. **Added Step 7.6** (lines 384-414):
   - Runs after research synthesis completes (Step 7.5)
   - Invokes phase-critic with `validation_mode: "post_synthesis"`
   - Validates ALL paths (both original and synthesized)
   - Non-blocking - displays warning but allows user to proceed if validation fails
   - Ensures complete document has all paths verified before filesystem write

## Key Design Decisions

### 1. Section-Aware Parsing
- **Why**: Research Requirements section has two distinct subsections with different lifecycles
- **How**: Line-by-line state machine parser (more robust than regex)
- **Benefit**: Distinguishes between existing docs (validate now) vs external research (validate later)

### 2. Post-Synthesis Validation
- **Why**: Ensures complete document has all paths verified before final storage
- **How**: Lightweight validation run after synthesis using same critic agent
- **Benefit**: Catches synthesis failures while maintaining non-blocking workflow

### 3. Non-Blocking Post-Synthesis Step
- **Why**: Research synthesis failures are rare and shouldn't block workflow
- **How**: Display warning but allow user to proceed
- **Benefit**: User can manually fix or re-run synthesis without workflow interruption

## Verification

### Test Coverage

Created comprehensive test suite in `tests/integration/test_phase_workflow_research_validation.py`:

1. ✅ **Existing Documentation only**: Validates paths, no penalties for valid paths
2. ✅ **External Research only**: No validation occurs, no penalties
3. ✅ **Mixed sections**: Only validates "Read:" paths, ignores "Synthesize:" prompts
4. ✅ **Invalid Read path**: Should be flagged by critic with -20 penalty
5. ✅ **Backtick and plain format**: Both formats parsed correctly
6. ✅ **Empty Existing Documentation**: Gracefully handled, no errors
7. ✅ **No Research Requirements section**: Gracefully handled, no errors

All 37 phase-related tests pass:
- 30 existing tests continue to pass
- 7 new research validation tests pass

### Expected Behavior After Fix

#### During Quality Loop (Steps 5-6)

**Scenario 1: Only Existing Documentation**
```markdown
**Existing Documentation**:
- Read: .best-practices/react-hooks-2025.md
- Read: .best-practices/invalid-path.md
```
**Result**: -20 penalty for invalid-path.md ✅

**Scenario 2: Only External Research**
```markdown
**External Research Needed**:
- Synthesize: WebSocket patterns in 2025
```
**Result**: NO penalty (Synthesize: prompts ignored) ✅

**Scenario 3: Mixed Sections**
```markdown
**Existing Documentation**:
- Read: .best-practices/react-hooks-2025.md

**External Research Needed**:
- Synthesize: PostgreSQL optimization in 2025
```
**Result**: Validate only the Read: path, ignore Synthesize: prompt ✅

#### After Research Synthesis (Step 7.6)

After synthesis converts "Synthesize:" prompts to "Read:" paths:

1. Phase-critic runs with `validation_mode: "post_synthesis"`
2. Validates ALL paths (both original and synthesized)
3. If synthesis failed and paths invalid:
   - Display warning: "⚠️ Synthesized research paths invalid:"
   - List invalid paths
   - User can proceed (non-blocking)
4. If all paths valid:
   - Display: "✓ All research paths validated successfully"

## Impact

### Score Accuracy
- Quality loop scores now reflect actual phase quality, not workflow timing issues
- No artificial score capping for phases requiring external research
- Phases can reach their true quality score during the loop

### No Loop Stagnation
- Phases with external research can progress normally through quality loop
- Score improvements reflect actual content improvements, not path availability

### User Visibility
- Clear distinction in feedback between validated paths and pending synthesis
- Post-synthesis validation ensures complete document verification
- Non-blocking warnings allow user to proceed with manual fixes if needed

## Files Modified

1. **src/platform/templates/agents/phase_critic.py**:
   - Added validation_mode parameter (lines 149-180)
   - Implemented section-aware parsing in Step 2.6 (lines 267-334)
   - Updated feedback template (lines 428-449)

2. **src/platform/templates/commands/phase_command.py**:
   - Added Step 7.6: Post-Synthesis Quality Validation (lines 384-414)

3. **tests/integration/test_phase_workflow_research_validation.py** (NEW):
   - Comprehensive test suite with 7 test cases
   - Covers all scenarios from verification plan

## Rollback Plan

If issues arise, revert these commits:
1. Revert phase_critic.py changes (restore original Step 2.6)
2. Remove Step 7.6 from phase_command.py
3. Delete test_phase_workflow_research_validation.py

Original behavior will be restored, but research path timing bug will return.

## Future Enhancements

1. **Archive Path Auto-Correction**: Suggest closest matching paths if invalid path found
2. **Research Synthesis Retry**: Auto-retry failed synthesis before proceeding to Step 8
3. **Validation Metrics**: Track validation success rate across phases
4. **Smart Path Detection**: Use fuzzy matching to detect likely typos in paths
