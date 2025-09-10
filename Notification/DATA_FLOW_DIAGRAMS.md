# Notification System - Data Flow Diagrams

This document contains comprehensive data flow diagrams for the notification system using Mermaid diagrams.

## 1. Overall System Data Flow

```mermaid
flowchart TD
    Client[Client/UI] -->|HTTP Request| Gateway[API Gateway]
    Gateway -->|Notification Request| NotificationServer[Notification Server]
    
    NotificationServer -->|Fetch User Data| UserDB[(User Database)]
    UserDB -->|User Profile & Devices| NotificationServer
    
    NotificationServer -->|Queue Task| Redis[(Redis Queue)]
    NotificationServer -->|Track Status| StatusTracker[Status Tracker]
    
    Redis -->|Pop Task| EmailWorker[Email Worker]
    Redis -->|Pop Task| SMSWorker[SMS Worker] 
    Redis -->|Pop Task| PushWorker[Push Worker]
    
    EmailWorker -->|Send Email| SMTP[SMTP Server]
    SMSWorker -->|Send SMS| Twilio[Twilio API]
    PushWorker -->|Send Push| FCM[Firebase Cloud Messaging]
    
    EmailWorker -->|Update Status| StatusTracker
    SMSWorker -->|Update Status| StatusTracker
    PushWorker -->|Update Status| StatusTracker
    
    StatusTracker -->|Store Status| Redis
```

## 2. Notification Request Processing Data Flow

```mermaid
flowchart TD
    Request[Notification Request] -->|user_id, type, message| Validation[Input Validation]
    Validation -->|Valid Request| UserLookup[User Data Lookup]
    
    UserLookup -->|Query User| UserDB[(User Database)]
    UserDB -->|User Profile| DeviceCheck{Need Device Token?}
    
    DeviceCheck -->|Push Notification| DeviceLookup[Fetch Device Tokens]
    DeviceCheck -->|Email/SMS| TaskCreation[Create Notification Task]
    
    DeviceLookup -->|Query Devices| UserDB
    UserDB -->|Device List| TaskCreation
    
    TaskCreation -->|Notification Task| QueueRouter[Queue Router]
    QueueRouter -->|Email Task| EmailQueue[email_queue]
    QueueRouter -->|SMS Task| SMSQueue[sms_queue]
    QueueRouter -->|Push Task| PushQueue[push_queue]
    
    TaskCreation -->|Initial Status| StatusStore[Status Storage]
    StatusStore -->|queued status| Redis[(Redis)]
```

## 3. Worker Processing Data Flow

```mermaid
flowchart TD
    subgraph "Email Worker Data Flow"
        EmailQueue[email_queue] -->|Pop Task| EmailWorker[Email Worker]
        EmailWorker -->|Parse Task| EmailPayload[Email Payload]
        EmailPayload -->|Extract Data| EmailData[To, Subject, Message]
        EmailData -->|SMTP Request| SMTPServer[SMTP Server]
        SMTPServer -->|Response| RetryLogic[Retry Logic]
        RetryLogic -->|Success| EmailSuccess[Mark as Sent]
        RetryLogic -->|Failure & < 3 attempts| EmailRetry[Retry with Backoff]
        RetryLogic -->|Failure & 3 attempts| EmailFailed[Mark as Failed]
        EmailRetry -->|Re-queue| EmailQueue
    end
    
    subgraph "SMS Worker Data Flow"  
        SMSQueue[sms_queue] -->|Pop Task| SMSWorker[SMS Worker]
        SMSWorker -->|Parse Task| SMSPayload[SMS Payload]
        SMSPayload -->|Extract Data| SMSData[To, Message]
        SMSData -->|API Request| TwilioAPI[Twilio API]
        TwilioAPI -->|Response| SMSRetryLogic[Retry Logic]
        SMSRetryLogic -->|Success| SMSSuccess[Mark as Sent]
        SMSRetryLogic -->|Failure & < 3 attempts| SMSRetry[Retry with Backoff]
        SMSRetryLogic -->|Failure & 3 attempts| SMSFailed[Mark as Failed]
        SMSRetry -->|Re-queue| SMSQueue
    end
    
    subgraph "Push Worker Data Flow"
        PushQueue[push_queue] -->|Pop Task| PushWorker[Push Worker]
        PushWorker -->|Parse Task| PushPayload[Push Payload]
        PushPayload -->|Extract Data| PushData[Device Tokens, Message]
        PushData -->|API Request| FCMAPI[Firebase Cloud Messaging]
        FCMAPI -->|Response| PushRetryLogic[Retry Logic]
        PushRetryLogic -->|Success| PushSuccess[Mark as Sent]
        PushRetryLogic -->|Failure & < 3 attempts| PushRetry[Retry with Backoff]
        PushRetryLogic -->|Failure & 3 attempts| PushFailed[Mark as Failed]
        PushRetry -->|Re-queue| PushQueue
    end
```

