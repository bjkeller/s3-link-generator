"""Simple Lambda function example without database"""

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
        
        # Process request
        result = {
            "message": "Hello from Lambda!",
            "request_id": context.aws_request_id,
            "input": body
        }
        
        logger.info("Request processed successfully", extra={
            "request_id": context.aws_request_id
        })
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(result)
        }
        
    except json.JSONDecodeError as e:
        logger.warning("Invalid JSON in request body", extra={
            "error": str(e),
            "request_id": context.aws_request_id
        })
        return error_response(400, "Invalid JSON format")
        
    except Exception as e:
        logger.error("Unexpected error", extra={
            "error": str(e),
            "request_id": context.aws_request_id
        })
        return error_response(500, "Internal server error")


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
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({"error": message})
    }