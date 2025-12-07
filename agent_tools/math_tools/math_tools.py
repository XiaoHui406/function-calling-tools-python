"""
示例工具模块：提供 add 两数相加工具，演示 Pydantic 参数模型与工具注册装饰器的用法。
"""
# tools/math_tools.py
from pydantic import BaseModel, Field
from tool_registry import tool_manager  # 导入实例


class AddInput(BaseModel):
    """加法工具的输入参数模型。"""
    a: int = Field(..., description="第一个数字")
    b: int = Field(..., description="第二个数字")

# 使用实例进行装饰


@tool_manager.agent_tool(InputClass=AddInput)
def add(args: AddInput):
    """计算两个数字的和"""
    return args.a + args.b
