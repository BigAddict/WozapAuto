# WozapAuto Test Suite

This directory contains comprehensive tests for the WozapAuto application, with a particular focus on the onboarding process which has been identified as problematic.

## Test Organization

Tests are organized by app and functionality:

### Core App Tests (`core/tests/`)
- `test_models.py` - Tests for UserProfile model and onboarding-related functionality
- `test_forms.py` - Tests for onboarding forms (PersonalProfileForm, BusinessProfileForm, OTPVerificationForm, CustomUserCreationForm)
- `test_views.py` - Tests for onboarding views and authentication
- `test_onboarding.py` - Comprehensive integration tests for the complete onboarding flow

### Business App Tests (`business/tests/`)
- `test_models.py` - Tests for business models (BusinessProfile, BusinessType, Product, Service, etc.)
- `test_forms.py` - Tests for business forms
- `test_views.py` - Tests for business views and API endpoints

### Other App Tests
- `audit/tests/test_models.py` - Tests for audit models
- `connections/tests/test_models.py` - Tests for connection models
- `aiengine/tests/test_models.py` - Tests for AI engine models
- `knowledgebase/tests/test_models.py` - Tests for knowledge base models

## Test Categories

### 1. Onboarding Model Tests
- UserProfile creation and management
- Onboarding step progression
- Business profile OTP generation and verification
- Step validation and redirect URL generation

### 2. Form Validation Tests
- Personal profile form validation
- Business profile form validation with phone number validation
- OTP verification form validation
- User creation form validation with password requirements
- Email uniqueness validation

### 3. View Tests
- Onboarding flow step-by-step testing
- Authentication views (signup, signin, signout)
- Profile management views
- Error handling and edge cases
- Redirect logic and step validation

### 4. Integration Tests
- Complete onboarding flow from signup to completion
- Error scenarios and recovery
- Step skipping prevention
- WhatsApp service integration (mocked)

### 5. Edge Case Tests
- Users without profiles
- Business profile phone number uniqueness
- OTP expiry and max attempts
- Concurrent onboarding attempts
- Inactive business types

### 6. Performance Tests
- Page load performance
- Form submission performance
- Database query optimization

## Running Tests

### Run All Tests
```bash
python manage.py test
```

### Run Specific Test Module
```bash
python manage.py test core.tests.test_onboarding
python manage.py test core.tests.test_models
python manage.py test business.tests.test_views
```

### Run Onboarding Tests Only
```bash
python run_tests.py onboarding
```

### Run All Tests
```bash
python run_tests.py all
```

### Run with Coverage
```bash
coverage run --source='.' manage.py test
coverage report
coverage html
```

## Test Configuration

The `test_config.py` file provides:
- Base test case classes (`WozapAutoTestCase`, `WozapAutoTransactionTestCase`)
- Test mixins (`OnboardingTestMixin`, `BusinessTestMixin`)
- Test data factories (`TestDataFactory`)
- Common setup utilities

## Key Test Features

### Mocking
- WhatsApp service calls are mocked to avoid external dependencies
- File uploads are simulated with `SimpleUploadedFile`
- External API calls are mocked where necessary

### Database Testing
- Uses Django's test database
- Transaction tests for complex scenarios
- Proper cleanup after each test

### Edge Case Coverage
- Invalid form data
- Missing required fields
- Duplicate data (emails, phone numbers)
- Expired OTPs
- Maximum attempt limits
- Concurrent access scenarios

### Integration Testing
- Complete user journeys
- Cross-app functionality
- Error recovery paths

## Test Data

Tests use realistic but minimal test data:
- Valid phone numbers with country codes
- Proper email formats
- Strong passwords meeting requirements
- Business information
- Product and service data

## Common Issues Tested

The test suite specifically addresses these problematic areas in the onboarding process:

1. **Step Validation**: Users cannot skip onboarding steps
2. **Form Validation**: Proper validation of phone numbers, emails, passwords
3. **OTP Handling**: Expiry, attempts, generation, verification
4. **Error Recovery**: Graceful handling of failures
5. **Data Integrity**: Uniqueness constraints, required fields
6. **User Experience**: Proper redirects, messages, error handling

## Contributing

When adding new tests:
1. Follow the existing naming conventions
2. Use the base test classes and mixins
3. Include both positive and negative test cases
4. Test edge cases and error scenarios
5. Update this README if adding new test categories

## Test Reports

After running tests, you can generate detailed reports:
- Coverage reports show which code is tested
- Performance reports identify slow tests
- Integration reports show cross-component functionality

The test suite is designed to be comprehensive, fast, and maintainable, providing confidence in the onboarding process and overall application stability.
