This workflow diagram illlustrates the end-to-end process for creating applicants via API from file-based data from an ATS system. It is designed with the core principles of data quality, validation and rate limit management with comprehensive error handling. 

**Data Validation**
Before any API call, the data from the row (or the system via API response) should undergo validation to ensure all required fields are present and that phone numbers and emails are formatted properly. Invalid data should be flagged and reviewed so as not to consume API rate limits on data will fail anyway

**Rate Limiting**
This workflow will actively monitor rate limits by checking the remaining request response header before calls. When it drops to a certain threshold, read the reset UNIX timestamp and sleep until ready to resume API calls. It ensures no rate limit violations and uninterrupted processing.

**Error Handling**
4xx Client errors
500 internal errors
503/504 retries
Duplicate handling

```mermaid
    flowchart TD
        Start([Start Process]) --> ReadFile[Read File with Applicant Data]
        ReadFile --> ProcessRow{More Rows to Process?}

        ProcessRow -->|Yes| ValidateData[Validate Row Data]
        ProcessRow -->|No| End([End Process])

        ValidateData --> CheckRequired{Has First Name, Last Name, Phone, Email?}
        CheckRequired -->|No| RouteMissing[Route and Notify]
        RouteMissing --> NotifyMissing[Log Missing]

        CheckRequired -->|Yes| ValidatePhone{Valid Phone Format?}
        ValidatePhone -->|No| RouteInvalidPhone[Route and Notify]
        RouteInvalidPhone --> NotifyInvalidPhone[Log Missing]


        ValidatePhone -->|Yes| ValidateEmail{Valid Email Format?}
        ValidateEmail -->|No| RouteInvalidEmail[Route and Notify]
        RouteInvalidEmail --> NotifyInvalidEmail[Log Missing]

        ValidateEmail -->|Yes| CheckRate[Check Rate Limit Remaining]

        CheckRate --> RateCheck{Rate Limit < 2?}
        RateCheck -->|Yes| GetReset[Get Unix Reset Time from Response Headers]
        RateCheck -->|No| CallCreateApplicantEndpoint

        GetReset --> Sleep[Sleep Until Reset Time]
        Sleep --> CallCreateApplicantEndpoint

        CallCreateApplicantEndpoint --> Response{HTTP Status Code?}

        Response -->|201 Success| CheckDuplicate{Check: Is Duplicate?}
        CheckDuplicate -->|No| LogSuccess[Log Success]
        CheckDuplicate -->|Yes| RouteDuplicate[Route and Notify]
        RouteDuplicate --> NotifyDuplicate[Log Duplicate]

        Response -->|4xx Client Error| Route4xx[Route and Notify]

        Response -->|500 Internal Error| Route500[Route and Notify]

        Response -->|503/504 Timeout| RetryCheck{Retry Count < 3?}
        RetryCheck -->|Yes| IncrementRetry[Increment Retry Counter]
        IncrementRetry --> BackoffSleep[Exponential Backoff Sleep]
        BackoffSleep --> CallCreateApplicantEndpoint
        RetryCheck -->|No| RouteRetryFail[Route and Notify]

        Response -->|Other Error| RouteOther[Route and Notify]

    style Start fill:#e1f5e1
    style End fill:#ffe1e1
    style LogSuccess fill:#c8e6c9
```
