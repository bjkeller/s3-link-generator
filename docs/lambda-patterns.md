# Lambda Implementation Patterns

This guide provides implementation patterns and templates for common AWS Lambda use cases in a Pants monorepo.

## Basic Lambda Pattern

### Simple HTTP API Lambda

**File: `lambda/hello_world/src/python/hello_world_lambda/lambda_function.py`**

```python
"""Simple HTTP API Lambda function"""

import json
from typing import Any, Dict

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()


def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Handle HTTP API requests.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    logger.info("Processing request", extra={
        "request_id": context.aws_request_id,
        "path": event.get("path"),
        "method": event.get("httpMethod")
    })
    
    try:
        # Extract request data
        body = json.loads(event.get("body", "{}"))
        path_params = event.get("pathParameters", {})
        query_params = event.get("queryStringParameters", {})
        
        # Process request
        result = process_request(body, path_params, query_params)
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(result)
        }
        
    except ValueError as e:
        logger.warning("Invalid request", extra={"error": str(e)})
        return error_response(400, "Invalid request format")
        
    except Exception as e:
        logger.error("Unexpected error", extra={"error": str(e)})
        return error_response(500, "Internal server error")


def process_request(body: Dict[str, Any], path_params: Dict[str, Any], 
                   query_params: Dict[str, Any]) -> Dict[str, Any]:
    """Process the business logic.
    
    Args:
        body: Request body
        path_params: Path parameters
        query_params: Query parameters
        
    Returns:
        Response data
    """
    return {
        "message": "Hello World!",
        "timestamp": context.aws_request_id,
        "data": body
    }


def error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Create standardized error response.
    
    Args:
        status_code: HTTP status code
        message: Error message
        
    Returns:
        Error response
    """
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message})
    }
```

**BUILD file:**
```python
python_sources(name="function")

python_aws_lambda_function(
    name="lambda",
    runtime="python3.11",
    handler="lambda_function.py:lambda_handler",
    include_requirements=False,
)

python_aws_lambda_layer(
    name="layer",
    runtime="python3.11",
    dependencies=[":function", "//:root#aws-lambda-powertools"],
    include_sources=False,
)
```

## Database Lambda Pattern

### Lambda with Database Connection

**File: `lambda/user_service/src/python/user_service_lambda/lambda_function.py`**

