"""Tests for simple lambda function"""

import json
from unittest.mock import MagicMock

import pytest
from simple_lambda.lambda_function import lambda_handler


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
        "path": "/hello",
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"name": "World"}),
        "pathParameters": None,
        "queryStringParameters": None
    }


def test_lambda_handler_success(api_gateway_event, lambda_context):
    """Test successful lambda execution"""
    response = lambda_handler(api_gateway_event, lambda_context)
    
    assert response["statusCode"] == 200
    assert "Content-Type" in response["headers"]
    
    body = json.loads(response["body"])
    assert "message" in body
    assert body["request_id"] == "test-request-id"
    assert body["input"]["name"] == "World"


def test_lambda_handler_invalid_json(lambda_context):
    """Test lambda with invalid JSON"""
    event = {
        "httpMethod": "POST",
        "path": "/hello",
        "body": "invalid json",
        "pathParameters": None,
        "queryStringParameters": None
    }
    
    response = lambda_handler(event, lambda_context)
    
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["error"] == "Invalid JSON format"


def test_lambda_handler_empty_body(lambda_context):
    """Test lambda with empty body"""
    event = {
        "httpMethod": "POST",
        "path": "/hello",
        "body": None,
        "pathParameters": None,
        "queryStringParameters": None
    }
    
    response = lambda_handler(event, lambda_context)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["input"] == {}