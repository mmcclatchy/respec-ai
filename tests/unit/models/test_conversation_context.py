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

    def test_build_markdown_total_stages_default_is_six(self) -> None:
        ctx = ConversationContext(
            problem_statement='Build something',
            desired_outcome='Working software',
            success_metrics='Ships on time',
            business_drivers='Business need',
            stakeholder_needs='Stakeholder requirements',
            organizational_constraints='None',
        )

        markdown = ctx.build_markdown()

        assert '**Total Stages Completed**: 6' in markdown

    def test_build_markdown_includes_technology_decisions(self) -> None:
        ctx = ConversationContext(
            problem_statement='Build an API',
            desired_outcome='Fast REST API',
            success_metrics='< 100ms latency',
            business_drivers='Performance needs',
            stakeholder_needs='Developer experience',
            organizational_constraints='Python only',
            technology_decisions=['FastAPI chosen for async support and auto-generated OpenAPI docs'],
            technology_rejections=['Flask rejected — no async support, manual OpenAPI required'],
        )

        markdown = ctx.build_markdown()

        assert '### Technology Decisions' in markdown
        assert 'FastAPI chosen for async support' in markdown
        assert '### Rejected Technologies' in markdown
        assert 'Flask rejected' in markdown

    def test_build_markdown_includes_architecture_direction(self) -> None:
        ctx = ConversationContext(
            problem_statement='Build a data pipeline',
            desired_outcome='Reliable ETL pipeline',
            success_metrics='< 5min processing time',
            business_drivers='Data freshness',
            stakeholder_needs='Analysts need up-to-date data',
            organizational_constraints='AWS only',
            architecture_direction='Lambda functions for ingestion, S3 for staging, Redshift for warehouse',
        )

        markdown = ctx.build_markdown()

        assert '## Architecture Direction' in markdown
        assert 'Lambda functions for ingestion' in markdown

    def test_build_markdown_architecture_direction_appears_before_conversation_summary(self) -> None:
        ctx = ConversationContext(
            problem_statement='Build something',
            desired_outcome='Working software',
            success_metrics='Ships on time',
            business_drivers='Business need',
            stakeholder_needs='Stakeholder requirements',
            organizational_constraints='None',
            architecture_direction='Microservices with API gateway',
        )

        markdown = ctx.build_markdown()

        arch_pos = markdown.index('## Architecture Direction')
        summary_pos = markdown.index('## Conversation Summary')
        assert arch_pos < summary_pos

    def test_build_markdown_includes_scope_boundaries(self) -> None:
        ctx = ConversationContext(
            problem_statement='Build a CMS',
            desired_outcome='Simple content management',
            success_metrics='5 minute content publishing',
            business_drivers='Marketing agility',
            stakeholder_needs='Non-technical editors',
            organizational_constraints='Budget constrained',
            anti_requirements=['No real-time collaboration', 'No versioning system'],
            performance_targets=['Page load < 2s', '99.9% uptime'],
        )

        markdown = ctx.build_markdown()

        assert '## Scope Boundaries' in markdown
        assert '### Anti-Requirements' in markdown
        assert 'No real-time collaboration' in markdown
        assert '### Performance Targets' in markdown
        assert 'Page load < 2s' in markdown

    def test_build_markdown_includes_risk_assessment(self) -> None:
        ctx = ConversationContext(
            problem_statement='Build a payment service',
            desired_outcome='Secure payment processing',
            success_metrics='PCI compliance',
            business_drivers='Revenue',
            stakeholder_needs='Merchant needs',
            organizational_constraints='PCI scope',
            risk_assessment=['PCI compliance complexity — High severity, requires security audit before launch'],
        )

        markdown = ctx.build_markdown()

        assert '## Risk Assessment' in markdown
        assert 'PCI compliance complexity' in markdown

    def test_build_markdown_includes_quality_bar(self) -> None:
        ctx = ConversationContext(
            problem_statement='Build an auth service',
            desired_outcome='Secure authentication',
            success_metrics='Zero breaches',
            business_drivers='Security compliance',
            stakeholder_needs='Enterprise customers',
            organizational_constraints='SOC 2 required',
            quality_bar='90% unit test coverage, OWASP Top 10 compliance, WCAG 2.1 AA',
        )

        markdown = ctx.build_markdown()

        assert '## Quality Bar' in markdown
        assert '90% unit test coverage' in markdown