```python
"""User service Lambda with database connectivity"""

import json
import os
from typing import Any, Dict, Optional

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import BaseModel, ValidationError
from sqlalchemy import create_engine, Engine
from sqlalchemy.exc import SQLAlchemyError

logger = Logger()

# Global database engine (reused across invocations)
_db_engine: Optional[Engine] = None


class UserRequest(BaseModel):
    """User request model"""
    name: str
    email: str
    age: Optional[int] = None


class UserResponse(BaseModel):
    """User response model"""
    id: int
    name: str
    email: str
    age: Optional[int] = None
    created_at: str


def get_database_engine() -> Engine:
    """Get database engine (singleton pattern).
    
    Returns:
        SQLAlchemy engine
    """
    global _db_engine
    
    if _db_engine is None:
        database_url = os.environ["DATABASE_URL"]
        _db_engine = create_engine(
            database_url,
            pool_size=1,  # Lambda-optimized pool size
            max_overflow=0,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        logger.info("Database engine initialized")
    
    return _db_engine


def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Handle user service requests.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    logger.info("Processing user request", extra={
        "request_id": context.aws_request_id,
        "method": event.get("httpMethod")
    })
    
    try:
        method = event.get("httpMethod")
        
        if method == "POST":
            return create_user(event, context)
        elif method == "GET":
            return get_user(event, context)
        else:
            return error_response(405, "Method not allowed")
            
    except Exception as e:
        logger.error("Unexpected error", extra={
            "error": str(e),
            "request_id": context.aws_request_id
        })
        return error_response(500, "Internal server error")


def create_user(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Create a new user.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    try:
        # Validate request
        body = json.loads(event.get("body", "{}"))
        user_request = UserRequest.model_validate(body)
        
        # Get database connection
        engine = get_database_engine()
        
        # Create user in database
        user_id = create_user_in_db(engine, user_request)
        
        # Return response
        response = UserResponse(
            id=user_id,
            name=user_request.name,
            email=user_request.email,
            age=user_request.age,
            created_at="2024-01-01T00:00:00Z"  # Would be actual timestamp
        )
        
        logger.info("User created successfully", extra={
            "user_id": user_id,
            "request_id": context.aws_request_id
        })
        
        return {
            "statusCode": 201,
            "headers": {"Content-Type": "application/json"},
            "body": response.model_dump_json()
        }
        
    except ValidationError as e:
        logger.warning("Invalid request data", extra={"error": str(e)})
        return error_response(400, "Invalid request data")
        
    except SQLAlchemyError as e:
        logger.error("Database error", extra={"error": str(e)})
        return error_response(500, "Database error")


def get_user(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Get user by ID.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    try:
        # Extract user ID from path
        path_params = event.get("pathParameters", {})
        user_id = int(path_params.get("id", 0))
        
        if not user_id:
            return error_response(400, "User ID required")
        
        # Get database connection
        engine = get_database_engine()
        
        # Fetch user from database
        user = get_user_from_db(engine, user_id)
        
        if not user:
            return error_response(404, "User not found")
        
        logger.info("User retrieved successfully", extra={
            "user_id": user_id,
            "request_id": context.aws_request_id
        })
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": user.model_dump_json()
        }
        
    except ValueError as e:
        logger.warning("Invalid user ID", extra={"error": str(e)})
        return error_response(400, "Invalid user ID")
        
    except SQLAlchemyError as e:
        logger.error("Database error", extra={"error": str(e)})
        return error_response(500, "Database error")


def create_user_in_db(engine: Engine, user_request: UserRequest) -> int:
    """Create user in database.
    
    Args:
        engine: Database engine
        user_request: User data
        
    Returns:
        Created user ID
    """
    # Database implementation would go here
    # This is a placeholder
    return 123


def get_user_from_db(engine: Engine, user_id: int) -> Optional[UserResponse]:
    """Get user from database.
    
    Args:
        engine: Database engine
        user_id: User ID
        
    Returns:
        User data or None
    """
    # Database implementation would go here
    # This is a placeholder
    return UserResponse(
        id=user_id,
        name="John Doe",
        email="john@example.com",
        age=30,
        created_at="2024-01-01T00:00:00Z"
    )


def error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Create standardized error response.
    
    Args:
        status_code: HTTP status code
        message: Error message
        
    Returns:
        Error response
    """
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message})
    }
```

**BUILD file with database dependencies:**
```python
python_sources(name="function")

python_aws_lambda_function(
    name="lambda",
    runtime="python3.11",
    handler="lambda_function.py:lambda_handler",
    include_requirements=False,
)

python_aws_lambda_layer(
    name="layer",
    runtime="python3.11",
    dependencies=[
        ":function",
        "//common/src/python/database:lib",
        "//:root#aws-lambda-powertools",
        "//:root#sqlalchemy",
        "//:root#pydantic",
        "//:root#pymysql"  # or appropriate database driver
    ],
    include_sources=False,
)
```

## Event-Driven Lambda Pattern

### S3 Event Processing Lambda

**File: `lambda/file_processor/src/python/file_processor_lambda/lambda_function.py`**

