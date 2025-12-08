# respec-ai Workflows Guide

> **⚠️ Workflow Status:** Currently functional: `/respec-plan`, `/respec-roadmap`, `/respec-spec`. The `/respec-build` workflow is not yet functional.

---

## Table of Contents

**Part 1: User-Facing**
- [Overview](#overview)
- [Development Pipeline](#development-pipeline)
- [Workflows](#workflows)
  - [/respec-plan](#respec-plan)
  - [/respec-roadmap](#respec-roadmap)
  - [/respec-spec](#respec-spec)
  - [/respec-build](#respec-build-not-yet-functional)
- [Workflow Patterns](#workflow-patterns)
- [Best Practices](#best-practices)

**Part 2: Technical Details**
- [Quality & Refinement Loops](#quality--refinement-loops)
- [Critic Agents](#critic-agents)
- [Quality Thresholds](#quality-thresholds)
- [MCP Tools & Architecture](#mcp-tools--architecture)

---

## Part 1: User-Facing

### Overview

respec-ai provides a complete development pipeline that adds systematic critical evaluation to LLM-generated content. Instead of manually iterating with LLMs to check alignment and provide feedback, respec-ai automates the refinement process through:

1. **Clear separation of responsibilities** - Each workflow has a definitive purpose (Plan, Roadmap, Spec, Build)
2. **Automated critic refinement loops** - Quality gates at each stage validate against parent document targets
3. **Quality thresholds (0-100)** - Concrete, measurable quality scores determine when to proceed
4. **Hierarchical validation** - Each level validates against its parent to prevent alignment drift

**The Problem This Solves:**
- Writing specs helps keep LLMs on track, but maintaining them during development becomes more time-consuming than generating code
- Overlapping responsibilities across documents create sync hell
- Manual evaluation against parent targets is frustrating and feels cyclical
- Developers spend more time iterating with LLMs than actually building

**The Solution:**
You determine the target → LLMs generate content → Automated critics evaluate against parent specifications → System iterates until quality thresholds are met → Manual evaluation burden removed

---

### Development Pipeline

respec-ai follows a standard enterprise workflow with automated quality gates at each stage:

```text
┌─────────────────────────────────────────────────────────────────┐
│                    Development Pipeline                         │
└─────────────────────────────────────────────────────────────────┘

1. Strategic Planning (/respec-plan)
   │
   ├─ Conversational requirements gathering
   ├─ Business objectives extraction
   └─ Quality validation with plan-critic

   ▼ Validates: Strategic alignment

2. Phase Breakdown (/respec-roadmap)
   │
   ├─ Multi-phase implementation roadmap
   ├─ Initial specs for each phase
   └─ Refinement with roadmap-critic (validates against plan)

   ▼ Validates: Roadmap aligns with strategic plan

3. Technical Design (/respec-spec)
   │
   ├─ Detailed technical specifications
   ├─ Architecture and technology decisions
   └─ Quality loops with spec-critic (validates against roadmap)

   ▼ Validates: Spec aligns with roadmap phase

4. Implementation (/respec-build) [NOT YET FUNCTIONAL]
   │
   ├─ Implementation planning
   ├─ TDD-driven code generation
   └─ Code review with build-reviewer (validates against spec)

   ▼ Validates: Code aligns with spec
```

**Key Principle:** Each stage validates against its parent document target, creating a chain of alignment from business objectives through to production code.

---

### Workflows

#### `/respec-plan`

**What it does:** Create strategic project plans through interactive discovery

**When to use:**
- Starting a new project or feature
- Need to understand business objectives
- Want structured strategic planning
- Requirements are unclear and need discovery

**How it works:**
1. **Conversational discovery** - Interactive Q&A to gather requirements
2. **Plan creation** - Generates strategic plan from conversation context
3. **Quality validation** - plan-critic evaluates and provides score for your review
4. **Business objectives extraction** - plan-analyst extracts structured objectives
5. **Validation** - analyst-critic validates extraction through automated refinement loop

**Example walkthrough:**

```text
User: /respec-plan my-auth-system

Claude: I'll help you create a strategic plan. Let me start by understanding your goals.

What problem are you trying to solve with this authentication system?

User: I need users to securely log in and access protected resources

Claude: Great! Let's explore this further. What types of users will use this system?
[Conversation continues with guided discovery...]

[After conversation]
Claude: Based on our discussion, I've created a strategic plan with these key objectives:
- Secure user authentication with JWT tokens
- Role-based access control
- Password reset functionality
- Session management

Quality Score: 85/100 (Excellent)

Would you like me to proceed with extracting business objectives?
```

**Tips:**
- Be specific about your goals and constraints during the conversation
- Provide context about users, technical requirements, and business needs
- Review the quality score before approving - if it's low (<80), consider refining
- The plan serves as the foundation for all subsequent workflows

---

#### `/respec-roadmap`

**What it does:** Generate multi-phase implementation roadmaps from strategic plans

**When to use:**
- Starting large, complex projects
- Need phase-based planning
- Want to break work into manageable chunks
- Clear strategic plan exists

**How it works:**
1. **Scope analysis** - Analyzes project complexity from your strategic plan
2. **Phase creation** - Creates logical phases with clear deliverables
3. **Quality evaluation** - roadmap-critic validates against plan
4. **Initial specs** - Generates starter specifications for each phase
5. **Refinement** - Iterates until quality threshold met or user approves

**Example walkthrough:**

```text
User: /respec-roadmap my-saas-platform

Claude: I'll create a multi-phase implementation roadmap based on your strategic plan.

[Analyzing project scope...]

I've created a 4-phase roadmap:

Phase 1: User Authentication & Authorization (2-3 weeks)
- JWT token-based authentication
- Role-based access control
- Password reset flow

Phase 2: Core Features (4-6 weeks)
- Dashboard and analytics
- User profile management
- Settings and preferences

Phase 3: Payment Integration (2-3 weeks)
- Stripe integration
- Subscription management
- Billing history

Phase 4: Advanced Features (3-4 weeks)
- Team collaboration
- Advanced reporting
- API access

Quality Score: 88/100 (Excellent)

I've also created initial specifications for each phase.
Would you like me to refine any phase?
```

**Tips:**
- Ensure your strategic plan is complete before generating a roadmap
- Phases should have clear deliverables and dependencies
- Consider technical dependencies when reviewing phase order
- Use roadmaps for projects with >4 weeks of implementation time

---

#### `/respec-spec`

**What it does:** Convert strategic plans into detailed technical specifications

**When to use:**
- After completing strategic planning (or roadmap for large projects)
- Need detailed technical specifications
- Ready to break down implementation approach
- Want architecture and technology decisions documented

**How it works:**
1. **Plan retrieval** - Retrieves existing strategic plan or roadmap phase
2. **Spec generation** - spec-architect creates technical specification
3. **Quality evaluation** - spec-critic validates against parent document (plan or roadmap)
4. **Platform creation** - Creates spec in your platform (Linear issue, GitHub issue, or Markdown file)
5. **Refinement** - Iterates until quality threshold met

**Example walkthrough:**

```text
User: /respec-spec phase-1-auth

Claude: I'll create a technical specification from your strategic plan.

[Retrieving plan: my-saas-platform...]
[Generating technical specification...]

Technical Specification: Phase 1 - User Authentication

Architecture:
- FastAPI backend with JWT token generation
- PostgreSQL for user storage
- bcrypt for password hashing
- Redis for session management

Implementation Approach:
1. User registration endpoint with validation
2. Login endpoint with JWT generation
3. Password reset flow with email tokens
4. Role-based middleware for route protection

Security Considerations:
- HTTPS only in production
- Rate limiting on auth endpoints
- Password complexity requirements
- Token expiration and refresh strategy

Quality Score: 92/100 (Excellent)

Creating Linear issue...
✓ Created: AUTH-123 "Phase 1: User Authentication"
```

**Tips:**
- Specs should include architecture, technology choices, and implementation approach
- Review security considerations carefully for auth-related features
- Quality scores >90 indicate well-defined specs
- Specs created in your platform (Linear/GitHub/Markdown) serve as single source of truth

---

#### `/respec-build` [NOT YET FUNCTIONAL]

**Status:** ⚠️ Under active development

**What it will do:** Implement specifications with automated code generation

**Planned workflow:**
1. **Spec retrieval** - Retrieves technical specification
2. **Build planning** - build-planner creates implementation plan
3. **Plan evaluation** - build-critic validates plan quality
4. **Code generation** - build-coder generates code with TDD approach
5. **Code review** - build-reviewer validates against spec
6. **Refinement** - Quality loops until tests pass and code meets standards

**When to use (future):**
- After completing technical specifications
- Ready to implement features
- Want automated code generation with quality checks
- Need TDD-driven implementation

**Planned capabilities:**
- Automated test generation
- Code generation following spec architecture
- Quality validation against spec requirements
- TDD workflow (tests first, then implementation)

---

### Workflow Patterns

#### Pattern 1: Solo Developer (Markdown Platform)

**Use case:** Individual developer working on personal or small projects

**Setup:**
```bash
respec-ai init -p markdown
```

**Workflow:**
1. `/respec-plan my-project` - Create strategic plan
2. `/respec-spec feature-name` - Create technical specs
3. Implement features manually using specs as guide

**Benefits:**
- Local files, Git-friendly
- No external platform dependencies
- Fast iteration

---

#### Pattern 2: Team Collaboration (Linear Platform)

**Use case:** Team using Linear for project management

**Setup:**
```bash
respec-ai init -p linear
```

**Workflow:**
1. `/respec-plan team-project` - Create strategic plan
2. `/respec-roadmap team-project` - Create phased roadmap
3. `/respec-spec phase-1-feature` - Create specs as Linear issues
4. Team implements features tracked in Linear

**Benefits:**
- Real-time collaboration
- Issue tracking with Linear
- Comments and feedback loops
- Sprint planning with cycles

---

#### Pattern 3: Open Source (GitHub Platform)

**Use case:** Open source project with public collaboration

**Setup:**
```bash
respec-ai init -p github
```

**Workflow:**
1. `/respec-plan oss-project` - Create strategic plan
2. `/respec-spec feature-request` - Create specs as GitHub issues
3. Contributors implement features from issue specs

**Benefits:**
- Public issue tracking
- GitHub project boards
- Milestone tracking
- Community visibility

---

### Best Practices

#### Strategic Planning

**DO:**
- ✅ Be thorough during conversational discovery
- ✅ Provide context about users, constraints, and business goals
- ✅ Review quality scores and refine if needed
- ✅ Extract business objectives for alignment tracking

**DON'T:**
- ❌ Rush through the conversation - quality here impacts everything
- ❌ Skip business objective extraction
- ❌ Approve plans with quality scores <70

---

#### Roadmap Creation

**DO:**
- ✅ Break large projects into logical phases
- ✅ Ensure phases have clear deliverables
- ✅ Consider technical dependencies when ordering phases
- ✅ Review initial specs generated for each phase

**DON'T:**
- ❌ Create too many small phases (>6 phases often indicates over-planning)
- ❌ Mix unrelated features in single phase
- ❌ Ignore dependency order

---

#### Technical Specifications

**DO:**
- ✅ Include architecture, technology choices, and implementation approach
- ✅ Document security considerations for sensitive features
- ✅ Specify testing requirements
- ✅ Review quality scores (>85 is ideal)

**DON'T:**
- ❌ Skip architecture decisions
- ❌ Leave implementation approach vague
- ❌ Forget security considerations for auth/payment features

---

#### Working with Quality Scores

**Understanding scores:**
- **90-100:** Excellent - proceed with confidence
- **80-89:** Good - minor refinements may help
- **70-79:** Acceptable - review for gaps
- **<70:** Needs work - iterate or provide feedback

**When scores are low:**
1. Review the critic feedback for specific issues
2. Provide additional context or clarification
3. Let the refinement loop iterate
4. If stagnating, provide user feedback to guide improvement

---

#### Platform-Specific Tips

**Markdown:**
- Commit specs to version control regularly
- Use meaningful spec names (they become filenames)
- Review generated files in `.respec-ai/projects/[name]/`

**Linear:**
- Use descriptive issue titles
- Leverage Linear labels for categorization
- Link related issues for dependencies
- Use cycles for sprint planning

**GitHub:**
- Create milestones for roadmap phases
- Use project boards to track progress
- Label issues with priorities
- Link issues to pull requests

---

## Part 2: Technical Details

### Quality & Refinement Loops

respec-ai uses two types of quality loops to ensure high-quality outputs:

#### 1. Human-in-the-Loop with Quality Validation

**Used by:** `/respec-plan`

**Process:**
1. **Conversation:** Interactive Q&A to gather requirements
2. **Generation:** Creates strategic plan from conversation context
3. **Quality Check:** plan-critic evaluates and provides score
4. **Human Review:** User sees quality score and decides next action
5. **Analysis:** plan-analyst extracts structured business objectives
6. **Validation:** analyst-critic validates through automated refinement loop
7. **Completion:** Final validated strategic plan

**This is a hybrid approach** - conversational gathering with automated quality validation and user decision points.

#### 2. Automated Refinement Loops (MCP-Driven)

**Used by:** `/respec-roadmap`, `/respec-spec`, `/respec-build`

**Process:**
1. **Generation:** Generative agent creates content (roadmap, spec, build plan, code)
2. **Evaluation:** Critic agent scores quality (0-100)
3. **Decision:** MCP server determines next action:
   - **High score (>threshold)** → Proceed to next phase
   - **Improving score** → Refine with feedback
   - **Stagnation** → Request user input

**Loop components:**
- **Generative agent** - Creates content based on parent document and requirements
- **Critic agent** - Evaluates quality against parent document targets
- **MCP server** - Orchestrates loop, tracks iterations, decides progression
- **Quality threshold** - Configurable score (default: 80-95 depending on workflow)

**Stagnation detection:**
- No improvement over successive iterations
- Max iterations reached (configurable)
- System requests user input for guidance

---

### Critic Agents

#### For Human-in-the-Loop

**plan-critic:**
- Evaluates strategic plans after conversational gathering
- Provides quality score for user decision-making
- No automated refinement loop - user decides next action
- Checks: Strategic clarity, business objectives, implementation feasibility

**analyst-critic:**
- Validates business objective extraction
- Uses MCP-driven automated refinement loop
- Ensures completeness and accuracy of analysis
- Checks: Objective completeness, clarity, alignment with plan

#### For Automated Loops

**roadmap-critic:**
- Evaluates implementation roadmaps
- Checks phase breakdown and sizing
- Validates dependencies and ordering
- Ensures roadmap aligns with strategic plan
- Validates: Phase logic, dependencies, deliverables, timeline

**spec-critic:**
- Evaluates technical specifications
- Checks architecture design decisions
- Validates implementation approach
- Ensures spec aligns with roadmap phase or plan
- Validates: Architecture, technology choices, security, implementation detail

**build-critic:**
- Evaluates build plans
- Checks implementation steps
- Validates technology choices
- Ensures plan aligns with technical spec
- Validates: Implementation approach, testing strategy, code structure

**build-reviewer:**
- Reviews generated code
- Checks code quality and best practices
- Validates implementation correctness
- Ensures code aligns with build plan and spec
- Validates: Code quality, test coverage, spec adherence

---

### Quality Thresholds

Quality scores determine progression through the pipeline:

#### Score Ranges

- **90-100:** Excellent quality - proceed immediately
- **80-89:** Good quality - minor refinements acceptable
- **70-79:** Acceptable - may need iteration
- **60-69:** Needs improvement - refinement required
- **<60:** Significant issues - major refinement needed

#### Threshold Configuration

Different workflows have different thresholds:

| Workflow | Default Threshold | Improvement Required |
|----------|------------------|---------------------|
| `/respec-plan` | 90 | 5 points |
| `/respec-roadmap` | 90 | 10 points |
| `/respec-spec` | 90 | 5 points |
| `/respec-build` | 95 | 5 points |

**Threshold:** Minimum score to proceed to next phase
**Improvement Required:** Points that must improve between iterations to avoid stagnation

#### Stagnation Detection

System requests user input when:
- Score improvement is less than threshold over 2 consecutive iterations
- Maximum iterations reached (default: 5 for plan, 3-5 for others)
- Quality score below 60 after multiple attempts

**User input options when stagnated:**
- Provide additional context or requirements
- Adjust expectations or constraints
- Accept current quality and proceed
- Abandon and restart

---

### MCP Tools & Architecture

#### MCP Server Role

The respec-ai MCP server provides 38 tools across 7 modules that power the workflow system:

**Loop Management (8 tools):**
- Initialize, track, and manage refinement cycles
- Determine progression decisions
- Store loop state and history

**Feedback Systems (5 tools):**
- Store and retrieve critic feedback
- Track improvement trends
- Support stagnation detection

**Document Management (21 tools):**
- Project plans (5 tools)
- Roadmaps (2 tools)
- Technical specs (9 tools)
- Build plans (4 tools)
- Completion reports (6 tools)

**State Management:**
- Tracks loop iterations and scores
- Maintains refinement history
- Orchestrates agent invocations
- Determines when to proceed vs. iterate vs. request user input

#### Agent Architecture

**Generative Agents:**
- `plan-analyst` - Extracts business objectives from strategic plans
- `roadmap` - Generates multi-phase roadmaps from plans
- `spec-architect` - Creates technical specifications from plans/roadmaps
- `build-planner` - Creates implementation plans from specs
- `build-coder` - Generates code from build plans

**Critic Agents:**
- `plan-critic` - Validates strategic plans
- `analyst-critic` - Validates objective extraction
- `roadmap-critic` - Validates roadmaps against plans
- `spec-critic` - Validates specs against roadmaps/plans
- `build-critic` - Validates build plans against specs
- `build-reviewer` - Validates code against build plans/specs

**Command Templates:**
Each `/respec-*` command is a template that orchestrates:
1. Generative agent(s) for content creation
2. Critic agent(s) for quality validation
3. MCP tools for state management and progression
4. Platform-specific tools (Linear/GitHub/Markdown) for storage

#### Platform Integration

**Platform Abstraction:**
The system uses platform-agnostic operations that map to platform-specific tools:

```text
Abstract Operation → Platform-Specific Tool
------------------------------------------
create_spec → Linear: create_issue | GitHub: create_issue | Markdown: Write
get_spec → Linear: get_issue | GitHub: get_issue | Markdown: Read
update_spec → Linear: update_issue | GitHub: update_issue | Markdown: Edit
```

**Benefits:**
- Single workflow logic works across all platforms
- Switch platforms without changing commands
- Platform capabilities abstracted into unified operations

---

### How Everything Connects

```text
┌──────────────────────────────────────────────────────────────┐
│                    User Invokes Command                      │
│                    (e.g., /respec-spec)                      │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                  Command Template                            │
│  • Determines parent document (plan or roadmap phase)        │
│  • Initializes refinement loop via MCP                       │
│  • Invokes generative agent                                  │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│               Generative Agent (e.g., spec-architect)        │
│  • Retrieves parent document via MCP tools                   │
│  • Generates technical specification                         │
│  • Returns content to command                                │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                Critic Agent (e.g., spec-critic)              │
│  • Evaluates content against parent document target          │
│  • Provides quality score (0-100)                            │
│  • Provides specific feedback for improvement                │
│  • Stores feedback via MCP tools                             │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    MCP Server Decision                       │
│  • Checks score against threshold                            │
│  • Checks improvement trend                                  │
│  • Decides: Proceed | Iterate | Request User Input           │
└────────────────────────┬─────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
    Proceed         Iterate    Request User Input
         │               │               │
         │               └───────┐       │
         │                       │       │
         ▼                       ▼       ▼
┌─────────────────┐  ┌──────────────────────────────┐
│ Store in        │  │ Return to Generative Agent   │
│ Platform        │  │ with Feedback                │
│ (Linear/GitHub/ │  │                              │
│  Markdown)      │  │ Loop continues until         │
│                 │  │ threshold met or stagnation  │
└─────────────────┘  └──────────────────────────────┘
```

**Key insight:** The MCP server orchestrates the entire refinement loop, removing the manual burden of evaluating content, providing feedback, and deciding when quality is sufficient. You set the target, the system handles the refinement.

---

## Further Reading

- **[CLI Guide](CLI_GUIDE.md)** - Installation, setup, and CLI reference
- **[Architecture Guide](ARCHITECTURE.md)** - System design and implementation details
- **[README](../README.md)** - Project overview and quick start
