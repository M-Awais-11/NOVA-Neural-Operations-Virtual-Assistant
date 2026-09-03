"""Executor module for validating arguments, managing confirmations, and running tools."""
from typing import Dict, Any, Optional
from pydantic import BaseModel, ValidationError

from tools.registry import tool_registry
from tools.base import ToolResult
from security.confirmation import confirmation_manager
from security.permissions import RiskLevel, ActionCancelledError, AccessDeniedError
from agent.verifier import verifier, VerificationResult


class ExecutionStepResult(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    tool_result: ToolResult
    verification: VerificationResult
    success: bool
    cancelled: bool = False
    error: Optional[str] = None


class Executor:
    """Safely executes validated tool calls."""

    def __init__(self, confirmation_mgr=confirmation_manager, registry=tool_registry, verifier_instance=verifier):
        self.confirmation_mgr = confirmation_mgr
        self.registry = registry
        self.verifier = verifier_instance

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ExecutionStepResult:
        tool = self.registry.get_tool(tool_name)
        if not tool:
            err = f"Unknown tool: '{tool_name}'."
            return ExecutionStepResult(
                tool_name=tool_name,
                arguments=arguments,
                tool_result=ToolResult(success=False, error=err),
                verification=VerificationResult(verified=False, details=err),
                success=False,
                error=err
            )

        # 1. Validate arguments using Pydantic schema
        try:
            validated_args_model = tool.args_schema(**arguments)
            validated_args = validated_args_model.model_dump()
        except ValidationError as e:
            err = f"Argument validation failed for tool '{tool_name}': {e}"
            return ExecutionStepResult(
                tool_name=tool_name,
                arguments=arguments,
                tool_result=ToolResult(success=False, error=err),
                verification=VerificationResult(verified=False, details=err),
                success=False,
                error=err
            )

        # 2. Risk check and User Confirmation
        if tool.risk_level in (RiskLevel.RISKY, RiskLevel.BLOCKED):
            action_desc = f"Executing {tool.name}"
            target_info = ", ".join(f"{k}={v}" for k, v in validated_args.items())
            try:
                self.confirmation_mgr.confirm(
                    action_name=action_desc,
                    details=target_info,
                    risk_level=tool.risk_level
                )
            except ActionCancelledError as ace:
                return ExecutionStepResult(
                    tool_name=tool_name,
                    arguments=validated_args,
                    tool_result=ToolResult(success=False, error=str(ace)),
                    verification=VerificationResult(verified=False, details="Action cancelled by user."),
                    success=False,
                    cancelled=True,
                    error=str(ace)
                )

        # 3. Tool Execution
        try:
            result = tool.execute(**validated_args)
        except AccessDeniedError as ade:
            result = ToolResult(success=False, error=f"Security Violation: {ade}")
        except Exception as e:
            result = ToolResult(success=False, error=f"Execution error: {e}")

        # 4. Post-Execution Verification
        verification = self.verifier.verify(tool_name, validated_args, result)

        overall_success = result.success and verification.verified

        return ExecutionStepResult(
            tool_name=tool_name,
            arguments=validated_args,
            tool_result=result,
            verification=verification,
            success=overall_success,
            error=result.error if not result.success else (None if verification.verified else verification.details)
        )


executor = Executor()
