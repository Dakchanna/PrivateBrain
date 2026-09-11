from __future__ import annotations
"""
PrivateBrain AI Agent — Main Agent Loop

This is the real AI reasoning engine. It:
1. Receives a task context (robot, request, system state)
2. Calls the Ollama LLM with the specialized system prompt
3. Interprets tool calls from the LLM response
4. Executes backend tools
5. Feeds tool results back to the LLM
6. Iterates until a final structured decision is reached
7. Executes the decided action
"""

import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, Any

from app.agent.reasoning import ollama_client
from app.agent.prompts.system_prompt import PRIVATEBRAIN_SYSTEM_PROMPT
from app.agent.tools import agent_tools
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

MAX_AGENT_ITERATIONS = 8  # Prevent infinite loops


class AgentContext:
    """Short-lived task context for a single request processing session."""

    def __init__(self, request_id: str, robot_id: str, task_type: str,
                 priority: str, payload: dict, robot_repo, request_repo,
                 decision_repo, scheduler, model_router, resource_monitor):
        self.request_id = request_id
        self.robot_id = robot_id
        self.task_type = task_type
        self.priority = priority
        self.payload = payload
        # Backend services (agent cannot directly access these — only via tools)
        self._robot_repo = robot_repo
        self._request_repo = request_repo
        self._decision_repo = decision_repo
        self._scheduler = scheduler
        self._model_router = model_router
        self._resource_monitor = resource_monitor


