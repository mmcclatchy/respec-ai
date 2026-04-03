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
    technology_context='[Deployment target and general technology preferences from discussion]',
    technology_decisions=[
        '[Technology chosen — justification tied to project requirements (e.g., "PostgreSQL — relational data model, team familiarity, managed hosting on DO")]',
    ],
    technology_rejections=[
        '[Technology rejected — specific reason preventing future re-derivation (e.g., "WeasyPrint — requires libpango/libcairo, incompatible with serverless deployment")]',
    ],
    architecture_direction='[High-level component structure, integration points, deployment model, and data flow established during conversation]',
    anti_requirements=[
        '[Thing the system must NOT do — prevents scope creep (e.g., "Must not replace existing auth system — SSO integration only")]',
    ],
    performance_targets=[
        '[Quantified target (e.g., "API responses < 200ms p95", "Support 1000 concurrent users", "Process 10k records/min")]',
    ],
    risk_assessment=[
        '[Technical risk with severity/likelihood/mitigation (e.g., "HIGH: Third-party API rate limits — mitigation: local caching layer")]',
    ],
    quality_bar='[Test coverage minimum, security requirements, accessibility standards, performance thresholds]',
    total_stages_completed=6,
    key_insights=['[Main discoveries or understandings from the conversation]'],
    areas_of_emphasis=['[Topics or aspects the user focused on most]'],
    user_engagement_level='high|medium|low',
).build_markdown()


