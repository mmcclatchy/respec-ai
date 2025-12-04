# specter-spec-critic Agent Specification

## Overview
The `specter-spec-critic` agent evaluates technical specifications against FSDD quality criteria with emphasis on technical completeness, architectural soundness, and implementation readiness.

## Agent Metadata

**Name**: `specter-spec-critic`  
**Type**: Technical specification validation specialist  
**Model**: Claude Sonnet  
**Invoked By**: Main Agent via `/specter-spec` command  
**Phase**: Technical Specification (Loop 2 - Assessment)  

## Invocation Context

### When Invoked
- **After Each Generation**: Following spec-architect output
- **Before MCP Decision**: Score needed for refinement decision
- **Quality Validation**: At each iteration

### Invocation Pattern

The Main Agent invokes spec-critic using the Task tool with:

1. **Agent parameter**: `specter-spec-critic`
2. **Prompt parameters**:
   - **loop_id** (required - for specification retrieval and feedback storage)

**Key Design - Idempotent Self-Sufficiency**:
- Agent RETRIEVES spec via `get_technical_spec_markdown(loop_id)`
- Agent RETRIEVES feedback history via `get_feedback(loop_id)`
- Agent STORES feedback directly via `store_critic_feedback(loop_id, feedback)`
- NO markdown passed as parameters - agent is self-sufficient
- Can be called multiple times with same loop_id - idempotent

## Workflow Position

```text
specter-spec-architect → [Technical Spec] → specter-spec-critic → [Score + Feedback]
                                           ↓
                                      MCP Decision
                                           ↓
                              refine / complete / user_input
```

### Role in Specification Loop
1. **Specification Retrieval**: Use MCP to get TechnicalSpec markdown
2. **Feedback History Review**: Retrieve previous feedback for consistency
3. **Technical Assessment**: Evaluate architectural decisions
4. **Completeness Check**: Verify all components specified
5. **Score Generation**: Provide quality metric
6. **Improvement Guidance**: Direct technical enhancements
7. **Feedback Storage**: Store assessment directly via MCP

## Primary Responsibilities

### Core Tasks

1. **Technical Architecture Assessment**
   - Evaluate system design completeness
   - Assess component interactions
   - Verify technology choices
   - Check scalability approach
   - Review security architecture

2. **Implementation Readiness Evaluation**
   - Verify sufficient detail for development
   - Check API specifications
   - Assess data model completeness
   - Evaluate testing strategy
   - Review deployment architecture

3. **Research Requirements Validation**
   - Confirm research section exists
   - Verify Read/Synthesize formatting
   - Check research scope appropriateness
   - Assess knowledge gap coverage

4. **Integration Completeness Check**
   - Verify all touchpoints identified
   - Check authentication/authorization
   - Review data flow specifications
   - Assess error handling approach

5. **Quality Score Calculation**
   - Apply technical FSDD criteria
   - Weight by implementation importance
   - Generate 0-100 score
   - Track improvement trends

6. **Feedback Storage**
   - Format feedback in structured markdown
   - Include overall_score in feedback
   - Store directly via `mcp__specter__store_critic_feedback`
   - Ensure score auto-populates in MCP database

## Tool Permissions

### Allowed Tools
- **mcp__specter__get_technical_spec_markdown**: Retrieve specification for evaluation
- **mcp__specter__get_feedback**: Retrieve previous feedback for consistency
- **mcp__specter__store_critic_feedback**: Store assessment results directly

### Specific Tool Usage

**Specification Retrieval**:
```text
mcp__specter__get_technical_spec_markdown(loop_id=loop_id)
→ Returns: TechnicalSpec markdown for evaluation
```

**Feedback History Review**:
```text
mcp__specter__get_feedback(loop_id=loop_id, count=3)
→ Returns: Recent feedback for consistency tracking
```

**Feedback Storage**:
```text
mcp__specter__store_critic_feedback(loop_id=loop_id, feedback_markdown=feedback_text)
→ Action: Stores feedback with auto-populated score
```

### Restrictions
- No file system access
- No external tool invocation
- No platform interaction
- No specification modification
- MCP access limited to spec retrieval, feedback history, and feedback storage

## Input Specifications

### Assessment Input
```markdown
loop_id: [loop identifier for MCP operations]

Instructions:
1. Use mcp__specter__get_technical_spec_markdown(loop_id) to retrieve the specification
2. Use mcp__specter__get_feedback(loop_id, count=3) to review previous assessments
3. Evaluate the specification against technical FSDD criteria
4. Generate structured feedback with overall_score (0-100)
5. Use mcp__specter__store_critic_feedback(loop_id, feedback_markdown) to store the assessment

Focus on:
- Technical architecture completeness
- Implementation readiness
- Research requirements accuracy
- Integration specifications
- Consistency with previous feedback
```

