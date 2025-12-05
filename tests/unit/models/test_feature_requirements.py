import pytest
from src.models.enums import RequirementsStatus
from src.models.feature_requirements import FeatureRequirements


class TestFeatureRequirementsParsing:
    def test_parse_markdown_extracts_all_fields(self) -> None:
        markdown = """# Feature Requirements: User Authentication System

## Overview

### Feature Description
Secure user authentication with multi-factor support

### Problem Statement
Users need secure access to the platform with protection against unauthorized access

### Target Users
All platform users including administrators and end-users

### Business Value
Increased security compliance and user trust leading to higher retention

## Requirements

### User Stories
As a user, I want to log in securely so that my account is protected from unauthorized access

### Acceptance Criteria
User can login with email/password, MFA is required for admin accounts, password reset functionality works

### User Experience Goals
Simple login process, clear error messages, quick authentication under 2 seconds

## Technical Specifications

### Functional Requirements
JWT token-based authentication, password hashing with bcrypt, session management

### Non-Functional Requirements
99.9% uptime, sub-1s login response time, support for 10,000 concurrent users

### Integration Requirements
OAuth providers (Google, GitHub), LDAP integration, audit logging system

## Metrics

### User Metrics
User login success rate >95%, password reset completion rate >90%

### Performance Metrics
Average login time <1s, token refresh time <200ms, system availability >99.9%

### Technical Metrics
Failed authentication attempts <5%, security incidents = 0, API response time <500ms

## Feature Prioritization

### Must Have
Email/password login, secure session management, password reset via email

### Should Have
Two-factor authentication, OAuth integration, remember me functionality

### Could Have
Biometric authentication, single sign-on, social media integration

### Won't Have
SMS-based authentication (privacy concerns), password sharing features

## Metadata

### Status
approved

"""

        requirements = FeatureRequirements.parse_markdown(markdown)

        assert requirements.project_name == 'User Authentication System'
        assert requirements.feature_description == 'Secure user authentication with multi-factor support'
        assert (
            requirements.problem_statement
            == 'Users need secure access to the platform with protection against unauthorized access'
        )
        assert requirements.target_users == 'All platform users including administrators and end-users'
        assert requirements.business_value == 'Increased security compliance and user trust leading to higher retention'
        assert 'As a user, I want to log in securely' in requirements.user_stories
        assert 'User can login with email/password' in requirements.acceptance_criteria
        assert 'Simple login process' in requirements.user_experience_goals
        assert 'JWT token-based authentication' in requirements.functional_requirements
        assert '99.9% uptime' in requirements.non_functional_requirements
        assert 'OAuth providers' in requirements.integration_requirements
        assert 'User login success rate >95%' in requirements.user_metrics
        assert 'Average login time <1s' in requirements.performance_metrics
        assert 'Failed authentication attempts <5%' in requirements.technical_metrics
        assert 'Email/password login' in requirements.must_have_features
        assert 'Two-factor authentication' in requirements.should_have_features
        assert 'Biometric authentication' in requirements.could_have_features
        assert 'SMS-based authentication' in requirements.wont_have_features
        assert requirements.requirements_status == RequirementsStatus.APPROVED

    def test_parse_markdown_handles_missing_sections(self) -> None:
        markdown = """# Feature Requirements: Basic Feature

## Overview

### Feature Description
Simple feature implementation

### Problem Statement
Need basic functionality

### Target Users
End users

### Business Value
Improved user experience

## Metadata

### Status
draft

"""

        requirements = FeatureRequirements.parse_markdown(markdown)

        assert requirements.project_name == 'Basic Feature'
        assert requirements.feature_description == 'Simple feature implementation'
        # Missing sections should have default values
        assert 'User Stories not specified' in requirements.user_stories
        assert 'Acceptance Criteria not specified' in requirements.acceptance_criteria
        assert 'Must Have Features not specified' in requirements.must_have_features

    def test_parse_markdown_invalid_format_raises_error(self) -> None:
        invalid_markdown = """This is not a feature requirements format"""

        with pytest.raises(ValueError, match='Invalid feature requirements format: missing title'):
            FeatureRequirements.parse_markdown(invalid_markdown)


