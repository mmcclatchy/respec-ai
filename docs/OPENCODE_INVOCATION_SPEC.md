# OpenCode Invocation Specification for respec-ai

**Purpose**: How OpenCode's command/agent invocation works and specific structural requirements for respec-ai prompts

**Date**: 2026-03-30

---

## Executive Summary

OpenCode uses a different execution model than Claude Code:

- **Claude Code**: Uses /command syntax that agents can invoke
- **OpenCode**: Uses Task tool with explicit subagent_type and prompt parameters
- **Critical**: The /respec-* bash commands in current prompts will fail in OpenCode

---

## OpenCode Architecture

### Configuration (opencode.json)

    {
      "agent": {
        "agent-name": {
          "mode": "primary|subagent",
          "prompt": "{file:path/to/prompt.md}",
          "tools": { ... },
          "permission": { ... }
        }
      },
      "command": {
        "command-name": {
          "template": "{file:path/to/prompt.md}",
          "agent": "agent-name"
        }
      },
      "mcp": { }
    }

### Agent Modes

**Primary Agents** (mode: primary):

- Can interact directly with users
- Can use Task tool to invoke subagents
- Execute when user triggers associated command

**Subagents** (mode: subagent):

- Run in isolated environment
- Cannot interact with users
- Execute only when invoked via Task tool

---

## The Core Problem

Current respec-ai prompts use this syntax:

    ## Step 2: Invoke Conversation
    ```bash
    /respec-plan-conversation [CONTEXT]
    ```

This fails because:

1. /respec-plan-conversation is not a bash command
2. OpenCode does not parse /command syntax inside prompts
3. The agent tries to execute it in bash, which fails

---

## How OpenCode Actually Invokes Agents

Use the Task tool with explicit parameters:

    CALL task:
      subagent_type: "respec-plan-conversation"
      prompt: "Complete instructions for the subagent..."

This is the ONLY way to invoke subagents in OpenCode.

---

## Required Prompt Structure

### Pattern 1: Primary Agent Handles User Dialogue

For user-facing steps, the primary agent should handle dialogue directly:

    ## Step 2: Conversational Requirements Gathering
    
    As the primary agent, conduct the 6-stage conversation:
    
    Stage 1: Vision and Context Discovery
    - Ask: "Tell me about what you're trying to build"
    - Wait for user response
    - Store in variable: STAGE_1_VISION
    
    Stage 2: Progressive Requirement Refinement  
    - Ask: "Let's talk about what this includes"
    - Wait for user response
    - Store in variable: STAGE_2_SCOPE
    
    [Continue for all 6 stages...]
    
    Compile Results:
    - Structure all responses into CONVERSATION_CONTEXT
    - Use ConversationContext format with all sections

**Use when**: Step requires user interaction

---

### Pattern 2: Explicit Task Tool Invocation

For invoking subagents without user interaction:

    ## Step 2: Invoke Conversation Agent
    
    Use the Task tool to launch respec-plan-conversation:
    
    CALL task with:
      - subagent_type: "respec-plan-conversation"
      - prompt: |
          Context from Claude Plan: {{CLAUDE_PLAN_FILE}}
          Initial User Context: {{CONVERSATION_INITIAL_CONTEXT}}
          
          Your Task:
          Conduct 6-stage conversational requirements gathering.
          Return structured CONVERSATION_CONTEXT in markdown format.
          
          Expected Output Format:
          - Vision and Objectives section
          - Business Context section  
          - Requirements sections
          - Technology Context section
          - Architecture Direction section
          - Scope Boundaries section
          - Risk Assessment section
          - Quality Bar section
    
    Wait for Task completion
    Store returned value as CONVERSATION_CONTEXT

**Use when**: Step can be isolated from user interaction

---

### Pattern 3: Inline Logic

For simple operations, include logic directly:

    ## Step 4: Quality Assessment
    
    Perform quality check inline (no subagent invocation):
    
    Evaluate Against FSDD Framework:
    - Completeness: Are all requirements covered?
    - Clarity: Is the plan unambiguous?
    - Measurability: Are success criteria quantified?
    - Feasibility: Can this be implemented?
    
    Calculate Quality Score:
    - Score each dimension 0-100
    - Average for overall score
    
    Return Feedback:
    - Store CRITIC_FEEDBACK with specific issues
    - Include recommendations for improvement

**Use when**: Logic is simple and evaluation criteria are clear

---

## File Locations

### Configuration

- File: opencode.json
- Location: Project root
- Contains: Agent definitions, command mappings, MCP servers

### Prompt Files