```python
"""S3 event processing Lambda function"""

import json
from typing import Any, Dict, List
from urllib.parse import unquote_plus

import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()

# Initialize AWS clients
s3_client = boto3.client('s3')


def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Handle S3 events.
    
    Args:
        event: S3 event
        context: Lambda context
        
    Returns:
        Processing results
    """
    logger.info("Processing S3 event", extra={
        "request_id": context.aws_request_id,
        "records_count": len(event.get("Records", []))
    })
    
    results = []
    
    for record in event.get("Records", []):
        try:
            result = process_s3_record(record, context)
            results.append(result)
        except Exception as e:
            logger.error("Error processing record", extra={
                "error": str(e),
                "record": record
            })
            results.append({"status": "error", "error": str(e)})
    
    logger.info("S3 event processing completed", extra={
        "total_records": len(results),
        "successful": len([r for r in results if r.get("status") == "success"])
    })
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "processed": len(results),
            "results": results
        })
    }


def process_s3_record(record: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Process individual S3 record.
    
    Args:
        record: S3 event record
        context: Lambda context
        
    Returns:
        Processing result
    """
    # Extract S3 information
    s3_info = record["s3"]
    bucket_name = s3_info["bucket"]["name"]
    object_key = unquote_plus(s3_info["object"]["key"])
    event_name = record["eventName"]
    
    logger.info("Processing S3 object", extra={
        "bucket": bucket_name,
        "key": object_key,
        "event": event_name
    })
    
    if event_name.startswith("ObjectCreated"):
        return process_object_created(bucket_name, object_key)
    elif event_name.startswith("ObjectRemoved"):
        return process_object_removed(bucket_name, object_key)
    else:
        logger.warning("Unhandled event type", extra={"event": event_name})
        return {"status": "skipped", "reason": f"Unhandled event: {event_name}"}


def process_object_created(bucket_name: str, object_key: str) -> Dict[str, Any]:
    """Process object creation event.
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        
    Returns:
        Processing result
    """
    try:
        # Get object metadata
        response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
        file_size = response["ContentLength"]
        content_type = response.get("ContentType", "unknown")
        
        logger.info("Object created", extra={
            "bucket": bucket_name,
            "key": object_key,
            "size": file_size,
            "content_type": content_type
        })
        
        # Process based on file type
        if content_type.startswith("image/"):
            return process_image_file(bucket_name, object_key, file_size)
        elif content_type == "application/json":
            return process_json_file(bucket_name, object_key, file_size)
        else:
            return process_generic_file(bucket_name, object_key, file_size)
            
    except Exception as e:
        logger.error("Error processing object creation", extra={
            "bucket": bucket_name,
            "key": object_key,
            "error": str(e)
        })
        return {"status": "error", "error": str(e)}


def process_object_removed(bucket_name: str, object_key: str) -> Dict[str, Any]:
    """Process object removal event.
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        
    Returns:
        Processing result
    """
    logger.info("Object removed", extra={
        "bucket": bucket_name,
        "key": object_key
    })
    
    # Cleanup related resources
    # Implementation would go here
    
    return {
        "status": "success",
        "action": "cleanup_completed",
        "bucket": bucket_name,
        "key": object_key
    }


def process_image_file(bucket_name: str, object_key: str, file_size: int) -> Dict[str, Any]:
    """Process image file.
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        file_size: File size in bytes
        
    Returns:
        Processing result
    """
    # Image processing logic would go here
    # Example: resize, generate thumbnails, extract metadata
    
    return {
        "status": "success",
        "action": "image_processed",
        "bucket": bucket_name,
        "key": object_key,
        "size": file_size,
        "thumbnails_created": 3
    }


def process_json_file(bucket_name: str, object_key: str, file_size: int) -> Dict[str, Any]:
    """Process JSON file.
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        file_size: File size in bytes
        
    Returns:
        Processing result
    """
    try:
        # Read and parse JSON file
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        content = response["Body"].read().decode("utf-8")
        data = json.loads(content)
        
        # Process JSON data
        record_count = len(data) if isinstance(data, list) else 1
        
        logger.info("JSON file processed", extra={
            "bucket": bucket_name,
            "key": object_key,
            "records": record_count
        })
        
        return {
            "status": "success",
            "action": "json_processed",
            "bucket": bucket_name,
            "key": object_key,
            "records": record_count
        }
        
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON file", extra={
            "bucket": bucket_name,
            "key": object_key,
            "error": str(e)
        })
        return {"status": "error", "error": "Invalid JSON format"}


def process_generic_file(bucket_name: str, object_key: str, file_size: int) -> Dict[str, Any]:
    """Process generic file.
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        file_size: File size in bytes
        
    Returns:
        Processing result
    """
    # Generic file processing
    # Example: virus scan, metadata extraction, archival
    
    return {
        "status": "success",
        "action": "file_processed",
        "bucket": bucket_name,
        "key": object_key,
        "size": file_size
    }
```

## Batch Processing Pattern

### SQS Batch Processing Lambda

**File: `lambda/batch_processor/src/python/batch_processor_lambda/lambda_function.py`**

