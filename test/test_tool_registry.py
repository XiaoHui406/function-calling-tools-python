"""
测试全局 tool_registry 和自动加载功能
"""
from typing import Any, Dict, cast
import pytest
from tool_registry import tool_manager


class TestToolRegistry:
    """测试全局工具注册实例"""

    def test_global_manager_exists(self):
        """测试全局 manager 实例存在"""
        assert tool_manager is not None
        assert hasattr(tool_manager, 'tool_name_list')
        assert hasattr(tool_manager, 'tool_map')

    def test_math_tools_loaded(self):
        """测试 math_tools 已自动加载"""
        # agent_tools/math_tools/math_tools.py 中的 add 工具应该已被加载
        assert "add" in tool_manager.tool_name_list

    def test_can_generate_tools(self):
        """测试可以生成工具列表"""
        tools = tool_manager.generate_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

        # 验证包含 add 工具
        tool_names = [tool["function"]["name"] for tool in tools]
        assert "add" in tool_names

    def test_loaded_tool_has_correct_schema(self):
        """测试加载的工具有正确的 schema"""
        tools = tool_manager.generate_tools()
        add_tool = next(
            (t for t in tools if t["function"]["name"] == "add"), None)

        assert add_tool is not None
        assert add_tool["type"] == "function"
        assert "description" in add_tool["function"]
        assert "计算两个数字的和" in add_tool["function"]["description"]

        # 验证参数
        assert "parameters" in add_tool["function"]
        params = add_tool["function"]["parameters"]
        assert "properties" in params
        assert "a" in cast(Dict[str, Any], params["properties"])
        assert "b" in cast(Dict[str, Any], params["properties"])
