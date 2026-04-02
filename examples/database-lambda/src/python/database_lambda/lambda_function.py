"""Database Lambda function example"""

import json
import os
from typing import Any, Dict, Optional

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import BaseModel, ValidationError
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = Logger()

# Global database engine (reused across invocations)
_db_engine: Optional[Engine] = None


class UserRequest(BaseModel):
    """User request model"""
    name: str
    email: str


class UserResponse(BaseModel):
    """User response model"""
    id: int
    name: str
    email: str
    created_at: str


def get_database_engine() -> Engine:
    """Get database engine (singleton pattern).
    
    Returns:
        SQLAlchemy engine
    """
    global _db_engine
    
    if _db_engine is None:
        database_url = os.environ.get("DATABASE_URL", "sqlite:///example.db")
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
    """Handle database requests.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    logger.info("Processing database request", extra={
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
            created_at="2024-01-01T00:00:00Z"
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
    with engine.connect() as conn:
        # This is a simplified example - in real implementation,
        # you would use proper ORM models or prepared statements
        result = conn.execute(
            text("INSERT INTO users (name, email) VALUES (:name, :email)"),
            {"name": user_request.name, "email": user_request.email}
        )
        conn.commit()
        return result.lastrowid or 1


def get_user_from_db(engine: Engine, user_id: int) -> Optional[UserResponse]:
    """Get user from database.
    
    Args:
        engine: Database engine
        user_id: User ID
        
    Returns:
        User data or None
    """
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, name, email, created_at FROM users WHERE id = :id"),
            {"id": user_id}
        )
        row = result.fetchone()
        
        if row:
            return UserResponse(
                id=row[0],
                name=row[1],
                email=row[2],
                created_at=row[3] or "2024-01-01T00:00:00Z"
            )
        return None


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