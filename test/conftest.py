"""
Pytest 配置和共享 fixtures
"""
import pytest
from agent_tool_manager import AgentToolManager
from pydantic import BaseModel, Field


@pytest.fixture
def clean_manager():
    """提供一个干净的 AgentToolManager 实例"""
    return AgentToolManager()


@pytest.fixture
def sample_input_class():
    """提供一个示例输入类"""
    class SampleInput(BaseModel):
        value: int = Field(..., description="测试值")
    
    return SampleInput


@pytest.fixture
def manager_with_tools(clean_manager, sample_input_class):
    """提供一个已注册示例工具的 manager"""
    
    @clean_manager.agent_tool(InputClass=sample_input_class)
    def sample_tool(args):
        """示例工具"""
        return args.value * 2
    
    return clean_manager