```python
"""SQS batch processing Lambda function"""

import json
from typing import Any, Dict, List

import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import BaseModel, ValidationError

logger = Logger()

# Initialize AWS clients
sqs_client = boto3.client('sqs')


class ProcessingTask(BaseModel):
    """Processing task model"""
    task_id: str
    task_type: str
    data: Dict[str, Any]
    priority: int = 1


def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Handle SQS batch events.
    
    Args:
        event: SQS event
        context: Lambda context
        
    Returns:
        Batch processing results
    """
    logger.info("Processing SQS batch", extra={
        "request_id": context.aws_request_id,
        "records_count": len(event.get("Records", []))
    })
    
    successful_messages = []
    failed_messages = []
    
    for record in event.get("Records", []):
        try:
            result = process_sqs_record(record, context)
            if result["status"] == "success":
                successful_messages.append(record["messageId"])
            else:
                failed_messages.append({
                    "itemIdentifier": record["messageId"],
                    "error": result.get("error", "Unknown error")
                })
        except Exception as e:
            logger.error("Error processing SQS record", extra={
                "message_id": record.get("messageId"),
                "error": str(e)
            })
            failed_messages.append({
                "itemIdentifier": record["messageId"],
                "error": str(e)
            })
    
    logger.info("SQS batch processing completed", extra={
        "successful": len(successful_messages),
        "failed": len(failed_messages)
    })
    
    # Return batch item failures for partial batch failure handling
    response = {}
    if failed_messages:
        response["batchItemFailures"] = failed_messages
    
    return response


def process_sqs_record(record: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Process individual SQS record.
    
    Args:
        record: SQS record
        context: Lambda context
        
    Returns:
        Processing result
    """
    message_id = record["messageId"]
    receipt_handle = record["receiptHandle"]
    
    try:
        # Parse message body
        body = json.loads(record["body"])
        task = ProcessingTask.model_validate(body)
        
        logger.info("Processing task", extra={
            "message_id": message_id,
            "task_id": task.task_id,
            "task_type": task.task_type,
            "priority": task.priority
        })
        
        # Process based on task type
        if task.task_type == "data_processing":
            result = process_data_task(task)
        elif task.task_type == "notification":
            result = process_notification_task(task)
        elif task.task_type == "cleanup":
            result = process_cleanup_task(task)
        else:
            raise ValueError(f"Unknown task type: {task.task_type}")
        
        logger.info("Task completed successfully", extra={
            "message_id": message_id,
            "task_id": task.task_id,
            "result": result
        })
        
        return {"status": "success", "result": result}
        
    except ValidationError as e:
        logger.error("Invalid task format", extra={
            "message_id": message_id,
            "error": str(e)
        })
        return {"status": "error", "error": "Invalid task format"}
        
    except Exception as e:
        logger.error("Task processing failed", extra={
            "message_id": message_id,
            "error": str(e)
        })
        return {"status": "error", "error": str(e)}


def process_data_task(task: ProcessingTask) -> Dict[str, Any]:
    """Process data processing task.
    
    Args:
        task: Processing task
        
    Returns:
        Processing result
    """
    # Data processing logic
    data = task.data
    
    # Example: transform data
    processed_count = len(data.get("items", []))
    
    # Example: store results
    # store_processed_data(processed_data)
    
    return {
        "task_id": task.task_id,
        "processed_items": processed_count,
        "status": "completed"
    }


def process_notification_task(task: ProcessingTask) -> Dict[str, Any]:
    """Process notification task.
    
    Args:
        task: Processing task
        
    Returns:
        Processing result
    """
    # Notification logic
    recipient = task.data.get("recipient")
    message = task.data.get("message")
    
    # Example: send notification
    # send_notification(recipient, message)
    
    return {
        "task_id": task.task_id,
        "recipient": recipient,
        "status": "sent"
    }


def process_cleanup_task(task: ProcessingTask) -> Dict[str, Any]:
    """Process cleanup task.
    
    Args:
        task: Processing task
        
    Returns:
        Processing result
    """
    # Cleanup logic
    resource_id = task.data.get("resource_id")
    
    # Example: cleanup resources
    # cleanup_resource(resource_id)
    
    return {
        "task_id": task.task_id,
        "resource_id": resource_id,
        "status": "cleaned"
    }
```

## Shared Utilities Pattern

### Common Response Handler

**File: `common/src/python/responses/BUILD`**
```python
python_sources(name="lib")
```

