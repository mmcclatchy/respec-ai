"""Test-only helper: extract the ```markdown fenced example under a reviewer template's
"## REVIEWER FEEDBACK MARKDOWN FORMAT" section, dedented as a real reviewer would author it
(the fence is indented in the template source purely for readability inside the surrounding
prose). No production code imports this module.
"""

import textwrap

_SECTION_HEADING = '## REVIEWER FEEDBACK MARKDOWN FORMAT'


def extract_reviewer_feedback_markdown_example(template: str) -> str:
    section_start = template.index(_SECTION_HEADING)
    fence_start = template.index('```markdown', section_start) + len('```markdown')

    # The example can itself contain a nested fenced block (coding_standards_reviewer.py's
    # Before/After ```text``` snippet), so the first ``` after the opener is not necessarily
    # the real close -- track fence depth instead. A fence line with a language tag right
    # after the backticks (` ```text`) opens a nested fence; a bare ` ``` ` closes one.
    depth = 1
    search_from = fence_start
    while depth > 0:
        next_fence = template.index('```', search_from)
        line_end = template.index('\n', next_fence)
        is_bare_close = template[next_fence + 3 : line_end].strip() == ''
        depth += -1 if is_bare_close else 1
        search_from = line_end
    fence_end = next_fence

    return textwrap.dedent(template[fence_start:fence_end]).strip('\n')