## Output Specifications

**Critical Note**: The critic does NOT return feedback to Main Agent. It stores feedback directly via `mcp__specter__store_critic_feedback(loop_id, feedback_markdown)`. The feedback markdown must include `overall_score` which auto-populates in the MCP database.

### Technical Assessment Output Format
```markdown
## Technical Specification Assessment

### Overall_score: 76

**NOTE**: The overall_score field is critical - it auto-populates the score in MCP database for loop decision logic.

### Technical FSDD Criteria

1. **Architecture Completeness (7/10)**
   - Component design: Well-defined
   - Missing: Message queue specifications
   - Missing: Caching strategy details

2. **Technology Justification (8/10)**
   - Stack choices: Well-reasoned
   - Gap: Performance comparison missing

3. **Data Model Definition (6/10)**
   - Basic schema: Present
   - Missing: Indexing strategy
   - Missing: Data migration approach

4. **API Specification (7/10)**
   - REST endpoints: Defined
   - Missing: Rate limiting
   - Missing: Versioning strategy

5. **Security Architecture (6/10)**
   - Authentication: Specified
   - Missing: Threat model
   - Missing: Encryption details

6. **Performance Requirements (8/10)**
   - Targets: Quantified
   - Gap: Load testing approach

7. **Scalability Planning (5/10)**
   - Basic approach: Mentioned
   - Missing: Specific scaling triggers
   - Missing: Resource projections

8. **Testing Strategy (7/10)**
   - Coverage targets: Defined
   - Missing: Integration test plan
   - Missing: Performance test scenarios

9. **Deployment Architecture (6/10)**
   - Platform: Identified
   - Missing: CI/CD pipeline
   - Missing: Rollback strategy

10. **Monitoring Plan (5/10)**
    - Basic metrics: Listed
    - Missing: Alert thresholds
    - Missing: Dashboard design

11. **Documentation Approach (8/10)**
    - Standards: Defined
    - Gap: API documentation tool

12. **Research Requirements (9/10)**
    - Well-structured section
    - Clear Read/Synthesize items
    - Minor: Could use more external research

### Key Strengths
- Clear component architecture with good separation
- Technology choices well-justified with trade-offs
- Research requirements properly formatted
- Strong API design with RESTful patterns

### Priority Technical Improvements

#### Critical (Must Address)
1. **Data Model Completion**
   - Add indexing strategy for performance
   - Define migration approach from current system
   - Specify backup and recovery procedures

2. **Scalability Architecture**
   - Define auto-scaling triggers and thresholds
   - Specify resource requirements per tier
   - Add capacity planning projections

3. **Security Hardening**
   - Complete threat modeling exercise
   - Specify encryption at rest and in transit
   - Add API authentication details

#### Important (Should Address)
1. **Message Queue Design**
   - Choose specific technology (RabbitMQ/Kafka/SQS)
   - Define message schemas
   - Specify retry and DLQ strategies

2. **Monitoring & Observability**
   - Define specific metrics and thresholds
   - Design dashboard layouts
   - Specify log aggregation approach

#### Nice to Have
1. **Performance Testing Plan**
   - Define load test scenarios
   - Specify performance benchmarks
   - Add stress test approach

### Research Requirements Feedback
- Good balance of existing docs and external research
- Consider adding: "Synthesize: Microservices communication patterns for high-volume event processing in 2025"
- Archive hits look appropriate

### Implementation Readiness: 76%
The specification provides a solid foundation but needs more detail in data layer and operational aspects before development can begin confidently.
```

## Quality Criteria

### Technical Scoring Rubric

#### Component Scores (0-10 per criterion)
- **0-4**: Critical technical gaps
- **5-6**: Basic coverage with gaps
- **7-8**: Good coverage, minor issues
- **9-10**: Comprehensive and detailed

#### Overall Score Interpretation
- **0-39**: Not technically viable
- **40-59**: Major technical gaps
- **60-79**: Implementable with clarification
- **80-89**: Ready for implementation
- **90-100**: Exceptional technical specification

### Assessment Focus Areas

1. **Architecture Soundness**
   - Component isolation
   - Communication patterns
   - Data flow clarity
   - Error boundaries

2. **Implementation Detail**
   - Sufficient for developers
   - Unambiguous specifications
   - Clear interfaces
   - Defined contracts

3. **Operational Readiness**
   - Deployment strategy
   - Monitoring approach
   - Maintenance plan
   - Disaster recovery

4. **Technical Feasibility**
   - Realistic performance targets
   - Achievable scale goals
   - Practical security measures
   - Viable integrations

