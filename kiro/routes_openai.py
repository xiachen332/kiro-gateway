# -*- coding: utf-8 -*-

# Kiro Gateway
# https://github.com/jwadow/kiro-gateway
# Copyright (C) 2025 Jwadow
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
FastAPI routes for Kiro Gateway.

Contains all API endpoints:
- / and /health: Health check
- /v1/models: Models list
- /v1/chat/completions: Chat completions
"""

import json
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Security
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import APIKeyHeader
from loguru import logger

from kiro.config import (
    PROXY_API_KEY,
    APP_VERSION,
)
from pydantic import BaseModel
from kiro.models_openai import (
    OpenAIModel,
    ModelList,
    ChatCompletionRequest,
    ChatMessage,
)
from kiro.auth import KiroAuthManager, AuthType
from kiro.cache import ModelInfoCache
from kiro.model_resolver import ModelResolver
from kiro.converters_openai import build_kiro_payload
from kiro.streaming_openai import stream_kiro_to_openai, collect_stream_response, stream_with_first_token_retry
from kiro.http_client import KiroHttpClient
from kiro.utils import generate_conversation_id
from kiro.config import WEB_SEARCH_ENABLED
from kiro.mcp_tools import handle_native_web_search

# Import debug_logger
try:
    from kiro.debug_logger import debug_logger
except ImportError:
    debug_logger = None


# --- Security scheme ---
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


async def verify_api_key(auth_header: str = Security(api_key_header)) -> bool:
    """
    Verify API key in Authorization header.
    
    Expects format: "Bearer {PROXY_API_KEY}"
    
    Args:
        auth_header: Authorization header value
    
    Returns:
        True if key is valid
    
    Raises:
        HTTPException: 401 if key is invalid or missing
    """
    if not auth_header or auth_header != f"Bearer {PROXY_API_KEY}":
        logger.warning("Access attempt with invalid API key.")
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")
    return True


# --- Router ---
router = APIRouter()


@router.get("/")
async def root():
    """
    Health check endpoint.
    
    Returns:
        Status and application version
    """
    return {
        "status": "ok",
        "message": "Kiro Gateway is running",
        "version": APP_VERSION
    }


@router.get("/health")
async def health():
    """
    Detailed health check.
    
    Returns:
        Status, timestamp and version
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": APP_VERSION
    }

@router.get("/v1/models", response_model=ModelList, dependencies=[Depends(verify_api_key)])
async def get_models(request: Request):
    """
    Return list of available models.
    
    Models are loaded at startup (blocking) and cached.
    This endpoint returns the cached list.
    
    Args:
        request: FastAPI Request for accessing app.state
    
    Returns:
        ModelList with available models in consistent format (with dots)
    """
    logger.info("Request to /v1/models")
    
    model_resolver: ModelResolver = request.app.state.model_resolver
    model_cache: ModelInfoCache = request.app.state.model_cache
    
    # Get all available models from resolver (cache + hidden models)
    available_model_ids = model_resolver.get_available_models()
    
    # Build OpenAI-compatible model list with metadata
    openai_models = []
    for model_id in available_model_ids:
        # Get model info from cache for token limits
        model_info = model_cache.get(model_id)
        max_input = model_cache.get_max_input_tokens(model_id) if model_info else 200000
        
        openai_models.append(
            OpenAIModel(
                id=model_id,
                owned_by="anthropic",
                description="Claude model via Kiro API",
                context_window=max_input,
                max_tokens=8192,
                capabilities={"text_generation": True, "vision": True}
            )
        )
    
    return ModelList(data=openai_models)


