<!-- 921b3dc0-4c5e-4b7b-afa1-9a5ef7cb4d3e 7ae30f15-cb5d-4ca1-8b45-5d5dc9dde9ab -->
# Enhanced Signup and Onboarding Flow

## Overview

Refactor the signup process to use Django's UserCreationForm, add email verification requirements, enforce email uniqueness, track newsletter preferences, and implement a welcome onboarding flow for profile completion.

## 1. Update User Model and Profile

**File**: `/home/bigaddict/Projects/Codebases/WozapAuto/core/models.py`

Add new fields to `UserProfile`:

- `newsletter_subscribed`: BooleanField to track newsletter opt-in
- `onboarding_completed`: BooleanField to track if welcome flow is done
- `email_verification_token`: CharField for verification token (nullable)
- `email_verification_sent_at`: DateTimeField for token expiry

Update the User model to enforce unique emails:

- Create a migration to add `unique=True` to the email field (via custom migration or using Django's User model constraints)

**Migration needed**: Create migration for new UserProfile fields

## 2. Create Custom Signup Form

**File**: `/home/bigaddict/Projects/Codebases/WozapAuto/core/forms.py` (create if doesn't exist)

Create `CustomUserCreationForm`:

- Extends Django's `UserCreationForm`
- Add fields: `first_name`, `last_name`, `email` (required), `terms_agreement`, `newsletter`
- Validate email uniqueness (case-insensitive)
- Validate password strength server-side
- Validate terms acceptance
- Clean and normalize inputs (strip whitespace, lowercase email)

## 3. Refactor Signup View

**File**: `/home/bigaddict/Projects/Codebases/WozapAuto/core/views.py`

Replace the current `signup()` function:

- Use `CustomUserCreationForm` instead of manual POST handling
- On successful signup:
- Create user (but set `is_active=True` to allow login)
- Generate email verification token
- Save newsletter preference to UserProfile
- Set `onboarding_completed=False`
- Send verification email (DO NOT auto-login yet)
- Redirect to a "check your email" page
- Handle form errors properly with messages

## 4. Create Email Verification System

**File**: `/home/bigaddict/Projects/Codebases/WozapAuto/core/email_service.py`

Add `send_verification_email(user, request)` method:

- Generate a unique verification token
- Store token in UserProfile
- Send email with verification link
- Use existing email logging infrastructure

**File**: `/home/bigaddict/Projects/Codebases/WozapAuto/core/views.py`

Create `verify_email(request, token)` view:

- Validate token and check expiry (24 hours)
- Mark user as verified (`is_verified=True`)
- Auto-login the user
- Redirect to welcome onboarding flow
- Show success message

**File**: `/home/bigaddict/Projects/Codebases/WozapAuto/core/templates/core/`

Create templates:

- `verify_email_sent.html` - "Check your email" page
- `verify_email_success.html` - Email verified success page
- `verify_email_failed.html` - Invalid/expired token page
- `emails/verification_email.html` - Email template

## 5. Create Welcome Onboarding Flow

**File**: `/home/bigaddict/Projects/Codebases/WozapAuto/core/views.py`

Create `welcome_onboarding(request)` view:

- Protected by `@login_required`
- Multi-step form to collect:
- Step 1: Company name, phone number
- Step 2: Timezone, language preference
- Step 3: Optional avatar upload
- Save to UserProfile
- Set `onboarding_completed=True`
- Redirect to dashboard

**File**: `/home/bigaddict/Projects/Codebases/WozapAuto/core/forms.py`

Create `OnboardingForm`:

- Fields: `company_name`, `phone_number`, `timezone`, `language`, `avatar` (optional)
- Validate phone number format

**File**: `/home/bigaddict/Projects/Codebases/WozapAuto/core/templates/core/`

Create template:

- `welcome_onboarding.html` - Beautiful multi-step onboarding UI

## 6. Create Verification Middleware/Decorator

**File**: `/home/bigaddict/Projects/Codebases/WozapAuto/core/decorators.py` (create new)

Create `@verified_email_required` decorator:

- Checks if user is authenticated AND email is verified
- If not verified, redirect to "please verify your email" page
- Allow access to: signin, signup, signout, verify_email, resend_verification

**File**: `/home/bigaddict/Projects/Codebases/WozapAuto/core/views.py`

Create `resend_verification(request)` view:

- Allow unverified users to request a new verification email
- Rate limit to prevent abuse (max 3 per hour)

Create `verification_required_notice(request)` view:

- Show a page explaining email verification is needed
- Button to resend verification email

## 7. Apply Verification Requirements

**Update existing views** to use `@verified_email_required`:

- `HomePageView` - allow access but show banner if not verified
- All connection views (create, qr_display, detail)
- All aiengine views
- Profile views

**Modify**: `/home/bigaddict/Projects/Codebases/WozapAuto/core/views.py`

- `HomePageView.get()` - Check if user needs onboarding, redirect if so
- Show verification banner on dashboard if not verified

## 8. Update Signup Template

**File**: `/home/bigaddict/Projects/Codebases/WozapAuto/core/templates/core/signup.html`

Update form to work with `CustomUserCreationForm`:

- Use Django form rendering or keep current design
- Update field names to match form (already uses `password1`, `password2`)
- Keep existing frontend validation
- Add server-side error display

## 9. Update URL Configuration

**File**: `/home/bigaddict/Projects/Codebases/WozapAuto/core/urls.py`

Add new URLs:

- `verify-email/<str:token>/` - Email verification view
- `verify-email-sent/` - Check your email page
- `verification-required/` - Verification notice page
- `resend-verification/` - Resend verification email
- `welcome/` - Welcome onboarding flow

## 10. Update Email Types in Audit

**File**: `/home/bigaddict/Projects/Codebases/WozapAuto/audit/models.py`

Add to `EMAIL_TYPES`:

- `('email_verification', 'Email Verification')`

## Implementation Order

1. Update models and create migrations
2. Create forms (CustomUserCreationForm, OnboardingForm)
3. Create email verification service
4. Refactor signup view
5. Create verification views and templates
6. Create onboarding flow
7. Create decorator and apply to views
8. Update templates
9. Test complete flow

## Key Security Considerations

- Use cryptographically secure tokens for verification
- Set token expiry (24 hours)
- Rate limit verification email resends
- Validate all inputs server-side
- Use Django's built-in password validation
- CSRF protection on all forms
- Prevent timing attacks on email uniqueness checks

## UX Improvements

- Clear error messages at each step
- Progress indicators in onboarding
- Email verification reminder banner
- Resend verification option
- Skip onboarding option (complete later from profile)
- Mobile-responsive design for all new pages

### To-dos

- [ ] Remove cleanupOnLeave() function and page leave event listeners from qr_display.html
- [ ] Implement 3-attempt retry logic in checkConnectionCompleteWithDelay() with 20-second intervals
- [ ] Update button disable/enable logic for both Get New QR Code and Connection Complete buttons
- [ ] Add failure state handling after 3 attempts with user guidance message