class PrivateBrainAgent:
    """
    AI Agent powered by Ollama LLM with tool-calling architecture.

    The agent loop:
    CONTEXT → LLM → TOOL_CALL → BACKEND_EXECUTION → RESULT → LLM → DECISION
    """

    def __init__(self):
        self._use_llm = True  # Disabled gracefully if Ollama unavailable

    async def _check_llm_availability(self) -> bool:
        available = await ollama_client.is_available()
        if not available:
            logger.warning({"event": "llm_unavailable",
                            "message": "Ollama not reachable — using deterministic fallback agent"})
        return available

    def _build_context_message(self, ctx: AgentContext, system_state: dict) -> str:
        """Build the user message with full context for the LLM."""
        return f"""
New AI task request to orchestrate:

REQUEST:
  request_id: {ctx.request_id}
  robot_id:   {ctx.robot_id}
  task_type:  {ctx.task_type}
  priority:   {ctx.priority}

SYSTEM STATE:
{json.dumps(system_state, indent=2)}

Available tools you may call:
- get_robot_status(robot_id)
- get_system_resources()
- inspect_queue()
- inspect_available_models()
- estimate_task_resources(task_type)
- select_model(task_type)

After inspecting the state, return your final JSON decision.
You MUST return only valid JSON in this format:
{{
    "action": "SCHEDULE",
    "priority": "{ctx.priority}",
    "selected_model": "<model_name>",
    "reason": "<concise reason>"
}}
"""

    async def _execute_tool(self, tool_name: str, tool_args: dict, ctx: AgentContext) -> dict:
        """Execute a named tool and return its result."""
        logger.info({"event": "agent_tool_call", "tool": tool_name,
                     "request_id": ctx.request_id})
        try:
            if tool_name == "get_robot_status":
                result = await agent_tools.get_robot_status(
                    tool_args.get("robot_id", ctx.robot_id), ctx._robot_repo
                )
            elif tool_name == "get_system_resources":
                result = await agent_tools.get_system_resources(ctx._resource_monitor)
            elif tool_name == "inspect_queue":
                result = await agent_tools.inspect_queue(ctx._scheduler)
            elif tool_name == "inspect_available_models":
                result = await agent_tools.inspect_available_models(ctx._model_router)
            elif tool_name == "estimate_task_resources":
                result = await agent_tools.estimate_task_resources(
                    tool_args.get("task_type", ctx.task_type)
                )
            elif tool_name == "select_model":
                result = await agent_tools.select_model(
                    tool_args.get("task_type", ctx.task_type), ctx._model_router
                )
            else:
                result = agent_tools.ToolResult(
                    success=False, data={}, error=f"Unknown tool: {tool_name}"
                )
            return {"tool": tool_name, "success": result.success,
                    "data": result.data, "error": result.error}
        except Exception as e:
            return {"tool": tool_name, "success": False, "data": {}, "error": str(e)}

    def _parse_llm_response(self, response: str) -> tuple[Optional[dict], list[dict]]:
        """
        Parse LLM response for:
        1. Native Ollama tool_calls JSON
        2. Final decision JSON
        Returns (decision_or_None, tool_calls_list)
        """
        response = response.strip()

        # Check for native tool calls
        if response.startswith('{"tool_calls"'):
            try:
                parsed = json.loads(response)
                tool_calls = parsed.get("tool_calls", [])
                calls = []
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    calls.append({"name": fn.get("name", ""), "arguments": fn.get("arguments", {})})
                return None, calls
            except json.JSONDecodeError:
                pass

        # Try to extract JSON decision block
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                parsed = json.loads(response[start:end])
                if "action" in parsed:
                    return parsed, []
            except json.JSONDecodeError:
                pass

        # Try to find tool call patterns in plain text
        tool_calls = []
        for tool in ["get_robot_status", "get_system_resources", "inspect_queue",
                     "inspect_available_models", "estimate_task_resources", "select_model"]:
            if tool in response:
                tool_calls.append({"name": tool, "arguments": {}})
        if tool_calls:
            return None, tool_calls

        return None, []

    async def _deterministic_fallback(self, ctx: AgentContext) -> dict:
        """
        Rule-based fallback decision when Ollama is not available.
        This ensures the system always works even without an LLM.
        """
        logger.info({"event": "deterministic_fallback", "request_id": ctx.request_id})

        resources = await agent_tools.get_system_resources(ctx._resource_monitor)
        queue_state = await agent_tools.inspect_queue(ctx._scheduler)
        model_info = await agent_tools.select_model(ctx.task_type, ctx._model_router)

        resource_data = resources.data if resources.success else {}
        queue_data = queue_state.data if queue_state.success else {}
        cpu = resource_data.get("cpu_percent", 0)
        queue_size = queue_data.get("total_queued", 0)

        priority = ctx.priority.lower()

        if not model_info.success:
            action = "FALLBACK"
            selected_model = None
            reason = "No model available — triggering fallback"
        elif priority == "critical":
            action = "PROCESS"
            selected_model = model_info.data.get("model_name")
            reason = "Critical priority — immediate processing"
        elif priority == "high" and cpu < 85:
            action = "SCHEDULE"
            selected_model = model_info.data.get("model_name")
            reason = "High priority with sufficient resources — scheduling now"
        elif cpu > 85 or queue_size > 8:
            action = "QUEUE"
            selected_model = model_info.data.get("model_name")
            reason = f"Resources constrained (CPU={cpu:.0f}%, queue={queue_size}) — queuing request"
        else:
            action = "SCHEDULE"
            selected_model = model_info.data.get("model_name")
            reason = "Normal conditions — scheduling request"

        return {
            "action": action,
            "priority": priority,
            "selected_model": selected_model,
            "reason": reason,
        }

    async def process_request(self, ctx: AgentContext) -> dict:
        """
        Main agent loop: reason about the request and produce a decision.
        Uses real LLM when available, deterministic fallback otherwise.
        """
        llm_available = await self._check_llm_availability()

        if not llm_available:
            decision = await self._deterministic_fallback(ctx)
            decision["llm_used"] = False
            return decision

        # Gather initial system state for LLM context
        resources = await agent_tools.get_system_resources(ctx._resource_monitor)
        queue = await agent_tools.inspect_queue(ctx._scheduler)
        models = await agent_tools.inspect_available_models(ctx._model_router)

        system_state = {
            "resources": resources.data if resources.success else {},
            "queue": queue.data if queue.success else {},
            "models": models.data if models.success else {},
        }

        conversation: list[dict] = []
        user_message = self._build_context_message(ctx, system_state)
        decision = None

        for iteration in range(MAX_AGENT_ITERATIONS):
            logger.info({"event": "agent_iteration", "iteration": iteration,
                         "request_id": ctx.request_id})
            try:
                response = await ollama_client.generate_decision(
                    PRIVATEBRAIN_SYSTEM_PROMPT, user_message, conversation
                )
            except ConnectionError:
                logger.warning({"event": "llm_connection_lost", "request_id": ctx.request_id})
                decision = await self._deterministic_fallback(ctx)
                decision["llm_used"] = False
                return decision

            # Parse response
            parsed_decision, tool_calls = self._parse_llm_response(response)

            if parsed_decision:
                decision = parsed_decision
                decision["llm_used"] = True
                break

            if tool_calls:
                # Execute all tool calls
                tool_results = []
                for tc in tool_calls:
                    result = await self._execute_tool(tc["name"], tc.get("arguments", {}), ctx)
                    tool_results.append(result)

                # Add to conversation for next iteration
                conversation.append({"role": "assistant", "content": response})
                conversation.append({
                    "role": "user",
                    "content": f"Tool results:\n{json.dumps(tool_results, indent=2)}\n\nNow provide your final JSON decision."
                })
                user_message = ""  # User message already in conversation
            else:
                # No tools, no decision — try to extract or fallback
                logger.warning({"event": "unparseable_response", "iteration": iteration,
                                "request_id": ctx.request_id})
                conversation.append({"role": "assistant", "content": response})
                conversation.append({
                    "role": "user",
                    "content": "Please respond with ONLY the JSON decision object."
                })
                user_message = ""

        if not decision:
            logger.warning({"event": "max_iterations_reached", "request_id": ctx.request_id})
            decision = await self._deterministic_fallback(ctx)
            decision["llm_used"] = False

        # Validate decision action
        valid_actions = {"QUEUE", "SCHEDULE", "PROCESS", "RETRY", "FALLBACK", "REJECT", "WAIT"}
        if decision.get("action") not in valid_actions:
            decision["action"] = "SCHEDULE"
            decision["reason"] = "Action corrected to SCHEDULE (invalid action received)"

        return decision


# Global singleton
privatebrain_agent = PrivateBrainAgent()