def generate_plan_conversation_command_template(tools: Any = None) -> str:
    plan_command_name = getattr(tools, 'plan_command_name', 'respec-plan')
    plan_conversation_command_name = getattr(tools, 'plan_conversation_command_name', 'respec-plan-conversation')
    plan_command_invocation = getattr(
        tools,
        'plan_command_invocation',
        'Invoke the `respec-plan` workflow with: `[plan-name] [optional: initial context]`.',
    )

    return f"""---
allowed-tools: mcp__exa__web_search_exa, Read
argument-hint: [optional-context]
description: Conduct conversational requirements gathering
---

# Conversational Requirements Discovery

## How to Conduct This Conversation

This is a genuine requirements discovery conversation — NOT a questionnaire.

═══════════════════════════════════════════════
MANDATORY CONVERSATIONAL PACING PROTOCOL
═══════════════════════════════════════════════
MUST ask exactly 1-2 questions per message. Wait for user response.
Your message contains questions — then STOP and wait for the user.

VIOLATION: Asking 3 or more questions in a single message.
           This overwhelms the user and reduces response quality.
═══════════════════════════════════════════════

**Pacing:**
- Ask 1-2 questions per message. Wait for the user to respond before continuing.
- Spend multiple turns on a topic if it's rich. Move on only when you genuinely understand.
- The bullet points under each stage are topics to explore, NOT a list to ask all at once.

**Depth over breadth:**
- Follow up on what the user says. Dig into their answers before moving to new topics.
- If the user mentions something interesting or uncertain, explore it before changing subjects.
- It's better to deeply understand 3 topics than to superficially cover 6.

**When to move on:**
- Move on when you can summarize the topic back to the user and they confirm your understanding.
- Move on when the user gives short, confident answers — they've said what they need to say.
- Move on if you've asked 2-3 follow-ups on the same point and the user isn't adding new information.
- If the user signals they want to move forward ("that's about it", "let's move on", "yeah that covers it"), move on immediately.

**Natural flow:**
- Follow the user's lead — if they jump ahead to technology, go with it.
- Transitions between stages should be invisible. Don't announce stage numbers.
- Do NOT present numbered question lists or bullet lists of questions.

**Handoff:** Store all conversation results in the variable `CONVERSATION_CONTEXT` for handoff back to the calling command. The conversation completes when all six stages have been covered with meaningful depth.

## Stage 1: Vision and Context Discovery
Start with a single open question and build from there. Explore the user's idea before moving on.

Open with something like: "Tell me about what you're building — what problem are you trying to solve?"

Then follow the thread. Topics to cover through natural follow-up (not all at once):
- What's driving this project
- What success looks like
- Who's involved or affected

### Conversational Techniques
- **Follow-up Questions**: Build naturally on user responses with related questions
- **Clarifying Examples**: Use examples to validate understanding and prompt additional details
- **Active Listening**: "I hear that [X] is important because..."
- **Gentle Probing**: Ask for more information when answers seem incomplete without being pushy
- **Context Bridging**: Connect different parts of the conversation to build comprehensive understanding
- **Open Space**: Give user time to add what they think matters

## Stage 2: Progressive Requirement Refinement
As the vision becomes clear, naturally explore scope and requirements through follow-up.

Topics to cover through natural follow-up (not all at once):
- What's included and what's explicitly not
- How someone would actually use this
- What other systems or tools it needs to work with
- What limitations or requirements exist

### Understanding Validation
- **Summarization**: "So if I understand correctly, you're looking for..."
- **Gap Identification**: "I want to make sure I'm not missing anything important..."
- **Priority Confirmation**: "It sounds like [X] is more important than [Y], is that right?"
- **Constraint Validation**: "Given what you've told me about [constraint], does that mean...?"

## Stage 3: Detail and Validation
Pause to validate your understanding before going deeper. Summarize what you've heard and confirm.

Topics to cover through natural follow-up (not all at once):
- Validate your understanding: "Let me make sure I've got this right..."
- Priorities if trade-offs are needed
- Timeline expectations
- How success will be measured

### Conversation Management
- **Pacing**: Allow natural conversation flow without rushing toward detailed requirements
- **Context Bridging**: Connect different parts of conversation to maintain comprehensive understanding
- **Comfort Building**: Create a comfortable environment for sharing incomplete thoughts and ideas
- **Active Response**: Respond to what the user emphasizes and follow their natural direction

## Decision Facilitation Pattern

When a question involves technology choices, architecture trade-offs, or design decisions
with meaningful impact, use this pattern rather than open-ended questions:

1. Present 2-3 most viable options (not an exhaustive list)
2. For each option, provide:
   - What it is (one sentence)
   - Pros (2-3 points, grounded in THIS project's specific context)
   - Cons (2-3 points, honest about trade-offs)
   - Best suited for (when this option shines)
3. State your recommendation with reasoning tied to the project's requirements
4. Ask the user which direction they'd like to go

Frame as: "Here's what I'd consider — what resonates with you?"
NOT as: "I recommend X, shall I proceed?"

The user may know things you don't. Their choice overrides your recommendation.
If they choose something you wouldn't, ask one clarifying question to make sure they've
considered the key trade-off — then honor their decision and record it with their reasoning.

## Stage 4: Technology Stack Discussion

Discuss the technology stack, informed by what you've learned so far.

Start by exploring what the user already has in mind before introducing options.

Topics to cover through natural follow-up (not all at once):
- What languages, frameworks, or databases they're considering
- Where this will run (cloud, serverless, containers, on-premise)
- Any must-use or must-not-use technologies

### If Claude Plan Context Was Provided
If the initial context mentions decisions from a Claude Plan file:
- Acknowledge already-resolved technology decisions (do not re-derive or challenge them)
- Focus discussion on technology areas NOT covered by the Claude Plan
- Ask whether there are additional technology decisions to capture beyond the plan

═══════════════════════════════════════════════
MANDATORY TECHNOLOGY DISCOVERY PROTOCOL
═══════════════════════════════════════════════
After understanding the user's initial technology preferences,
you MUST execute technology search. This is NOT optional.

1. Derive 2-3 search queries from the problem domain, requirements, and deployment target
   Examples:
   - "best Python [problem-domain] libraries 2026"
   - "[deployment-target] compatible [technology-category] frameworks"
   - "[specific-requirement] open source tools actively maintained"

2. CALL mcp__exa__web_search_exa for each query (num_results=5)

3. Filter results for:
   - Actively maintained (commits within 6 months)
   - Good documentation
   - Relevant to the project's specific constraints and deployment target

4. Present findings using the Decision Facilitation Pattern:
   "Based on your requirements, I found some technologies worth considering:"
   - For each relevant find: name, what it does, why it's relevant to THIS project
   - If user already mentioned a technology and search confirms it's a good fit, say so
   - If search reveals a better alternative the user didn't mention, present both options

5. If user is already familiar with search results, move on quickly

IF user already knows their stack: Execute search anyway to confirm or surface alternatives.
IF search returns no useful results: Note "Technology search completed — no additional options found" and proceed.

VIOLATION: Skipping technology search because the user "seems knowledgeable"
           or "already has preferences." Search MUST always execute.
═══════════════════════════════════════════════

### Technology Validation and Capture
Confirm and record all technology decisions:
- Confirm final technology preferences and hard constraints
- Capture explicit rejections with specific reasons — these are critical for downstream agents
  (e.g., "WeasyPrint rejected — requires libpango/libcairo, incompatible with serverless")
- Record deployment target explicitly — this drives many downstream architecture choices
- Note open questions that still need investigation

## Stage 5: Architecture Direction

Discuss the high-level system design. The goal is to establish direction so a phase-architect
has a starting point to refine — not to produce detailed architecture.

If the user is unsure about architecture, use the Decision Facilitation Pattern to sketch
2-3 options based on what you've learned about their project.

Topics to cover through natural follow-up (not all at once):
- How the major pieces of the system work together (components, services)
- What existing systems this needs to connect to
- Where data comes from, where it goes, and what transforms it
- How this will be deployed
- The 2-3 hardest technical problems they foresee

## Stage 6: Scope Boundaries and Risk Assessment

Ground the plan in reality. This is where you define what the system must NOT do, identify
risks, and set quality expectations.

Topics to cover through natural follow-up (not all at once):
- What the system MUST NOT do (anti-requirements)
- Expected load and performance targets (offer sensible defaults if user is unsure)
- What could go wrong technically — surface the challenges from Stage 5 as risks
- Quality bar: test coverage, security, accessibility expectations

═══════════════════════════════════════════════
MANDATORY ANTI-REQUIREMENTS PROTOCOL
═══════════════════════════════════════════════
The conversation MUST NOT complete without at least ONE anti-requirement.
Anti-requirements define what the system MUST NOT do — they prevent
scope creep in downstream phases.

IF the user has not mentioned any anti-requirements:
  Ask directly: "What should the system explicitly NOT do?"
  Provide examples from their context: "For example, should it NOT
  replace [existing system]?"

IF the user says "nothing comes to mind":
  Suggest 2-3 anti-requirements based on the project context.
  Ask the user to confirm or modify.

VIOLATION: Generating CONVERSATION_CONTEXT with an empty
           anti_requirements list.
═══════════════════════════════════════════════

For each risk identified: capture severity, likelihood, and a mitigation approach.
Use the Decision Facilitation Pattern for high-severity risks with multiple mitigations.

### Final Validation
Before wrapping up, summarize what you've heard across all topics and ask the user to confirm.
"Does this capture everything important? Is there anything I missed or that changed your thinking?"

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

═══════════════════════════════════════════════
MANDATORY COMPLETION GATE
═══════════════════════════════════════════════
ALL of the following MUST be true before generating CONVERSATION_CONTEXT:

- [ ] Vision and desired outcomes clearly articulated
- [ ] Key requirements and constraints identified
- [ ] Priorities and trade-offs discussed
- [ ] Success criteria defined
- [ ] Technology stack discussed, searched, and decisions captured with rationale
- [ ] Rejected technologies recorded with specific reasons
- [ ] Deployment target explicitly recorded
- [ ] Architecture direction established (components, integrations, data flow)
- [ ] Anti-requirements documented (what system MUST NOT do)
- [ ] Performance/scale targets defined (or sensible defaults accepted)
- [ ] Technical risks identified with mitigations
- [ ] User confirms understanding is accurate

IF ANY item is unchecked: DO NOT generate CONVERSATION_CONTEXT.
Instead, continue the conversation to cover the missing topic.

VIOLATION: Generating CONVERSATION_CONTEXT with unchecked items.
           Incomplete context produces a plan missing critical sections.
═══════════════════════════════════════════════

## Context Structure and Handoff Protocol

### Final Step
After completing all conversation stages and passing the MANDATORY COMPLETION GATE, structure all
gathered information in the `CONVERSATION_CONTEXT` variable using this markdown format.

You MUST populate EVERY field in the template below.
IF a field has no relevant information from the conversation, set it to "Not discussed — requires follow-up".
Do NOT leave any field with placeholder text like "[Description]".

```markdown
{indent(conversation_context_template, '    ')}
```

### Handoff Protocol
Once `CONVERSATION_CONTEXT` is populated:

**If called from {plan_command_name}**: The calling command will automatically proceed with strategic
plan generation using this structured context.

**If called standalone**: Display the following message to the user:

```markdown
## Conversation Complete

I've gathered comprehensive context for your project plan.

### Next Steps
The {plan_command_name} workflow is designed to call this command internally. To use this workflow:

{plan_command_invocation}

The {plan_command_name} workflow will:
1. Call {plan_conversation_command_name} to gather requirements (if needed)
2. Transform the conversation into a structured strategic plan
3. Create a plan file/project for your review
4. Evaluate the plan quality using the FSDD framework
5. Guide you through refinement or acceptance

**Note**: Run {plan_command_name} directly for the full workflow.

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
If conversation cannot be completed due to persistent issues, populate `CONVERSATION_CONTEXT`
with available information and include detailed notes in `conversation_summary` about
the challenges encountered.
"""
