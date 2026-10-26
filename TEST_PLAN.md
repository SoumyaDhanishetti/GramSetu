# GramSetu — Test Plan

## 1. Purpose

This document describes the manual tests used to check GramSetu's main features before deployment.

**Note:** Test results must be recorded after running each test. The cases below have not yet been marked as passed.

## 2. Sample Test Data

Use fictional data for testing.

| Module | Sample input | Expected result |
|---|---|---|
| Farmer Marketplace | Crop: Demo Tomato; Quantity: 50 kg; Price: ₹20/kg | Listing should appear after successful submission |
| Rural Products | Product: Demo Millet Snacks; Price: ₹100/pack | Product should appear after successful submission |
| Employment | Job: Demo Farm Assistant; Location: Demo Village | Opportunity should appear after successful submission |
| Smart Farming | A suitable test leaf image | Screening result or a clear error if the feature is unavailable |

Do not use real personal contact details in test records.

## 3. Application Startup Tests

| Test ID | Test | Expected result | Status |
|---|---|---|---|
| SM-01 | Start the Flask application | Application starts without errors | Not tested |
| SM-02 | Open the home page | Home page loads correctly | Not tested |
| SM-03 | Navigate to each available module | Pages load without server errors | Not tested |

## 4. Farmer Marketplace Tests

| Test ID | Test | Expected result | Status |
|---|---|---|---|
| FM-01 | Submit a valid crop listing | Listing is displayed | Not tested |
| FM-02 | Search for an existing crop | Matching crop appears | Not tested |
| FM-03 | Search for a nonexistent crop | No unrelated results appear | Not tested |
| FM-04 | Submit incomplete required information | Invalid input is handled appropriately | Not tested |
| FM-05 | Upload an allowed crop image, if supported | Image displays correctly | Not tested |
| FM-06 | Restart the application | Saved data remains available in configured persistent storage | Not tested |

## 5. Rural Products Tests

| Test ID | Test | Expected result | Status |
|---|---|---|---|
| RP-01 | Submit a valid product listing | Product appears in the marketplace | Not tested |
| RP-02 | Search for a product | Matching product appears | Not tested |
| RP-03 | Search for an unavailable product | No unrelated results appear | Not tested |
| RP-04 | Attempt a protected action with an incorrect PIN, if implemented | Action is rejected | Not tested |
| RP-05 | Attempt a protected action with the correct test PIN, if implemented | Only the authorized action succeeds | Not tested |
| RP-06 | Upload an allowed product image, if supported | Image displays correctly | Not tested |

## 6. Employment Tests

| Test ID | Test | Expected result | Status |
|---|---|---|---|
| EM-01 | Submit a valid job listing | Opportunity appears | Not tested |
| EM-02 | Search for a matching opportunity | Matching result appears | Not tested |
| EM-03 | Test available listing-management controls | Only permitted actions succeed | Not tested |

## 7. Smart Farming Tests

| Test ID | Test | Expected result | Status |
|---|---|---|---|
| SF-01 | Open the farming page | Page loads correctly | Not tested |
| SF-02 | Submit a suitable test image, if screening is enabled | Screening result or clear error appears | Not tested |
| SF-03 | Submit an unsupported image, if applicable | Input is handled safely | Not tested |
| SF-04 | Review the screening message | It explains that results require expert confirmation | Not tested |

## 8. Deployment Tests

| Test ID | Test | Expected result | Status |
|---|---|---|---|
| DP-01 | Review files before pushing to GitHub | No secrets or real user data are exposed | Not tested |
| DP-02 | Open the deployed website | Website loads successfully | Not tested |
| DP-03 | Test the website from another device or browser | Main pages are accessible | Not tested |
| DP-04 | Restart or redeploy the hosted app | Data and images persist when persistent storage is configured | Not tested |

## 9. Test Summary

- Date tested:
- Version or commit:
- Tests passed:
- Tests failed:
- Tests not run:
- Issues to fix before submission:

## 10. Conclusion

GramSetu should be considered ready for submission only after the required features have been tested, failures have been reviewed, and deployment-specific checks have been completed.
