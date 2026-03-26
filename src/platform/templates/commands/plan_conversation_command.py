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


def generate_plan_conversation_command_template(_tools: Any = None) -> str:
    return f"""---
allowed-tools: [mcp__exa__web_search_exa, Read]
argument-hint: [optional-context]
description: Conduct conversational requirements gathering
---

# Conversational Requirements Discovery

## Command Integration

### Purpose
This command conducts structured conversation with the user to gather comprehensive project
requirements. It operates as a sub-command called by `/respec-plan` and returns structured
context for strategic plan generation.

### Variable Management
Store all conversation results in the variable `CONVERSATION_CONTEXT` for handoff back to the
calling command.

### Completion Protocol
This command completes when all six stages have been executed and comprehensive context has
been gathered in structured format.

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

Discuss the technology stack, informed by the project context from Stages 1-3.

### Technology Preferences
- "What languages, frameworks, and databases are you considering?"
- "Where will this run? Cloud provider, serverless, containers, on-premise?"
- "Are there any technologies you must or must not use?"

### If Claude Plan Context Was Provided
If the initial context mentions decisions from a Claude Plan file:
- Acknowledge already-resolved technology decisions (do not re-derive or challenge them)
- Focus discussion on technology areas NOT covered by the Claude Plan
- Ask whether there are additional technology decisions to capture beyond the plan

### Technology Discovery (Active Search)
After understanding the user's initial preferences, search for relevant technologies:

```text
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
```

### Technology Validation and Capture
Confirm and record all technology decisions:
- Confirm final technology preferences and hard constraints
- Capture explicit rejections with specific reasons — these are critical for downstream agents
  (e.g., "WeasyPrint rejected — requires libpango/libcairo, incompatible with serverless")
- Record deployment target explicitly — this drives many downstream architecture choices
- Note open questions that still need investigation

## Stage 5: Architecture Direction

Discuss the high-level system design, informed by technology decisions from Stage 4.
Goal: establish direction so the phase-architect has a starting point to refine — not to
produce detailed architecture.

### Component Structure
- "How do you envision the major pieces of this system working together?"
- "What are the main components or services you see?"
- If user is unsure, use the Decision Facilitation Pattern to sketch options:
  - Monolith with clear module boundaries
  - Service-oriented with defined API boundaries
  - Serverless/event-driven
  (Select context-appropriate options based on the project's requirements)

### Integration Landscape
- "What existing systems does this need to connect to?"
- "What APIs, databases, or services already exist that this will interact with?"
- "Are there any systems this explicitly should NOT connect to or replace?"

### Data Flow
- "Where does data come from, where does it go, and what transforms it?"
- "What's the primary data store? Are there secondary stores or caches?"
- "What data format or protocol constraints exist?"

### Deployment Model
- "How will this be deployed — containers, serverless, VMs, managed services?"
- "What does the production environment look like?"
- "What's the scaling model — horizontal, vertical, auto-scaling?"
- This should confirm/expand on deployment discussion from Stage 4

### Key Technical Challenges
- "What are the 2-3 hardest technical problems you foresee?"
- "Are there any technical unknowns that make you nervous?"
- Note these — they become risk inputs for Stage 6

## Stage 6: Scope Boundaries and Risk Assessment

Ground the plan in reality with explicit constraints and risk awareness.

### Anti-Requirements
- "What should this system explicitly NOT do?"
- "Are there features that seem obvious to build but you want to avoid?"
- "Any past experiences where scope creep caused problems on similar projects?"
- Anti-requirements propagate to Phase scope boundaries and prevent over-building

### Performance and Scale Targets
- "What's the expected load — concurrent users, requests/sec, data volume?"
- "What are the latency requirements — real-time, near-real-time, batch processing?"
- "What's the growth trajectory — 10x in a year, or steady state?"
- If user is unsure, offer sensible defaults based on project type with reasoning

### Risk Assessment
- "Based on everything we've discussed, what could go wrong technically?"
- "What would make you consider this project a failure even if it technically ships?"
- Surface the key technical challenges identified in Stage 5
- For each risk: severity (High/Medium/Low), likelihood, and a mitigation approach
- Use the Decision Facilitation Pattern for high-severity risks with multiple mitigations

### Quality Bar
- "What's the minimum test coverage you'd be comfortable with?"
- "Are there security or compliance requirements I should know about?"
- "What's the accessibility requirement for the UI?"
- If user hasn't thought about these, present sensible defaults with brief reasoning

### Final Validation
- Summarize all 6 stages in a brief recap
- "Does this capture everything important? Is there anything that changed your thinking?"
- Ask if anything was missed or if priorities shifted during the conversation

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
- All six stages have been conducted with meaningful user engagement
- User has provided sufficient detail in vision, requirements, constraints, priorities,
  technology, architecture direction, and scope boundaries
- Key questions have been answered and understanding has been validated
- User expresses satisfaction that their needs have been captured
- No critical information gaps remain that would prevent strategic plan creation

### Completion Checklist
- [ ] Vision and desired outcomes clearly articulated
- [ ] Key requirements and constraints identified
- [ ] Priorities and trade-offs discussed
- [ ] Success criteria defined
- [ ] Technology stack discussed, searched, and decisions captured with rationale
- [ ] Rejected technologies recorded with specific reasons
- [ ] Deployment target explicitly recorded
- [ ] Architecture direction established (components, integrations, data flow)
- [ ] Anti-requirements documented (what system must NOT do)
- [ ] Performance/scale targets defined (or sensible defaults accepted)
- [ ] Technical risks identified with mitigations
- [ ] User confirms understanding is accurate

## Context Structure and Handoff Protocol

### Final Step
After completing all conversation stages and meeting completion criteria, structure all
gathered information in the `CONVERSATION_CONTEXT` variable using this markdown format:

```markdown
{indent(conversation_context_template, '    ')}
```

### Handoff Protocol
Once `CONVERSATION_CONTEXT` is populated:

**If called from /respec-plan**: The calling command will automatically proceed with strategic
plan generation using this structured context.

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
If conversation cannot be completed due to persistent issues, populate `CONVERSATION_CONTEXT`
with available information and include detailed notes in `conversation_summary` about
the challenges encountered.
"""
