from src.models.conversation_context import ConversationContext


class TestConversationContextBuildMarkdown:
    def test_build_markdown_includes_technology_context(self) -> None:
        ctx = ConversationContext(
            problem_statement='Build a PDF generation service',
            desired_outcome='Fast serverless PDF generation',
            success_metrics='< 3s generation time',
            business_drivers='Customer demand',
            stakeholder_needs='Engineers need simple API',
            organizational_constraints='DigitalOcean Functions only',
            technology_context='Python 3.13, fpdf2 (not WeasyPrint — requires libpango incompatible with DO Functions)',
        )

        markdown = ctx.build_markdown()

        assert '## Technology Context' in markdown
        assert '### Preferred Stack' in markdown
        assert 'fpdf2' in markdown
        assert 'WeasyPrint' in markdown

    def test_build_markdown_default_technology_context(self) -> None:
        ctx = ConversationContext(
            problem_statement='Build something',
            desired_outcome='Working software',
            success_metrics='Ships on time',
            business_drivers='Business need',
            stakeholder_needs='Stakeholder requirements',
            organizational_constraints='None',
        )

        markdown = ctx.build_markdown()

        assert '## Technology Context' in markdown
        assert '[Technology preferences and decisions from discussion]' in markdown

    def test_build_markdown_technology_context_appears_before_conversation_summary(self) -> None:
        ctx = ConversationContext(
            problem_statement='Build something',
            desired_outcome='Working software',
            success_metrics='Ships on time',
            business_drivers='Business need',
            stakeholder_needs='Stakeholder requirements',
            organizational_constraints='None',
            technology_context='Python, FastAPI',
        )

        markdown = ctx.build_markdown()

        tech_pos = markdown.index('## Technology Context')
        summary_pos = markdown.index('## Conversation Summary')
        assert tech_pos < summary_pos

    def test_build_markdown_total_stages_default_is_four(self) -> None:
        ctx = ConversationContext(
            problem_statement='Build something',
            desired_outcome='Working software',
            success_metrics='Ships on time',
            business_drivers='Business need',
            stakeholder_needs='Stakeholder requirements',
            organizational_constraints='None',
        )

        markdown = ctx.build_markdown()

        assert '**Total Stages Completed**: 4' in markdown