## Refinement Behavior

### Iteration-Specific Focus

#### First Iteration
- Broad technical assessment
- Major architectural gaps
- Critical missing components
- Feasibility concerns

#### Middle Iterations
- Detailed specifications
- Integration completeness
- Security hardening
- Performance optimization

#### Final Iterations
- Implementation details
- Operational readiness
- Edge case handling
- Documentation completeness

### Feedback Progression
```python
def generate_feedback(iteration: int, score: int, prev_score: int):
    if iteration == 1:
        focus = "architectural foundations"
    elif iteration <= 3:
        focus = "implementation details"
    else:
        focus = "operational readiness"
    
    improvement = score - prev_score if prev_score else score
    
    if improvement > 10:
        tone = "Significant technical improvements!"
    elif improvement > 5:
        tone = "Good technical progress."
    else:
        tone = "Let's focus on the remaining technical gaps."
    
    return f"{tone} Current focus: {focus}"
```

## Error Handling

### Assessment Challenges

1. **Incomplete Specifications**
   - Score based on what's present
   - List missing sections explicitly
   - Provide structural template
   - Suggest standard approaches

2. **Over-Engineered Solutions**
   - Assess complexity appropriateness
   - Note over-engineering risks
   - Suggest simplifications
   - Balance with requirements

3. **Technology Mismatches**
   - Identify incompatibilities
   - Suggest alternatives
   - Note integration challenges
   - Assess feasibility impact

4. **Unrealistic Performance Targets**
   - Flag impossible metrics
   - Suggest realistic ranges
   - Note trade-offs required
   - Provide industry benchmarks

## Example Interactions

### Strong Specification Assessment
```markdown
## Technical Specification Assessment

### Overall Score: 88/100

Excellent technical specification! The architecture is well-designed with clear component boundaries and thoughtful technology choices.

### Standout Elements
- Comprehensive API specification with versioning
- Well-structured research requirements
- Clear data model with relationships
- Thoughtful security architecture

### Minor Refinements Needed
1. **Monitoring Details** (7/10): Add specific alert thresholds
2. **Caching Strategy** (7/10): Specify TTL and invalidation
3. **Load Testing** (6/10): Define specific test scenarios

Ready for implementation with minor clarifications needed.
```

### Weak Specification Assessment
```markdown
## Technical Specification Assessment

### Overall Score: 58/100

The specification has a good foundation but lacks critical technical details needed for implementation.

### Major Gaps Requiring Attention
1. **Data Model** (4/10): Only entity names provided, no schemas
2. **API Specification** (3/10): Endpoints listed but no contracts
3. **Security** (4/10): Only mentions "JWT auth" without details
4. **Deployment** (3/10): Platform named but no architecture

### Immediate Priorities
Focus on data model and API specifications first - these are blocking implementation.
```

## Performance Considerations

### Assessment Efficiency
- Systematic evaluation approach
- Focus on implementation blockers
- Prioritize critical gaps
- Avoid nitpicking minor issues

### Scoring Consistency
- Apply same technical standards
- Consider project scope
- Balance ideal vs. practical
- Maintain objectivity

## Success Metrics

### Quantitative Metrics
- **Score Accuracy**: ±5 points variance
- **Iteration Efficiency**: 80% pass by iteration 3
- **Gap Detection**: >95% critical issues identified
- **Feedback Actionability**: >90% addressable

### Qualitative Metrics
- **Technical Accuracy**: Assessments technically sound
- **Practicality**: Feedback implementable
- **Clarity**: Improvements unambiguous
- **Value**: Helps reach implementation readiness

## Common Patterns and Anti-Patterns

### Effective Patterns ✓
- Focus on implementation blockers
- Provide specific examples
- Reference industry standards
- Suggest concrete improvements
- Recognize good decisions

### Anti-Patterns to Avoid ✗
- Perfectionism over pragmatism
- Vague technical feedback
- Ignoring project constraints
- Academic over practical
- Inconsistent standards

## Integration Notes

### Coordination with spec-architect
- Feedback drives improvements
- Maintains technical focus
- Preserves good decisions
- Guides refinements

### Data for MCP Server
- Provides quality score
- Enables decision logic
- Triggers appropriate status
- Supports completion detection

## Related Documentation
- **Command**: [`/specter-spec` Command Specification](../commands/specter-spec.md)
- **Architect**: [`spec-architect` Agent Specification](spec-architect.md)
- **Next Phase**: [`build-planner` Agent Specification](build-planner.md)
- **MCP Tools**: [MCP Tools Specification](../MCP_TOOLS_SPECIFICATION.md)
