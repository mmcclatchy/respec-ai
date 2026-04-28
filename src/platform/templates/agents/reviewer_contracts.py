def render_reviewer_mcp_retry_contract() -> str:
    return """═══════════════════════════════════════════════
MANDATORY MCP RETRY CONTRACT
═══════════════════════════════════════════════
Apply this retry policy to MCP tool calls only:
- get_document
- get_feedback
- store_reviewer_result

If an MCP tool call fails with handshake timeout, startup timeout, server unavailable, or transient transport error:
- Retry the same MCP tool call once.
- Preserve the original parameters exactly.
- Record the retry attempt in `Reviewer Execution Report (Non-Actionable)`.

Do NOT retry deterministic MCP validation errors, missing loop/document errors, project test failures, lint/type failures, coverage failures, or file-read failures.

If the retry fails:
- Stop MCP-dependent persistence work.
- Return the failure output from the mandatory output contract.
- Include the exact MCP operation and error in `execution_notes`.
═══════════════════════════════════════════════"""


def render_reviewer_output_contract(reviewer_name: str, store_reviewer_result_call: str) -> str:
    return f"""═══════════════════════════════════════════════
MANDATORY OUTPUT SCOPE
═══════════════════════════════════════════════
Store reviewer result via {store_reviewer_result_call}.

On successful reviewer-result storage, your ONLY output to the orchestrator is:
  "Reviewer result stored: {reviewer_name} (score=[REVIEW_SCORE], iteration=[review_iteration])"
  "run_status=clean|warnings"
  "stored_result=yes"
  "execution_notes=[none, or concise non-actionable tool/read/command limitation]"

On failed reviewer-result storage after the mandatory MCP retry, your ONLY output to the orchestrator is:
  "Reviewer result NOT stored: {reviewer_name} (iteration=[review_iteration])"
  "run_status=incomplete"
  "stored_result=no"
  "execution_notes=[exact MCP operation and error, or concise non-actionable tool/read/command limitation]"

Do NOT output "Reviewer result stored" when `stored_result=no`.
Do NOT return review markdown to the orchestrator.
Do NOT write files to disk.

VIOLATION: Returning full reviewer feedback markdown to the orchestrator
           instead of storing via MCP tool.
VIOLATION: Reporting "Reviewer result stored" with `stored_result=no`.
═══════════════════════════════════════════════"""


def render_reviewer_execution_report_contract() -> str:
    return """## REVIEWER EXECUTION REPORT CONTRACT (NON-ACTIONABLE)

Include this section in `REVIEW_SECTION_MARKDOWN` before successful `store_reviewer_result` persistence:

```markdown
#### Reviewer Execution Report (Non-Actionable)
- Run Status: [clean/warnings]
- Stored Result: [yes]
- MCP Retry Attempts: [none / operation retried once with result]
- Tool/Command/Read Limitations: [none / concise limitations]
- Fallbacks Used: [none / concise fallback]
- Challenges: [none / concise execution challenge]
- Orchestrator Action Needed: [none/rerun/fail-closed]
```

This section is for workflow visibility and audit history only.
Do NOT copy execution-report-only problems into `Key Issues`, `Recommendations`, `blockers`, or `findings`.
Only record a problem in `Key Issues`, `Recommendations`, `blockers`, or `findings` when the same evidence is a real implementation defect.

If `store_reviewer_result` fails after retry, this section is not stored in MCP. Put the exact storage failure in final `execution_notes` instead."""
