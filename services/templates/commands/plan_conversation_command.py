from typing import Any


def generate_plan_conversation_command_template(_tools: Any = None) -> str:
    return """---
allowed-tools: []
argument-hint: [optional-context]
description: Conduct conversational requirements gathering
---

# Conversational Requirements Discovery

## Command Integration

#### Purpose
This command conducts structured conversation with the user to gather comprehensive project requirements. It operates as a sub-command called by `/specter-plan` and returns structured context for strategic plan generation.

#### Variable Management
Store all conversation results in the variable `CONVERSATION_CONTEXT` for handoff back to the calling command.

#### Completion Protocol
This command completes when all three stages have been executed and comprehensive context has been gathered in structured format.

## Stage 1: Vision and Context Discovery
Begin with broad, open-ended exploration:
- Vision Understanding: "Tell me about what you're trying to build or achieve"
- Context Gathering: "What's driving this project? What problem are you solving?"
- Success Exploration: "How will you know when this is successful?"
- Stakeholder Context: "Who are the main people involved or affected by this?"

### Conversational Techniques
- **Follow-up Questions**: Build naturally on user responses with related questions
- **Clarifying Examples**: Use examples to validate understanding and prompt additional details
- **Active Listening**: "I hear that [X] is important because..."
- **Gentle Probing**: Ask for more information when answers seem incomplete without being pushy
- **Context Bridging**: Connect different parts of the conversation to build comprehensive understanding
- **Open Space**: Give user time to add what they think matters

## Stage 2: Progressive Requirement Refinement
Guide conversation toward more specific details:
- Scope Clarification: "Let's talk about what this includes and what it doesn't"
- User Experience Focus: "Walk me through how someone would use this"
- Integration Context: "What other systems or tools does this need to work with?"
- Constraint Exploration: "What limitations or requirements do we need to work within?"

### Understanding Validation
- **Summarization**: "So if I understand correctly, you're looking for..."
- **Gap Identification**: "I want to make sure I'm not missing anything important..."
- **Priority Confirmation**: "It sounds like [X] is more important than [Y], is that right?"
- **Constraint Validation**: "Given what you've told me about [constraint], does that mean...?"

## Stage 3: Detail and Validation
Refine understanding with specific validation:
- Requirement Validation: "Let me make sure I understand correctly..."
- Priority Clarification: "What's most important if we had to prioritize?"
- Timeline Context: "What's the timeline you're thinking about?"
- Success Criteria: "How will we measure if this is working well?"

### Conversation Management
- **Pacing**: Allow natural conversation flow without rushing toward detailed requirements
- **Context Bridging**: Connect different parts of conversation to maintain comprehensive understanding
- **Comfort Building**: Create a comfortable environment for sharing incomplete thoughts and ideas
- **Active Response**: Respond to what the user emphasizes and follow their natural direction

## Quality Conversation Indicators

### Good Conversation Flow
- User provides information voluntarily without feeling interrogated
- Conversation builds naturally from general to specific
- User asks questions and engages actively in the discussion
- Understanding is validated before moving to new topics
- User expresses confidence that their needs are being understood

### Effective Requirement Gathering
- Requirements emerge naturally from conversation rather than through direct questioning
- User provides context and reasoning behind requirements
- Contradictions or conflicts are identified and resolved through discussion
- Priorities become clear through natural conversation progression
- User feels heard and understood throughout the process

## Conversation Completion Criteria

#### Ready to Complete When
- All three stages have been conducted with meaningful user engagement
- User has provided sufficient detail in each major area (vision, requirements, constraints, priorities)
- Key questions have been answered and understanding has been validated
- User expresses satisfaction that their needs have been captured
- No critical information gaps remain that would prevent strategic plan creation

#### Completion Checklist
- [ ] Vision and desired outcomes clearly articulated
- [ ] Key requirements and constraints identified
- [ ] Priorities and trade-offs discussed
- [ ] Success criteria defined
- [ ] User confirms understanding is accurate

## Context Structure and Handoff Protocol

#### Final Step
After completing all conversation stages and meeting completion criteria, structure all gathered information in the `CONVERSATION_CONTEXT` variable using this format:

```json
{
  "vision": {
    "problem_statement": "...",
    "desired_outcome": "...",
    "success_metrics": "..."
  },
  "business_context": {
    "business_drivers": "...",
    "stakeholder_needs": "...",
    "organizational_constraints": "..."
  },
  "requirements": {
    "functional": [...],
    "user_experience": [...],
    "integration": [...],
    "performance": [...],
    "security": [...],
    "technical_constraints": [...]
  },
  "constraints": {
    "timeline": [...],
    "resource": [...],
    "business": [...],
    "technical": [...]
  },
  "priorities": {
    "must_have": [...],
    "nice_to_have": [...]
  },
  "conversation_summary": {
    "total_stages_completed": 3,
    "key_insights": [...],
    "areas_of_emphasis": [...],
    "user_engagement_level": "high|medium|low"
  }
}
```

#### Handoff Protocol
Once `CONVERSATION_CONTEXT` is populated:

**If called from /specter-plan**: The calling command will automatically proceed with strategic plan generation using this structured context.

**If called standalone**: Display the following message to the user:

```markdown
## Conversation Complete

I've gathered comprehensive context for your project plan.

#### Next Steps
The /specter-plan command is designed to call this command internally. To use this workflow:

```bash
/specter-plan [project-name] [optional: initial context]
```

The /specter-plan command will:
1. Call /specter-plan-conversation to gather requirements (if needed)
2. Transform the conversation into a structured strategic plan
3. Create a plan file/project for your review
4. Evaluate the plan quality using the FSDD framework
5. Guide you through refinement or acceptance

**Note**: Run /specter-plan directly for the full workflow.
```

## Error Handling and Recovery

### Conversation Stalls
#### If user becomes unresponsive or provides minimal answers
- Rephrase questions using simpler language or concrete examples
- Offer multiple-choice options to jumpstart engagement
- Break complex questions into smaller, more manageable parts
- Example: "I notice you're hesitating. Would it help if I gave you some examples of what I mean?"

### Scope Overwhelm
#### If user seems overwhelmed by the scope of questions
- Focus on one area at a time and reassure about the process
- Emphasize that incomplete answers can be refined later
- Suggest starting with what they're most confident about
- Example: "Let's start with just the core problem you're trying to solve. We can build from there."

### Technical Confusion
#### If user gets bogged down in technical details
- Redirect to business outcomes and user value
- Defer technical implementation discussions
- Focus on "what" rather than "how"
- Example: "Let's focus on what you want to achieve first. We'll figure out the technical approach later."

### Information Gaps
#### If critical information is missing after all stages
- Identify specific gaps and ask targeted follow-up questions
- Use hypothetical scenarios to help user think through unclear areas
- Suggest reasonable assumptions that can be validated later
- Document gaps clearly for strategic plan generation

### Conversation Recovery
#### If conversation derails or becomes unproductive
- Summarize progress made so far to re-establish momentum
- Identify the most important remaining areas to cover
- Offer to change approach or take a break if needed
- Example: "We've made good progress on X and Y. Let's focus on Z to wrap up the key pieces."

#### Error Escalation
If conversation cannot be completed due to persistent issues, populate `CONVERSATION_CONTEXT` with available information and include detailed notes in `conversation_summary` about the challenges encountered."""
