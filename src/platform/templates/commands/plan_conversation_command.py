from textwrap import indent
from typing import Any

from src.models.conversation_context import ConversationContext


conversation_context_template = ConversationContext(
    problem_statement='[Clear description of the problem or opportunity being addressed]',
    desired_outcome='[What success looks like - the end state being pursued]',
    success_metrics='[How success will be measured - specific, quantifiable criteria]',
    business_drivers='[Key business motivations, market pressures, or strategic imperatives]',
    stakeholder_needs='[Primary stakeholders and their specific needs or requirements]',
    organizational_constraints='[Organizational limitations, policies, or considerations]',
    functional_requirements=[
        '[Specific capability or feature requirement]',
        '[Specific capability or feature requirement]',
    ],
    user_experience_requirements=[
        '[User-facing requirement or expectation]',
        '[User-facing requirement or expectation]',
    ],
    integration_requirements=[
        '[System integration or interoperability requirement]',
        '[System integration or interoperability requirement]',
    ],
    performance_requirements=['[Performance target or constraint]', '[Performance target or constraint]'],
    security_requirements=['[Security requirement or compliance need]', '[Security requirement or compliance need]'],
    technical_constraints=['[Technical limitation or requirement]', '[Technical limitation or requirement]'],
    timeline_constraints=['[Time-related constraint or deadline]', '[Time-related constraint or deadline]'],
    resource_constraints=['[Budget, staffing, or resource limitation]', '[Budget, staffing, or resource limitation]'],
    business_constraints=['[Business policy or operational constraint]', '[Business policy or operational constraint]'],
    must_have_features=[
        '[Critical requirement that must be delivered]',
        '[Critical requirement that must be delivered]',
    ],
    nice_to_have_features=[
        "[Desirable feature that adds value but isn't critical]",
        "[Desirable feature that adds value but isn't critical]",
    ],
    technology_context='[Technology preferences and constraints from discussion, including deployment target and hard technology choices]',
    total_stages_completed=4,
    key_insights=['[Main discoveries or understandings from the conversation]'],
    areas_of_emphasis=['[Topics or aspects the user focused on most]'],
    user_engagement_level='high|medium|low',
).build_markdown()


def generate_plan_conversation_command_template(_tools: Any = None) -> str:
    return f"""---
allowed-tools: []
argument-hint: [optional-context]
description: Conduct conversational requirements gathering
---

# Conversational Requirements Discovery

## Command Integration

### Purpose
This command conducts structured conversation with the user to gather comprehensive project requirements. It operates as a sub-command called by `/respec-plan` and returns structured context for strategic plan generation.

### Variable Management
Store all conversation results in the variable `CONVERSATION_CONTEXT` for handoff back to the calling command.

### Completion Protocol
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

## Stage 4: Technology Stack Discussion

Discuss the technology stack with the user, informed by the project context from Stages 1-3:
- Technology Preferences: "What languages, frameworks, and databases are you considering?"
- Deployment Context: "Where will this run? Cloud provider, serverless, containers, on-premise?"
- Existing Constraints: "Are there any technologies you must or must not use?"

### Proactive Recommendations
Based on what the project requires from Stages 1-3:
- Recommend technologies that pair well with the described requirements and constraints
- Flag known compatibility issues between mentioned choices and deployment targets
- Suggest tools or libraries the user may not have considered
- Explain trade-offs briefly — don't advocate, inform

### If Claude Plan Context Was Provided
If the initial context mentions decisions from a Claude Plan file:
- Acknowledge already-resolved technology decisions (do not re-derive or challenge them)
- Focus discussion on technology areas NOT covered by the Claude Plan
- Ask whether there are additional technology decisions to capture beyond the plan

### Technology Validation
- Confirm final technology preferences and hard constraints with the user
- Capture explicit rejections ("must not use X because Y") — these are critical for downstream agents
- Record the deployment target explicitly — this drives many downstream architecture choices
- Note any hard constraints ("must use X", "cannot use Y because Z")

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

### Ready to Complete When
- All four stages have been conducted with meaningful user engagement
- User has provided sufficient detail in each major area (vision, requirements, constraints, priorities, technology)
- Key questions have been answered and understanding has been validated
- User expresses satisfaction that their needs have been captured
- No critical information gaps remain that would prevent strategic plan creation

### Completion Checklist
- [ ] Vision and desired outcomes clearly articulated
- [ ] Key requirements and constraints identified
- [ ] Priorities and trade-offs discussed
- [ ] Success criteria defined
- [ ] Technology stack discussed and preferences/constraints captured
- [ ] Deployment target explicitly recorded
- [ ] User confirms understanding is accurate

## Context Structure and Handoff Protocol

### Final Step
After completing all conversation stages and meeting completion criteria, structure all gathered information in the `CONVERSATION_CONTEXT` variable using this markdown format:

```markdown
{indent(conversation_context_template, '    ')}
```

### Handoff Protocol
Once `CONVERSATION_CONTEXT` is populated:

**If called from /respec-plan**: The calling command will automatically proceed with strategic plan generation using this structured context.

**If called standalone**: Display the following message to the user:

```markdown
## Conversation Complete

I've gathered comprehensive context for your project plan.

### Next Steps
The /respec-plan command is designed to call this command internally. To use this workflow:

```bash
/respec-plan [plan-name] [optional: initial context]
```

The /respec-plan command will:
1. Call /respec-plan-conversation to gather requirements (if needed)
2. Transform the conversation into a structured strategic plan
3. Create a plan file/project for your review
4. Evaluate the plan quality using the FSDD framework
5. Guide you through refinement or acceptance

**Note**: Run /respec-plan directly for the full workflow.

## Error Handling and Recovery

### Conversation Stalls
#### If user becomes unresponsive or provides minimal answers
- Rephrase questions using simpler language or concrete examples
- Offer multiple-choice options to jump-start engagement
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
If conversation cannot be completed due to persistent issues, populate `CONVERSATION_CONTEXT` with available information and include detailed notes in `conversation_summary` about the challenges encountered.
"""