@router.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
async def chat_completions(request: Request, request_data: ChatCompletionRequest):
    """
    Chat completions endpoint - compatible with OpenAI API.
    
    Accepts requests in OpenAI format and translates them to Kiro API.
    Supports streaming and non-streaming modes.
    
    Args:
        request: FastAPI Request for accessing app.state
        request_data: Request in OpenAI ChatCompletionRequest format
    
    Returns:
        StreamingResponse for streaming mode
        JSONResponse for non-streaming mode
    
    Raises:
        HTTPException: On validation or API errors
    """
    logger.info(f"Request to /v1/chat/completions (model={request_data.model}, stream={request_data.stream})")
    
    auth_manager: KiroAuthManager = request.app.state.auth_manager
    model_cache: ModelInfoCache = request.app.state.model_cache
    
    # Note: prepare_new_request() and log_request_body() are now called by DebugLoggerMiddleware
    # This ensures debug logging works even for requests that fail Pydantic validation (422 errors)
    
    # Check for truncation recovery opportunities
    from kiro.truncation_state import get_tool_truncation, get_content_truncation
    from kiro.truncation_recovery import generate_truncation_tool_result, generate_truncation_user_message
    from kiro.models_openai import ChatMessage
    
    modified_messages = []
    tool_results_modified = 0
    content_notices_added = 0
    
    for msg in request_data.messages:
        # Check if this is a tool_result for a truncated tool call
        if msg.role == "tool" and msg.tool_call_id:
            truncation_info = get_tool_truncation(msg.tool_call_id)
            if truncation_info:
                # Modify tool_result content to include truncation notice
                synthetic = generate_truncation_tool_result(
                    tool_name=truncation_info.tool_name,
                    tool_use_id=msg.tool_call_id,
                    truncation_info=truncation_info.truncation_info
                )
                # Prepend truncation notice to original content
                modified_content = f"{synthetic['content']}\n\n---\n\nOriginal tool result:\n{msg.content}"
                
                # Create NEW ChatMessage object (Pydantic immutability)
                modified_msg = msg.model_copy(update={"content": modified_content})
                modified_messages.append(modified_msg)
                tool_results_modified += 1
                logger.debug(f"Modified tool_result for {msg.tool_call_id} to include truncation notice")
                continue  # Skip normal append since we already added modified version
        
        # Check if this is an assistant message with truncated content
        if msg.role == "assistant" and msg.content and isinstance(msg.content, str):
            truncation_info = get_content_truncation(msg.content)
            if truncation_info:
                # Add this message first
                modified_messages.append(msg)
                # Then add synthetic user message about truncation
                synthetic_user_msg = ChatMessage(
                    role="user",
                    content=generate_truncation_user_message()
                )
                modified_messages.append(synthetic_user_msg)
                content_notices_added += 1
                logger.debug(f"Added truncation notice after assistant message (hash: {truncation_info.message_hash})")
                continue  # Skip normal append since we already added it
        
        modified_messages.append(msg)
    
    if tool_results_modified > 0 or content_notices_added > 0:
        request_data.messages = modified_messages
        logger.info(f"Truncation recovery: modified {tool_results_modified} tool_result(s), added {content_notices_added} content notice(s)")
    
    # ==============================================================================
    # WebSearch Support - Path B: Auto-Injection (MCP Tool Emulation)
    # ==============================================================================
    
    # Auto-inject web_search tool if enabled (Path B - MCP emulation)
    if WEB_SEARCH_ENABLED:
        if request_data.tools is None:
            request_data.tools = []
        
        # Check if web_search already exists
        has_ws = any(
            getattr(tool, "type", None) == "function" and
            getattr(getattr(tool, "function", None), "name", None) == "web_search"
            for tool in request_data.tools
        )
        
        if not has_ws:
            from kiro.models_openai import Tool, ToolFunction
            web_search_tool = Tool(
                type="function",
                function=ToolFunction(
                    name="web_search",
                    description="Search the web for current information. Use when you need up-to-date data from the internet.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            }
                        },
                        "required": ["query"]
                    }
                )
            )
            request_data.tools.append(web_search_tool)
            logger.debug("Auto-injected web_search tool for MCP emulation (Path B)")
    
    # ==============================================================================
    # WebSearch Support - Path A: Native Format Check (OpenAI doesn't have native server-side tools)
    # ==============================================================================
    
    # OpenAI API doesn't have native server-side tools like Anthropic
    # But we check for consistency - if someone sends web_search function, handle it
    # This is actually Path B for OpenAI (all web_search goes through MCP emulation)
    
    # Generate conversation ID for Kiro API (random UUID, not used for tracking)
    conversation_id = generate_conversation_id()
    
    # Build payload for Kiro
    # profileArn is only needed for Kiro Desktop auth
    # AWS SSO OIDC (Builder ID) users don't need profileArn and it causes 403 if sent
    profile_arn_for_payload = ""
    if auth_manager.auth_type == AuthType.KIRO_DESKTOP and auth_manager.profile_arn:
        profile_arn_for_payload = auth_manager.profile_arn
    
    try:
        kiro_payload = build_kiro_payload(
            request_data,
            conversation_id,
            profile_arn_for_payload
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Log Kiro payload
    try:
        kiro_request_body = json.dumps(kiro_payload, ensure_ascii=False, indent=2).encode('utf-8')
        if debug_logger:
            debug_logger.log_kiro_request_body(kiro_request_body)
    except Exception as e:
        logger.warning(f"Failed to log Kiro request: {e}")
    
    # Create HTTP client with retry logic
    # For streaming: use per-request client to avoid CLOSE_WAIT leak on VPN disconnect (issue #54)
    # For non-streaming: use shared client for connection pooling
    url = f"{auth_manager.api_host}/generateAssistantResponse"
    logger.debug(f"Kiro API URL: {url}")
    
    if request_data.stream:
        # Streaming mode: per-request client prevents orphaned connections
        # when network interface changes (VPN disconnect/reconnect)
        http_client = KiroHttpClient(auth_manager, shared_client=None)
    else:
        # Non-streaming mode: shared client for efficient connection reuse
        shared_client = request.app.state.http_client
        http_client = KiroHttpClient(auth_manager, shared_client=shared_client)
    try:
        # Make request to Kiro API (for both streaming and non-streaming modes)
        # Important: we wait for Kiro response BEFORE returning StreamingResponse,
        # so that 200 OK means Kiro accepted the request and started responding
        response = await http_client.request_with_retry(
            "POST",
            url,
            kiro_payload,
            stream=True
        )
        
        if response.status_code != 200:
            try:
                error_content = await response.aread()
            except Exception:
                error_content = b"Unknown error"
            
            await http_client.close()
            error_text = error_content.decode('utf-8', errors='replace')
            
            # Try to parse JSON response from Kiro to extract error message
            error_message = error_text
            try:
                error_json = json.loads(error_text)
                # Enhance Kiro API errors with user-friendly messages
                from kiro.kiro_errors import enhance_kiro_error
                error_info = enhance_kiro_error(error_json)
                error_message = error_info.user_message
                # Log original error for debugging
                logger.debug(f"Original Kiro error: {error_info.original_message} (reason: {error_info.reason})")
            except (json.JSONDecodeError, KeyError):
                pass
            
            # Log access log for error (before flush, so it gets into app_logs)
            logger.warning(
                f"HTTP {response.status_code} - POST /v1/chat/completions - {error_message[:100]}"
            )
            
            # Flush debug logs on error ("errors" mode)
            if debug_logger:
                debug_logger.flush_on_error(response.status_code, error_message)
            
            # Return error in OpenAI API format
            return JSONResponse(
                status_code=response.status_code,
                content={
                    "error": {
                        "message": error_message,
                        "type": "kiro_api_error",
                        "code": response.status_code
                    }
                }
            )
        
        # Prepare data for fallback token counting
        # Convert Pydantic models to dicts for tokenizer
        messages_for_tokenizer = [msg.model_dump() for msg in request_data.messages]
        tools_for_tokenizer = [tool.model_dump() for tool in request_data.tools] if request_data.tools else None
        
        if request_data.stream:
            # Streaming mode
            async def stream_wrapper():
                streaming_error = None
                client_disconnected = False
                try:
                    async for chunk in stream_kiro_to_openai(
                        http_client.client,
                        response,
                        request_data.model,
                        model_cache,
                        auth_manager,
                        request_messages=messages_for_tokenizer,
                        request_tools=tools_for_tokenizer
                    ):
                        yield chunk
                except GeneratorExit:
                    # Client disconnected - this is normal
                    client_disconnected = True
                    logger.debug("Client disconnected during streaming (GeneratorExit in routes)")
                except Exception as e:
                    streaming_error = e
                    # Try to send [DONE] to client before finishing
                    # so client doesn't "hang" waiting for data
                    try:
                        yield "data: [DONE]\n\n"
                    except Exception:
                        pass  # Client already disconnected
                    raise
                finally:
                    await http_client.close()
                    # Log access log for streaming (success or error)
                    if streaming_error:
                        error_type = type(streaming_error).__name__
                        error_msg = str(streaming_error) if str(streaming_error) else "(empty message)"
                        logger.error(f"HTTP 500 - POST /v1/chat/completions (streaming) - [{error_type}] {error_msg[:100]}")
                    elif client_disconnected:
                        logger.info(f"HTTP 200 - POST /v1/chat/completions (streaming) - client disconnected")
                    else:
                        logger.info(f"HTTP 200 - POST /v1/chat/completions (streaming) - completed")
                    # Write debug logs AFTER streaming completes
                    if debug_logger:
                        if streaming_error:
                            debug_logger.flush_on_error(500, str(streaming_error))
                        else:
                            debug_logger.discard_buffers()
            
            return StreamingResponse(stream_wrapper(), media_type="text/event-stream")
        
        else:
            
            # Non-streaming mode - collect entire response
            openai_response = await collect_stream_response(
                http_client.client,
                response,
                request_data.model,
                model_cache,
                auth_manager,
                request_messages=messages_for_tokenizer,
                request_tools=tools_for_tokenizer
            )
            
            await http_client.close()
            
            # Log access log for non-streaming success
            logger.info(f"HTTP 200 - POST /v1/chat/completions (non-streaming) - completed")
            
            # Write debug logs after non-streaming request completes
            if debug_logger:
                debug_logger.discard_buffers()
            
            return JSONResponse(content=openai_response)
    
    except HTTPException as e:
        await http_client.close()
        # Log access log for HTTP error
        logger.error(f"HTTP {e.status_code} - POST /v1/chat/completions - {e.detail}")
        # Flush debug logs on HTTP error ("errors" mode)
        if debug_logger:
            debug_logger.flush_on_error(e.status_code, str(e.detail))
        raise
    except Exception as e:
        await http_client.close()
        logger.error(f"Internal error: {e}", exc_info=True)
        # Log access log for internal error
        logger.error(f"HTTP 500 - POST /v1/chat/completions - {str(e)[:100]}")
        # Flush debug logs on internal error ("errors" mode)
        if debug_logger:
            debug_logger.flush_on_error(500, str(e))
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


# ==================================================================================================
# /v1/responses - OpenAI Responses API (Codex CLI compatible)
# ==================================================================================================

class ResponseInputItem(BaseModel):
    """Input item for Responses API"""
    role: str
    content: Union[str, List[Any], Any]

class ResponseRequest(BaseModel):
    """OpenAI Responses API request format"""
    model: str
    input: Optional[Union[str, List[ResponseInputItem]]] = None
    instructions: Optional[str] = None
    tools: Optional[List[Any]] = None
    tool_choice: Optional[Any] = None
    stream: bool = False
    temperature: Optional[float] = None
    max_output_tokens: Optional[int] = None
    top_p: Optional[float] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    previous_response_id: Optional[str] = None
    store: bool = False
    metadata: Optional[Dict[str, Any]] = None
    user: Optional[str] = None


async def convert_chat_sse_to_responses_sse(
    chat_stream: AsyncGenerator[bytes, None],
    model: str,
    response_id: str
) -> AsyncGenerator[str, None]:
    """
    Convert chat.completions SSE stream to OpenAI Responses API SSE format.
    
    Codex CLI expects Responses API streaming events:
    - response.created
    - response.output_item.added
    - response.content_part.added
    - response.output_text.delta
    - response.content_part.done
    - response.output_item.done
    - response.completed
    """
    has_started = False
    output_index = 0
    content_index = 0
    message_id = f"msg_{response_id}"
    accumulated_text = ""
    
    async for chunk_bytes in chat_stream:
        # Handle both bytes and str (Starlette may yield either)
        if isinstance(chunk_bytes, bytes):
            chunk_text = chunk_bytes.decode('utf-8')
        else:
            chunk_text = str(chunk_bytes)
        
        for line in chunk_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            if not line.startswith('data:'):
                continue
            
            data_str = line[5:].strip()
            
            if data_str == '[DONE]':
                # Final completion event
                completed_event = {
                    "type": "response.completed",
                    "response": {
                        "id": response_id,
                        "object": "response",
                        "status": "completed",
                        "model": model,
                        "output": []
                    }
                }
                yield f"data: {json.dumps(completed_event, ensure_ascii=False)}\n\n"
                continue
            
            try:
                chat_data = json.loads(data_str)
                delta = chat_data.get("choices", [{}])[0].get("delta", {})
                finish_reason = chat_data.get("choices", [{}])[0].get("finish_reason")
                
                # Start of stream - emit initialization events
                if not has_started and (delta.get("role") or delta.get("content") or delta.get("reasoning_content")):
                    has_started = True
                    
                    # response.created
                    yield f"data: {json.dumps({'type': 'response.created', 'response': {'id': response_id, 'object': 'response', 'status': 'in_progress', 'model': model}}, ensure_ascii=False)}\n\n"
                    
                    # response.output_item.added
                    yield f"data: {json.dumps({'type': 'response.output_item.added', 'output_index': output_index, 'item': {'type': 'message', 'id': message_id, 'status': 'in_progress', 'role': 'assistant'}}, ensure_ascii=False)}\n\n"
                    
                    # response.content_part.added
                    yield f"data: {json.dumps({'type': 'response.content_part.added', 'output_index': output_index, 'content_index': content_index, 'part': {'type': 'output_text', 'text': ''}}, ensure_ascii=False)}\n\n"
                
                # Content delta
                content = delta.get("content", "")
                reasoning = delta.get("reasoning_content", "")
                text_delta = content or reasoning
                
                if text_delta:
                    accumulated_text += text_delta
                    delta_event = {
                        "type": "response.output_text.delta",
                        "output_index": output_index,
                        "content_index": content_index,
                        "delta": text_delta
                    }
                    yield f"data: {json.dumps(delta_event, ensure_ascii=False)}\n\n"
                
                # Tool calls (pass through as-is for now)
                if "tool_calls" in delta:
                    tool_calls = delta["tool_calls"]
                    for tc in tool_calls:
                        tool_event = {
                            "type": "response.function_call_arguments.delta",
                            "output_index": output_index,
                            "item_id": tc.get("id", ""),
                            "delta": json.dumps(tc.get("function", {}), ensure_ascii=False)
                        }
                        yield f"data: {json.dumps(tool_event, ensure_ascii=False)}\n\n"
                
                # Finish - emit completion events
                if finish_reason:
                    # content_part.done
                    yield f"data: {json.dumps({'type': 'response.content_part.done', 'output_index': output_index, 'content_index': content_index, 'part': {'type': 'output_text', 'text': accumulated_text}}, ensure_ascii=False)}\n\n"
                    
                    # output_item.done
                    yield f"data: {json.dumps({'type': 'response.output_item.done', 'output_index': output_index, 'item': {'type': 'message', 'id': message_id, 'status': 'completed', 'role': 'assistant'}}, ensure_ascii=False)}\n\n"
                    
                    # response.completed
                    completed_event = {
                        "type": "response.completed",
                        "response": {
                            "id": response_id,
                            "object": "response",
                            "status": "completed",
                            "model": model,
                            "output": []
                        }
                    }
                    yield f"data: {json.dumps(completed_event, ensure_ascii=False)}\n\n"
            
            except json.JSONDecodeError:
                continue
            except Exception as e:
                logger.warning(f"Error converting SSE chunk: {e}")
                continue


@router.post("/v1/responses", dependencies=[Depends(verify_api_key)])
async def responses_endpoint(request: Request, request_data: ResponseRequest):
    """
    OpenAI Responses API endpoint - compatible with Codex CLI.
    
    Converts Responses API requests to chat.completions format
    and translates responses back to Responses API format.
    """
    logger.info(f"Request to /v1/responses (model={request_data.model}, stream={request_data.stream})")
    
    # Convert Responses API request to ChatCompletionRequest
    messages = []
    
    # instructions → system message
    if request_data.instructions:
        messages.append(ChatMessage(role="system", content=request_data.instructions))
    
    # input → messages
    if request_data.input:
        if isinstance(request_data.input, str):
            messages.append(ChatMessage(role="user", content=request_data.input))
        elif isinstance(request_data.input, list):
            for item in request_data.input:
                if isinstance(item, dict):
                    messages.append(ChatMessage(role=item.get("role", "user"), content=item.get("content", "")))
                elif hasattr(item, 'role') and hasattr(item, 'content'):
                    messages.append(ChatMessage(role=item.role, content=item.content))
    
    # Build ChatCompletionRequest
    chat_request = ChatCompletionRequest(
        model=request_data.model,
        messages=messages,
        tools=request_data.tools,
        tool_choice=request_data.tool_choice,
        stream=request_data.stream,
        temperature=request_data.temperature,
        max_tokens=request_data.max_output_tokens,
        top_p=request_data.top_p,
        presence_penalty=request_data.presence_penalty,
        frequency_penalty=request_data.frequency_penalty,
        user=request_data.user,
        store=request_data.store
    )
    
    # Reuse chat_completions logic
    result = await chat_completions(request, chat_request)
    
    # Convert response back to Responses API format
    if isinstance(result, StreamingResponse):
        # Convert SSE stream from chat.completions format to Responses API format
        response_id = f"resp_{generate_conversation_id()}"
        converted_stream = convert_chat_sse_to_responses_sse(
            result.body_iterator,
            request_data.model,
            response_id
        )
        return StreamingResponse(converted_stream, media_type="text/event-stream")
    
    # Non-streaming: convert JSON response
    if isinstance(result, JSONResponse):
        chat_response = result.body
        if hasattr(chat_response, 'decode'):
            chat_response = json.loads(chat_response.decode('utf-8'))
        elif isinstance(chat_response, bytes):
            chat_response = json.loads(chat_response.decode('utf-8'))
        elif isinstance(chat_response, str):
            chat_response = json.loads(chat_response)
        
        # Build Responses API response
        response_id = chat_response.get("id", f"resp_{generate_conversation_id()}")
        created_at = chat_response.get("created", int(datetime.now(timezone.utc).timestamp()))
        model = chat_response.get("model", request_data.model)
        choices = chat_response.get("choices", [])
        usage = chat_response.get("usage", {})
        
        # Convert choices to output items
        output = []
        for choice in choices:
            message = choice.get("message", {})
            role = message.get("role", "assistant")
            content = message.get("content", "")
            tool_calls = message.get("tool_calls", [])
            
            output_item = {
                "type": "message",
                "id": f"msg_{generate_conversation_id()}",
                "status": "completed",
                "role": role,
                "content": []
            }
            
            if content:
                output_item["content"].append({
                    "type": "output_text",
                    "text": content
                })
            
            if tool_calls:
                for tc in tool_calls:
                    output_item["content"].append({
                        "type": "tool_call",
                        "id": tc.get("id", ""),
                        "call_id": tc.get("id", ""),
                        "name": tc.get("function", {}).get("name", ""),
                        "arguments": tc.get("function", {}).get("arguments", "")
                    })
            
            output.append(output_item)
        
        responses_api_response = {
            "id": response_id,
            "object": "response",
            "created_at": created_at,
            "model": model,
            "output": output,
            "usage": {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0)
            },
            "incomplete_details": None,
            "instructions": request_data.instructions,
            "max_output_tokens": request_data.max_output_tokens,
            "temperature": request_data.temperature,
            "top_p": request_data.top_p,
            "tool_choice": request_data.tool_choice,
            "tools": request_data.tools,
            "parallel_tool_calls": True,
            "store": request_data.store,
            "metadata": request_data.metadata,
            "user": request_data.user
        }
        
        return JSONResponse(content=responses_api_response)
    
    # Fallback: pass through original response
    return result


# Alias for Codex CLI compatibility when base_url doesn't include /v1 suffix
@router.post("/responses", dependencies=[Depends(verify_api_key)])
async def responses_without_v1(request: Request, request_data: ResponseRequest):
    """
    Alias endpoint for /v1/responses.
    
    Codex CLI may send requests to /responses directly when OPENAI_BASE_URL
    is configured without a /v1 suffix. This endpoint forwards to the
    main /v1/responses handler.
    """
    return await responses_endpoint(request, request_data)