## 4. Status Tracking Data Flow

```mermaid
flowchart TD
    NotificationCreate[Notification Created] -->|notification_id| InitialStatus[Set Initial Status]
    InitialStatus -->|queued| StatusStore[(Status Storage)]
    
    WorkerProcess[Worker Processes Task] -->|processing| StatusUpdate[Update Status]
    StatusUpdate -->|Store Status| StatusStore
    
    DeliveryAttempt[Delivery Attempt] -->|Result| StatusEvaluation{Delivery Result}
    StatusEvaluation -->|Success| SuccessStatus[Mark as Sent]
    StatusEvaluation -->|Failure & Retries Left| ProcessingStatus[Keep as Processing]
    StatusEvaluation -->|Failure & Max Retries| FailedStatus[Mark as Failed]
    
    SuccessStatus -->|sent| StatusStore
    ProcessingStatus -->|processing| StatusStore
    FailedStatus -->|failed| StatusStore
    
    StatusStore -->|Status Data| StatusAPI[Status API Endpoints]
    StatusAPI -->|JSON Response| Client[Client Applications]
    
    StatusStore -->|User Notifications| UserHistoryAPI[User History API]
    UserHistoryAPI -->|Notification List| Client
```

## 5. User Data Management Flow

```mermaid
flowchart TD
    UserRegistration[User Registration] -->|User Profile Data| UserValidation[Validate User Data]
    UserValidation -->|Valid Data| UserStorage[(User Database)]
    
    DeviceRegistration[Device Registration] -->|Device Token Data| DeviceValidation[Validate Device Data]
    DeviceValidation -->|Valid Device| DeviceStorage[Store Device Info]
    DeviceStorage -->|Link to User| UserStorage
    
    NotificationRequest[Notification Request] -->|user_id| UserLookup[User Data Lookup]
    UserLookup -->|Query| UserStorage
    UserStorage -->|User Profile| ContactInfo[Extract Contact Info]
    
    ContactInfo -->|Email Address| EmailValidation{Has Email?}
    ContactInfo -->|Phone Number| PhoneValidation{Has Phone?}
    
    PushNotification[Push Notification] -->|user_id| DeviceLookup[Device Token Lookup]
    DeviceLookup -->|Query Devices| UserStorage
    UserStorage -->|Device List| DeviceValidation2{Has Devices?}
    
    EmailValidation -->|Yes| EmailReady[Email Ready]
    EmailValidation -->|No| EmailError[No Email Error]
    PhoneValidation -->|Yes| SMSReady[SMS Ready]
    PhoneValidation -->|No| SMSError[No Phone Error]
    DeviceValidation2 -->|Yes| PushReady[Push Ready]
    DeviceValidation2 -->|No| PushError[No Devices Error]
```

## 6. Queue Management Data Flow

```mermaid
flowchart TD
    NotificationTask[Notification Task] -->|Task Data| QueueRouter[Queue Router]
    
    QueueRouter -->|Email Task| EmailQueue[(email_queue)]
    QueueRouter -->|SMS Task| SMSQueue[(sms_queue)]
    QueueRouter -->|Push Task| PushQueue[(push_queue)]
    
    EmailQueue -->|BRPOP| EmailWorker[Email Worker]
    SMSQueue -->|BRPOP| SMSWorker[SMS Worker]
    PushQueue -->|BRPOP| PushWorker[Push Worker]
    
    EmailWorker -->|Processing| EmailTask[Process Email Task]
    SMSWorker -->|Processing| SMSTask[Process SMS Task]
    PushWorker -->|Processing| PushTask[Process Push Task]
    
    EmailTask -->|Success| EmailComplete[Task Complete]
    EmailTask -->|Failure| EmailRetryCheck{Retry Count < 3?}
    
    SMSTask -->|Success| SMSComplete[Task Complete]
    SMSTask -->|Failure| SMSRetryCheck{Retry Count < 3?}
    
    PushTask -->|Success| PushComplete[Task Complete]
    PushTask -->|Failure| PushRetryCheck{Retry Count < 3?}
    
    EmailRetryCheck -->|Yes| EmailRequeue[Re-queue with Delay]
    EmailRetryCheck -->|No| EmailFailed[Mark as Failed]
    SMSRetryCheck -->|Yes| SMSRequeue[Re-queue with Delay]
    SMSRetryCheck -->|No| SMSFailed[Mark as Failed]
    PushRetryCheck -->|Yes| PushRequeue[Re-queue with Delay]
    PushRetryCheck -->|No| PushFailed[Mark as Failed]
    
    EmailRequeue -->|LPUSH| EmailQueue
    SMSRequeue -->|LPUSH| SMSQueue
    PushRequeue -->|LPUSH| PushQueue
```