class TestFeatureRequirementsMarkdownBuilding:
    @pytest.fixture
    def sample_requirements(self) -> FeatureRequirements:
        return FeatureRequirements(
            project_name='Shopping Cart Feature',
            feature_description='Add items to cart for later purchase',
            problem_statement='Users need to collect items before checkout',
            target_users='All e-commerce customers',
            business_value='Increased conversion rates and order values',
            user_stories='As a customer, I want to add items to my cart so I can purchase multiple items at once',
            acceptance_criteria='User can add/remove items, view cart total, proceed to checkout',
            user_experience_goals='Intuitive cart management, clear pricing, quick add/remove actions',
            functional_requirements='Cart persistence, item quantity management, price calculation',
            non_functional_requirements='Cart loads in <500ms, supports 100 items per cart',
            integration_requirements='Payment gateway integration, inventory system sync',
            user_metrics='Cart abandonment rate <30%, add-to-cart conversion >15%',
            performance_metrics='Cart operations <200ms, real-time inventory updates',
            technical_metrics='Cart API uptime >99.5%, data consistency checks pass 100%',
            must_have_features='Add items, remove items, view total price',
            should_have_features='Save for later, quantity adjustment, price breakdown',
            could_have_features='Wishlist integration, product recommendations',
            wont_have_features='Shared carts between users, complex discounting rules',
            requirements_status=RequirementsStatus.IN_REVIEW,
        )

    def test_build_markdown_creates_valid_template_format(self, sample_requirements: FeatureRequirements) -> None:
        markdown = sample_requirements.build_markdown()

        assert '# Feature Requirements: Shopping Cart Feature' in markdown
        assert '## Overview' in markdown
        assert '### Feature Description' in markdown
        assert 'Add items to cart for later purchase' in markdown
        assert '## Requirements' in markdown
        assert '### User Stories' in markdown
        assert 'As a customer, I want to add items to my cart so I can purchase multiple items at once' in markdown
        assert '## Feature Prioritization' in markdown
        assert '### Must Have' in markdown
        assert 'Add items, remove items, view total price' in markdown
        assert '### Status\nin-review' in markdown

    def test_round_trip_parsing_maintains_data_integrity(self, sample_requirements: FeatureRequirements) -> None:
        # Build markdown from the model
        markdown = sample_requirements.build_markdown()

        # Parse it back into a model
        parsed_requirements = FeatureRequirements.parse_markdown(markdown)

        # Should match original (except timestamps)
        assert parsed_requirements.project_name == sample_requirements.project_name
        assert parsed_requirements.feature_description == sample_requirements.feature_description
        assert parsed_requirements.problem_statement == sample_requirements.problem_statement
        assert parsed_requirements.target_users == sample_requirements.target_users
        assert parsed_requirements.business_value == sample_requirements.business_value
        assert parsed_requirements.user_stories == sample_requirements.user_stories
        assert parsed_requirements.acceptance_criteria == sample_requirements.acceptance_criteria
        assert parsed_requirements.user_experience_goals == sample_requirements.user_experience_goals
        assert parsed_requirements.functional_requirements == sample_requirements.functional_requirements
        assert parsed_requirements.non_functional_requirements == sample_requirements.non_functional_requirements
        assert parsed_requirements.integration_requirements == sample_requirements.integration_requirements
        assert parsed_requirements.user_metrics == sample_requirements.user_metrics
        assert parsed_requirements.performance_metrics == sample_requirements.performance_metrics
        assert parsed_requirements.technical_metrics == sample_requirements.technical_metrics
        assert parsed_requirements.must_have_features == sample_requirements.must_have_features
        assert parsed_requirements.should_have_features == sample_requirements.should_have_features
        assert parsed_requirements.could_have_features == sample_requirements.could_have_features
        assert parsed_requirements.wont_have_features == sample_requirements.wont_have_features
        assert parsed_requirements.requirements_status == sample_requirements.requirements_status

    def test_character_for_character_round_trip_validation(self, sample_requirements: FeatureRequirements) -> None:
        # Build markdown
        original_markdown = sample_requirements.build_markdown()

        # Parse and rebuild
        parsed_requirements = FeatureRequirements.parse_markdown(original_markdown)
        rebuilt_markdown = parsed_requirements.build_markdown()

        # Should be identical
        assert original_markdown == rebuilt_markdown