- Location: .opencode/prompts/*.md
- Naming: Match agent name (respec-plan.md for agent respec-plan)
- Reference: Use {file:.opencode/prompts/name.md} in opencode.json

### Generated Artifacts

- Plans: .respec-ai/plans/{plan-name}/plan.md
- Phases: .respec-ai/plans/{plan-name}/phase-{n}-{name}.md
- State: .respec-ai/loops/{loop-id}/state.json (if file-based)

---

## Permission Structure

Primary agents need explicit permission to invoke subagents:

    "permission": {
      "task": {
        "*": "deny",
        "respec-plan-conversation": "allow",
        "respec-plan-critic": "allow",
        "respec-plan-analyst": "allow"
      }
    }

Without this, Task invocations will fail.

---

## Tool Availability

### Always Available

- read, write, edit, glob, grep, bash
- task (for invoking subagents)
- webfetch, todowrite, skill

### Must Be Explicitly Enabled

In agent definition, list allowed tools:

    "tools": {
      "read": true,
      "write": true,
      "bash": true
    }

### Currently Unavailable (Bug)

All mcp__respec-ai__* tools - root cause is empty mcp section in opencode.json

---

## Platform Comparison

| Scenario | Claude Code | OpenCode |
|----------|-------------|----------|
| User triggers workflow | /respec-plan name context | /respec-plan name context |
| Agent invoked | respec-plan agent runs | respec-plan agent runs |
| Agent invokes subagent | /respec-plan-conversation | Use Task tool with subagent_type |
| User dialogue | Built into command | Primary agents can ask questions |
| State management | MCP tools | File-based or MCP (when fixed) |

---

## Specific Fixes Required

### Fix 1: respec-plan.md

Remove this:

    ## Step 2: Conversational Requirements Gathering
    ```bash
    /respec-plan-conversation [CONVERSATION_INITIAL_CONTEXT]
    ```

Replace with either:

    ## Step 2: Conversational Requirements Gathering
    
    Primary Agent conducts directly:
    - Ask user questions for all 6 stages
    - Store responses in variables  
    - Compile CONVERSATION_CONTEXT

Or:

    ## Step 2: Conversational Requirements Gathering
    
    CALL task:
      subagent_type: "respec-plan-conversation"
      prompt: "Context and instructions..."
    
    Wait for completion
    Store result as CONVERSATION_CONTEXT

---

### Fix 2: respec-roadmap.md

Remove this:

    Invoke roadmap agent:
    ```bash
    /respec-roadmap agent
    ```

Replace with:

    ## Step 3.1: Invoke Roadmap Agent
    
    CALL task:
      subagent_type: "respec-roadmap"
      prompt: |
        Loop ID: {{ROADMAP_LOOP_ID}}
        Plan Name: {{PLAN_NAME}}
        
        Generate implementation roadmap from strategic plan
    
    Wait for completion

---

### Fix 3: All Agent-to-Agent Calls

Replace ALL instances of:

    ```bash
    /respec-{agent-name} [args]
    ```

With:

    CALL task:
      subagent_type: "respec-{agent-name}"
      prompt: "Complete context and instructions..."

---

## Dynamic Templating

If respec-ai uses platform-specific code generation:

    def generate_invocation(platform, agent_name, context_vars):
        if platform == "claude_code":
            return f"/respec-{agent_name} {' '.join(context_vars)}"
        elif platform == "opencode":
            return f"CALL task:\n  subagent_type: \"{agent_name}\"\n  prompt: ..."

For unified templates with conditional logic:

    ## Step X: Invoke Agent
    
    IF PLATFORM == "claude_code":
      /respec-{agent-name} [context]
    
    IF PLATFORM == "opencode":
      CALL task:
        subagent_type: "respec-{agent-name}"
        prompt: [Context formatted for subagent]

---

## Summary

Required changes for OpenCode compatibility:

1. Remove bash-style /command invocations from all prompts
2. Replace with explicit Task tool calls using subagent_type parameter
3. Ensure permissions are correctly configured in opencode.json
4. Fix MCP server registration (empty mcp section)
5. Test in OpenCode environment to verify invocation chains
6. Consider platform-specific template variants to avoid conditional bloat

---

## Testing

Verify prompts do not contain bash command syntax:

    def test_opencode_invocation_syntax():
        prompt = generate_prompt(platform="opencode")
        assert "/respec-" not in prompt or "CALL task" in prompt
        assert "subagent_type" in prompt

Integration test:

1. Generate OpenCode config and prompts
2. Load in OpenCode environment
3. Execute /respec-plan foundation test-context
4. Verify Task invocations succeed
5. Verify file outputs created correctly