## 7. Error Handling and Retry Data Flow

```mermaid
flowchart TD
    TaskExecution[Task Execution] -->|Result| ExecutionResult{Execution Result}
    
    ExecutionResult -->|Success| SuccessPath[Success Path]
    ExecutionResult -->|Error| ErrorAnalysis[Analyze Error]
    
    ErrorAnalysis -->|Network Error| RetryableError[Retryable Error]
    ErrorAnalysis -->|Auth Error| NonRetryableError[Non-Retryable Error]
    ErrorAnalysis -->|Rate Limit| DelayedRetry[Delayed Retry]
    
    RetryableError -->|Check Attempts| RetryCounter{Attempts < 3?}
    RetryCounter -->|Yes| CalculateBackoff[Calculate Backoff Delay]
    RetryCounter -->|No| MaxRetriesReached[Max Retries Reached]
    
    CalculateBackoff -->|Exponential Backoff| DelayExecution[Delay Execution]
    DelayExecution -->|Wait Period| RequeueTask[Re-queue Task]
    
    DelayedRetry -->|Rate Limit Delay| DelayExecution
    
    RequeueTask -->|Back to Queue| TaskQueue[(Task Queue)]
    TaskQueue -->|Next Execution| TaskExecution
    
    SuccessPath -->|Update Status| StatusSuccess[Status: Sent]
    MaxRetriesReached -->|Update Status| StatusFailed[Status: Failed]
    NonRetryableError -->|Update Status| StatusError[Status: Error]
    
    StatusSuccess -->|Log Success| AuditLog[(Audit Log)]
    StatusFailed -->|Log Failure| AuditLog
    StatusError -->|Log Error| AuditLog
```

## 8. Health Check Data Flow

```mermaid
flowchart TD
    HealthRequest[Health Check Request] -->|API Call| HealthController[Health Check Controller]
    
    HealthController -->|Check Redis| RedisHealth[Redis Connection Test]
    HealthController -->|Check Database| DBHealth[Database Connection Test]
    HealthController -->|Check External APIs| ExternalHealth[External Service Test]
    
    RedisHealth -->|PING Command| Redis[(Redis)]
    Redis -->|PONG Response| RedisStatus[Redis Status]
    
    DBHealth -->|SELECT 1| Database[(User Database)]
    Database -->|Query Result| DBStatus[Database Status]
    
    ExternalHealth -->|Test Endpoints| ExternalServices[SMTP/Twilio/FCM]
    ExternalServices -->|Response Status| ExternalStatus[External Service Status]
    
    RedisStatus -->|Status Data| HealthAggregator[Health Aggregator]
    DBStatus -->|Status Data| HealthAggregator
    ExternalStatus -->|Status Data| HealthAggregator
    
    HealthAggregator -->|Overall Status| HealthResponse[Health Response JSON]
    HealthResponse -->|HTTP Response| Client[Health Check Client]
    
    HealthAggregator -->|Status Metrics| MonitoringSystem[Monitoring Dashboard]
```

## Data Models

### Notification Task Structure
```json
{
  "notification_id": "uuid",
  "user_id": "integer", 
  "type": "email|sms|push",
  "payload": {
    "subject": "string (email only)",
    "message": "string",
    "metadata": "object",
    "user_data": {
      "email": "string",
      "phone_number": "string", 
      "devices": "array"
    }
  },
  "created_at": "ISO datetime"
}
```

### Status Tracking Structure
```json
{
  "notification_id": "uuid",
  "user_id": "integer",
  "type": "email|sms|push", 
  "status": "queued|processing|sent|failed",
  "attempts": "integer",
  "created_at": "ISO datetime",
  "updated_at": "ISO datetime",
  "error_message": "string (if failed)"
}
```