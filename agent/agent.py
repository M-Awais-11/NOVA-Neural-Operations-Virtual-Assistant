"""Core agent orchestrator managing the full flow from user input to execution and response."""
import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from agent.planner import planner, Planner, PlanResult, SYSTEM_PROMPT
from agent.executor import executor, Executor, ExecutionStepResult
from memory.memory import memory, AgentMemory

logger = logging.getLogger(__name__)


class AgentResponse(BaseModel):
    user_input: str
    plan_steps: List[Dict[str, Any]]
    execution_results: List[ExecutionStepResult]
    final_response: str
    success: bool


class Agent:
    """Main Agent orchestrating Planner, Executor, Verifier, and Memory."""

    def __init__(
        self,
        planner_instance: Planner = planner,
        executor_instance: Executor = executor,
        memory_instance: AgentMemory = memory,
    ):
        self.planner = planner_instance
        self.executor = executor_instance
        self.memory = memory_instance
        self.conversation_history: List[Dict[str, Any]] = []

    def run(self, user_input: str) -> AgentResponse:
        """Processes a natural language command end-to-end."""
        plan_steps_summary: List[Dict[str, Any]] = []
        execution_results: List[ExecutionStepResult] = []

        try:
            plan_res = self.planner.plan(user_input, self.conversation_history)
        except Exception as e:
            error_msg = f"Planning failed: {e}"
            self.memory.log_interaction(
                user_input=user_input,
                status="FAILED",
                agent_response=error_msg
            )
            return AgentResponse(
                user_input=user_input,
                plan_steps=[],
                execution_results=[],
                final_response=error_msg,
                success=False
            )

        # If LLM gave a direct response with no tool calls (e.g. conversational question)
        if not plan_res.tool_calls:
            response_text = plan_res.direct_response or "I didn't find any specific action to perform."
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": response_text})

            self.memory.log_interaction(
                user_input=user_input,
                agent_response=response_text,
                status="SUCCESS"
            )

            return AgentResponse(
                user_input=user_input,
                plan_steps=[],
                execution_results=[],
                final_response=response_text,
                success=True
            )

        # Execute planned tool calls sequentially
        overall_success = True
        tool_messages_for_llm = []

        for tc in plan_res.tool_calls:
            plan_steps_summary.append({"tool": tc.tool_name, "arguments": tc.arguments})
            step_result = self.executor.execute_tool(tc.tool_name, tc.arguments)
            execution_results.append(step_result)

            if not step_result.success:
                overall_success = False

            # Format tool output for LLM synthesis
            tool_content = json.dumps(
                step_result.tool_result.to_dict()
            )
            tool_messages_for_llm.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": tool_content
            })

            # Log step to memory
            self.memory.log_interaction(
                user_input=user_input,
                plan=f"Tool: {tc.tool_name}",
                tool_name=tc.tool_name,
                tool_args=tc.arguments,
                tool_result=step_result.tool_result.to_dict(),
                status="SUCCESS" if step_result.success else ("CANCELLED" if step_result.cancelled else "FAILED")
            )

        # Synthesize final response using LLM with the tool execution outputs
        final_answer = self._synthesize_response(user_input, plan_res, tool_messages_for_llm, execution_results)

        # Update conversational memory
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": final_answer})

        return AgentResponse(
            user_input=user_input,
            plan_steps=plan_steps_summary,
            execution_results=execution_results,
            final_response=final_answer,
            success=overall_success
        )

    def _synthesize_response(
        self,
        user_input: str,
        plan_res: PlanResult,
        tool_messages: List[Dict[str, Any]],
        execution_results: List[ExecutionStepResult]
    ) -> str:
        """Sends tool execution outputs back to LLM for final response synthesis."""
        try:
            messages: List[Dict[str, Any]] = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input},
                {
                    "role": "assistant",
                    "content": plan_res.direct_response,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.tool_name,
                                "arguments": json.dumps(tc.arguments)
                            }
                        }
                        for tc in plan_res.tool_calls
                    ]
                }
            ]
            messages.extend(tool_messages)

            data = self.planner._call_llm_api(messages=messages)
            msg = data.get("choices", [{}])[0].get("message", {})
            return msg.get("content") or "Completed tasks successfully."
        except Exception as e:
            # Fallback if synthesis fails: assemble summary from step results
            logger.info(f"Synthesis fallback used: {e}")
            lines = []
            for r in execution_results:
                if r.success:
                    lines.append(f"✓ {r.tool_name}: {r.tool_result.message}")
                elif r.cancelled:
                    lines.append(f"⚠️ {r.tool_name}: Cancelled by user.")
                else:
                    lines.append(f"✗ {r.tool_name}: Error - {r.error}")
            return "\n".join(lines)


# Global default agent instance
agent = Agent()