**File: `common/src/python/responses/handler.py`**
```python
"""Common response handling utilities"""

import json
from typing import Any, Dict, Optional

from aws_lambda_powertools import Logger

logger = Logger()


def success_response(data: Any, status_code: int = 200, 
                    headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Create success response.
    
    Args:
        data: Response data
        status_code: HTTP status code
        headers: Additional headers
        
    Returns:
        API Gateway response
    """
    default_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
    }
    
    if headers:
        default_headers.update(headers)
    
    return {
        "statusCode": status_code,
        "headers": default_headers,
        "body": json.dumps(data) if not isinstance(data, str) else data
    }


def error_response(status_code: int, message: str, 
                  error_code: Optional[str] = None,
                  headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Create error response.
    
    Args:
        status_code: HTTP status code
        message: Error message
        error_code: Application-specific error code
        headers: Additional headers
        
    Returns:
        API Gateway response
    """
    default_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
    }
    
    if headers:
        default_headers.update(headers)
    
    error_body = {"error": message}
    if error_code:
        error_body["error_code"] = error_code
    
    return {
        "statusCode": status_code,
        "headers": default_headers,
        "body": json.dumps(error_body)
    }


def validation_error_response(errors: Any) -> Dict[str, Any]:
    """Create validation error response.
    
    Args:
        errors: Validation errors
        
    Returns:
        API Gateway response
    """
    return error_response(
        status_code=400,
        message="Validation failed",
        error_code="VALIDATION_ERROR"
    )
```

## Testing Patterns

### Lambda Test Template

**File: `lambda/user_service/test/python/test_lambda_function.py`**

```python
"""Tests for user service lambda function"""

import json
from unittest.mock import MagicMock, patch

import pytest
from user_service_lambda.lambda_function import lambda_handler, UserRequest


@pytest.fixture
def lambda_context():
    """Mock Lambda context"""
    context = MagicMock()
    context.aws_request_id = "test-request-id"
    context.function_name = "test-function"
    context.memory_limit_in_mb = 128
    context.remaining_time_in_millis = 30000
    return context


@pytest.fixture
def api_gateway_event():
    """Mock API Gateway event"""
    return {
        "httpMethod": "POST",
        "path": "/users",
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30
        }),
        "pathParameters": None,
        "queryStringParameters": None
    }


def test_create_user_success(api_gateway_event, lambda_context):
    """Test successful user creation"""
    with patch('user_service_lambda.lambda_function.get_database_engine'), \
         patch('user_service_lambda.lambda_function.create_user_in_db', return_value=123):
        
        response = lambda_handler(api_gateway_event, lambda_context)
        
        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["id"] == 123
        assert body["name"] == "John Doe"
        assert body["email"] == "john@example.com"


def test_create_user_invalid_data(lambda_context):
    """Test user creation with invalid data"""
    event = {
        "httpMethod": "POST",
        "path": "/users",
        "body": json.dumps({"name": ""}),  # Invalid: empty name
        "pathParameters": None,
        "queryStringParameters": None
    }
    
    response = lambda_handler(event, lambda_context)
    
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body


def test_get_user_success(lambda_context):
    """Test successful user retrieval"""
    event = {
        "httpMethod": "GET",
        "path": "/users/123",
        "pathParameters": {"id": "123"},
        "queryStringParameters": None
    }
    
    with patch('user_service_lambda.lambda_function.get_database_engine'), \
         patch('user_service_lambda.lambda_function.get_user_from_db') as mock_get:
        
        mock_user = MagicMock()
        mock_user.model_dump_json.return_value = json.dumps({
            "id": 123,
            "name": "John Doe",
            "email": "john@example.com"
        })
        mock_get.return_value = mock_user
        
        response = lambda_handler(event, lambda_context)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["id"] == 123


def test_user_not_found(lambda_context):
    """Test user not found scenario"""
    event = {
        "httpMethod": "GET",
        "path": "/users/999",
        "pathParameters": {"id": "999"},
        "queryStringParameters": None
    }
    
    with patch('user_service_lambda.lambda_function.get_database_engine'), \
         patch('user_service_lambda.lambda_function.get_user_from_db', return_value=None):
        
        response = lambda_handler(event, lambda_context)
        
        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["error"] == "User not found"


def test_method_not_allowed(lambda_context):
    """Test unsupported HTTP method"""
    event = {
        "httpMethod": "DELETE",
        "path": "/users/123",
        "pathParameters": {"id": "123"},
        "queryStringParameters": None
    }
    
    response = lambda_handler(event, lambda_context)
    
    assert response["statusCode"] == 405
    body = json.loads(response["body"])
    assert body["error"] == "Method not allowed"
```

These patterns provide a solid foundation for implementing various types of Lambda functions in your monorepo. Each pattern includes proper error handling, logging, testing, and follows AWS Lambda best practices.