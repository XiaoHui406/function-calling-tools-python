"""
AgentToolManager 核心功能测试
"""

from typing import Any, Dict, cast
import asyncio
import pytest
from pydantic import BaseModel, Field
from agent_tool_manager import AgentToolManager, AgentTool
from openai.types.chat import ChatCompletionMessageFunctionToolCall
from openai.types.chat.chat_completion_message_tool_call import Function
import json


class TestAgentToolRegistration:
    """测试工具注册功能"""

    def test_register_single_tool(self):
        """测试注册单个工具"""
        manager = AgentToolManager()

        class AddInput(BaseModel):
            a: int = Field(..., description="第一个数字")
            b: int = Field(..., description="第二个数字")

        @manager.agent_tool(InputClass=AddInput)
        def add(args: AddInput):
            """计算两个数字的和"""
            return args.a + args.b

        # 验证工具已注册
        assert "add" in manager.tool_name_list
        assert "add" in manager.tool_map
        assert manager.tool_map["add"].func == add
        assert manager.tool_map["add"].InputClass == AddInput

    def test_register_multiple_tools(self):
        """测试注册多个工具"""
        manager = AgentToolManager()

        class NumberInput(BaseModel):
            a: int
            b: int

        @manager.agent_tool(InputClass=NumberInput)
        def add(args: NumberInput):
            return args.a + args.b

        @manager.agent_tool(InputClass=NumberInput)
        def multiply(args: NumberInput):
            return args.a * args.b

        assert len(manager.tool_name_list) == 2
        assert "add" in manager.tool_name_list
        assert "multiply" in manager.tool_name_list

    def test_duplicate_tool_name_raises_error(self):
        """测试重复注册同名工具会抛出异常"""
        manager = AgentToolManager()

        class Input1(BaseModel):
            x: int

        @manager.agent_tool(InputClass=Input1)
        def duplicate_tool(args: Input1):
            return args.x

        # 尝试再次注册同名工具应该抛出异常
        with pytest.raises(ValueError, match="Tool name conflict"):

            @manager.agent_tool(InputClass=Input1)
            def duplicate_tool(args: Input1):
                return args.x * 2

    def test_decorated_function_still_callable(self):
        """测试装饰后的函数仍可直接调用"""
        manager = AgentToolManager()

        class AddInput(BaseModel):
            a: int
            b: int

        @manager.agent_tool(InputClass=AddInput)
        def add(args: AddInput):
            return args.a + args.b

        # 直接调用函数
        result = add(AddInput(a=3, b=5))
        assert result == 8


class TestToolSchemaGeneration:
    """测试工具 Schema 生成功能"""

    def test_generate_tools_empty(self):
        """测试空 manager 生成空工具列表"""
        manager = AgentToolManager()
        tools = manager.generate_tools()
        assert tools == []

    def test_generate_tools_with_docstring(self):
        """测试带 docstring 的工具 schema 生成"""
        manager = AgentToolManager()

        class AddInput(BaseModel):
            a: int = Field(..., description="第一个数字")
            b: int = Field(..., description="第二个数字")

        @manager.agent_tool(InputClass=AddInput)
        def add(args: AddInput):
            """计算两个数字的和"""
            return args.a + args.b

        tools = manager.generate_tools()

        assert len(tools) == 1
        tool = tools[0]
        assert tool["type"] == "function"
        assert tool["function"]["name"] == "add"
        assert (
            "description" in tool["function"]
            and tool["function"]["description"] == "计算两个数字的和"
        )
        assert "parameters" in tool["function"]
        assert "properties" in tool["function"]["parameters"]
        assert "a" in cast(Dict[str, Any], tool["function"]["parameters"]["properties"])
        assert "b" in cast(Dict[str, Any], tool["function"]["parameters"]["properties"])

    def test_generate_tools_without_docstring(self):
        """测试没有 docstring 的工具会生成默认描述"""
        manager = AgentToolManager()

        class Input(BaseModel):
            x: int

        @manager.agent_tool(InputClass=Input)
        def no_doc(args: Input):
            return args.x

        tools = manager.generate_tools()
        assert len(tools) == 1
        assert (
            "description" in tools[0]["function"]
            and "调用函数no_doc" in tools[0]["function"]["description"]
        )

    def test_generate_multiple_tools_schema(self):
        """测试生成多个工具的 schema"""
        manager = AgentToolManager()

        class NumberInput(BaseModel):
            a: int
            b: int

        @manager.agent_tool(InputClass=NumberInput)
        def add(args: NumberInput):
            """加法"""
            return args.a + args.b

        @manager.agent_tool(InputClass=NumberInput)
        def subtract(args: NumberInput):
            """减法"""
            return args.a - args.b

        tools = manager.generate_tools()
        assert len(tools) == 2

        tool_names = {tool["function"]["name"] for tool in tools}
        assert tool_names == {"add", "subtract"}


class TestToolExecution:
    """测试工具调用执行功能"""

    def test_call_tool_basic(self):
        """测试基本工具调用"""
        manager = AgentToolManager()

        class AddInput(BaseModel):
            a: int
            b: int

        @manager.agent_tool(InputClass=AddInput)
        def add(args: AddInput):
            return args.a + args.b

        # 模拟 OpenAI 返回的 tool_call
        tool_call = ChatCompletionMessageFunctionToolCall(
            id="call_123",
            function=Function(name="add", arguments='{"a": 10, "b": 20}'),
            type="function",
        )

        result = manager.call_tool(tool_call)

        assert result["role"] == "tool"
        assert result["tool_call_id"] == "call_123"
        assert json.loads(str(result["content"])) == 30

    def test_call_tool_with_complex_return(self):
        """测试返回复杂对象的工具调用"""
        manager = AgentToolManager()

        class UserInput(BaseModel):
            name: str
            age: int

        @manager.agent_tool(InputClass=UserInput)
        def get_user_info(args: UserInput):
            return {"name": args.name, "age": args.age, "is_adult": args.age >= 18}

        tool_call = ChatCompletionMessageFunctionToolCall(
            id="call_456",
            function=Function(
                name="get_user_info", arguments='{"name": "张三", "age": 25}'
            ),
            type="function",
        )

        result = manager.call_tool(tool_call)
        content = json.loads(str(result["content"]))

        assert content["name"] == "张三"
        assert content["age"] == 25
        assert content["is_adult"] is True

    def test_call_nonexistent_tool_raises_error(self):
        """测试调用不存在的工具会抛出异常"""
        manager = AgentToolManager()

        tool_call = ChatCompletionMessageFunctionToolCall(
            id="call_999",
            function=Function(name="nonexistent_tool", arguments="{}"),
            type="function",
        )

        with pytest.raises(ValueError, match="Tool not found"):
            manager.call_tool(tool_call)

    def test_call_tool_with_invalid_arguments(self):
        """测试传入无效参数会抛出验证异常"""
        manager = AgentToolManager()

        class StrictInput(BaseModel):
            required_field: str
            number: int

        @manager.agent_tool(InputClass=StrictInput)
        def strict_tool(args: StrictInput):
            return args.required_field

        tool_call = ChatCompletionMessageFunctionToolCall(
            id="call_789",
            function=Function(
                name="strict_tool",
                arguments='{"number": "not_a_number"}',  # 缺少必需字段且类型错误
            ),
            type="function",
        )

        # Pydantic 验证失败应该抛出异常
        with pytest.raises(Exception):  # 可能是 ValidationError
            manager.call_tool(tool_call)


class TestNestedObjects:
    """测试嵌套对象支持"""

    def test_nested_pydantic_models(self):
        """测试嵌套 Pydantic 模型"""
        manager = AgentToolManager()

        class Address(BaseModel):
            city: str = Field(..., description="城市")
            street: str = Field(..., description="街道")

        class User(BaseModel):
            name: str = Field(..., description="姓名")
            address: Address = Field(..., description="地址")

        class CreateUserInput(BaseModel):
            user: User = Field(..., description="用户信息")

        @manager.agent_tool(InputClass=CreateUserInput)
        def create_user(args: CreateUserInput):
            """创建用户"""
            return {"name": args.user.name, "city": args.user.address.city}

        # 验证 schema 生成
        tools = manager.generate_tools()
        assert len(tools) == 1
        assert "parameters" in tools[0]["function"]
        schema = tools[0]["function"]["parameters"]
        assert "user" in cast(Dict[str, Any], schema["properties"])

        # 验证工具调用
        tool_call = ChatCompletionMessageFunctionToolCall(
            id="call_nested",
            function=Function(
                name="create_user",
                arguments=json.dumps(
                    {
                        "user": {
                            "name": "李四",
                            "address": {"city": "上海", "street": "南京路"},
                        }
                    }
                ),
            ),
            type="function",
        )

        result = manager.call_tool(tool_call)
        content = json.loads(str(result["content"]))
        assert content["name"] == "李四"
        assert content["city"] == "上海"

    def test_list_of_objects(self):
        """测试对象列表参数"""
        manager = AgentToolManager()

        class Item(BaseModel):
            name: str
            quantity: int

        class OrderInput(BaseModel):
            items: list[Item] = Field(..., description="商品列表")

        @manager.agent_tool(InputClass=OrderInput)
        def create_order(args: OrderInput):
            """创建订单"""
            return {
                "total_items": len(args.items),
                "total_quantity": sum(item.quantity for item in args.items),
            }

        tool_call = ChatCompletionMessageFunctionToolCall(
            id="call_list",
            function=Function(
                name="create_order",
                arguments=json.dumps(
                    {
                        "items": [
                            {"name": "苹果", "quantity": 3},
                            {"name": "香蕉", "quantity": 5},
                        ]
                    }
                ),
            ),
            type="function",
        )

        result = manager.call_tool(tool_call)
        content = json.loads(str(result["content"]))
        assert content["total_items"] == 2
        assert content["total_quantity"] == 8


class TestMultipleManagers:
    """测试多个 manager 实例"""

    def test_independent_managers(self):
        """测试多个独立的 manager 实例"""
        manager1 = AgentToolManager()
        manager2 = AgentToolManager()

        class Input(BaseModel):
            x: int

        @manager1.agent_tool(InputClass=Input)
        def tool1(args: Input):
            return args.x * 2

        @manager2.agent_tool(InputClass=Input)
        def tool2(args: Input):
            return args.x * 3

        assert len(manager1.tool_name_list) == 1
        assert len(manager2.tool_name_list) == 1
        assert "tool1" in manager1.tool_name_list
        assert "tool2" in manager2.tool_name_list
        assert "tool2" not in manager1.tool_name_list
        assert "tool1" not in manager2.tool_name_list

    def test_same_function_different_managers(self):
        """测试同一个函数注册到不同 manager"""
        manager1 = AgentToolManager()
        manager2 = AgentToolManager()

        class Input(BaseModel):
            value: int

        @manager1.agent_tool(InputClass=Input)
        @manager2.agent_tool(InputClass=Input)
        def shared_tool(args: Input):
            return args.value * 10

        # 两个 manager 都应该有这个工具
        assert "shared_tool" in manager1.tool_name_list
        assert "shared_tool" in manager2.tool_name_list

        # 生成的工具列表应该独立
        tools1 = manager1.generate_tools()
        tools2 = manager2.generate_tools()
        assert len(tools1) == 1
        assert len(tools2) == 1

    def test_merge_managers_empty_list_raises_error(self):
        """测试合并空列表应该抛出异常"""
        from agent_tool_manager import merge_managers

        with pytest.raises(ValueError, match="tool_managers 列表不能为空"):
            merge_managers([])

    def test_merge_managers_invalid_type_raises_error(self):
        """测试合并包含非 AgentToolManager 实例的列表应该抛出异常"""
        from agent_tool_manager import merge_managers

        manager = AgentToolManager()

        with pytest.raises(
            ValueError, match="tool_managers 列表中包含非 AgentToolManager 实例"
        ):
            merge_managers([manager, "not_a_manager", 123])

    def test_merge_single_manager(self):
        """测试合并单个 manager"""
        from agent_tool_manager import merge_managers

        manager = AgentToolManager()

        class Input(BaseModel):
            x: int

        @manager.agent_tool(InputClass=Input)
        def tool1(args: Input):
            return args.x * 2

        merged = merge_managers([manager])

        # 验证合并后的 manager 包含原始工具
        assert len(merged.tool_name_list) == 1
        assert "tool1" in merged.tool_name_list
        assert "tool1" in merged.tool_map

        # 验证工具功能正常
        tools = merged.generate_tools()
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "tool1"

    def test_merge_multiple_managers(self):
        """测试合并多个 manager"""
        from agent_tool_manager import merge_managers

        # 创建三个不同的 manager
        manager1 = AgentToolManager()
        manager2 = AgentToolManager()
        manager3 = AgentToolManager()

        class Input(BaseModel):
            x: int

        @manager1.agent_tool(InputClass=Input)
        def tool1(args: Input):
            return args.x * 2

        @manager2.agent_tool(InputClass=Input)
        def tool2(args: Input):
            return args.x * 3

        @manager3.agent_tool(InputClass=Input)
        def tool3(args: Input):
            return args.x * 4

        merged = merge_managers([manager1, manager2, manager3])

        # 验证合并后的 manager 包含所有工具
        assert len(merged.tool_name_list) == 3
        assert set(merged.tool_name_list) == {"tool1", "tool2", "tool3"}

        # 验证工具功能正常
        tools = merged.generate_tools()
        assert len(tools) == 3
        tool_names = {tool["function"]["name"] for tool in tools}
        assert tool_names == {"tool1", "tool2", "tool3"}

    def test_merge_managers_with_duplicate_tools(self):
        """测试合并包含相同工具名的多个 manager（应该去重）"""
        from agent_tool_manager import merge_managers

        # 创建两个 manager，包含相同的工具名
        manager1 = AgentToolManager()
        manager2 = AgentToolManager()

        class Input(BaseModel):
            x: int

        # 两个 manager 都注册名为 "duplicate_tool" 的工具
        @manager1.agent_tool(InputClass=Input)
        def duplicate_tool(args: Input):
            return args.x * 2

        @manager2.agent_tool(InputClass=Input)
        def duplicate_tool(args: Input):
            return args.x * 3  # 不同的实现

        merged = merge_managers([manager1, manager2])

        # 验证去重：只保留第一个出现的工具
        assert len(merged.tool_name_list) == 1
        assert "duplicate_tool" in merged.tool_name_list

        # 验证保留的是第一个 manager 中的工具
        # 通过调用工具来验证实现
        tool_call = ChatCompletionMessageFunctionToolCall(
            id="call_dup",
            function=Function(name="duplicate_tool", arguments='{"x": 5}'),
            type="function",
        )

        result = merged.call_tool(tool_call)
        content = json.loads(str(result["content"]))
        # 应该返回 10 (5 * 2)，而不是 15 (5 * 3)
        assert content == 10

    def test_merged_manager_functionality(self):
        """测试合并后的 manager 功能完整"""
        from agent_tool_manager import merge_managers

        # 创建两个 manager，每个包含多个工具
        manager1 = AgentToolManager()
        manager2 = AgentToolManager()

        class MathInput(BaseModel):
            a: int
            b: int

        class StringInput(BaseModel):
            text: str

        @manager1.agent_tool(InputClass=MathInput)
        def add(args: MathInput):
            """加法"""
            return args.a + args.b

        @manager1.agent_tool(InputClass=MathInput)
        def multiply(args: MathInput):
            """乘法"""
            return args.a * args.b

        @manager2.agent_tool(InputClass=StringInput)
        def uppercase(args: StringInput):
            """转大写"""
            return args.text.upper()

        @manager2.agent_tool(InputClass=MathInput)
        def subtract(args: MathInput):
            """减法"""
            return args.a - args.b

        merged = merge_managers([manager1, manager2])

        # 验证工具数量
        assert len(merged.tool_name_list) == 4
        assert set(merged.tool_name_list) == {
            "add",
            "multiply",
            "uppercase",
            "subtract",
        }

        # 验证工具 schema 生成
        tools = merged.generate_tools()
        assert len(tools) == 4

        # 验证工具调用功能
        # 测试 add 工具
        add_call = ChatCompletionMessageFunctionToolCall(
            id="call_add",
            function=Function(name="add", arguments='{"a": 10, "b": 20}'),
            type="function",
        )
        add_result = merged.call_tool(add_call)
        assert json.loads(str(add_result["content"])) == 30

        # 测试 uppercase 工具
        upper_call = ChatCompletionMessageFunctionToolCall(
            id="call_upper",
            function=Function(name="uppercase", arguments='{"text": "hello"}'),
            type="function",
        )
        upper_result = merged.call_tool(upper_call)
        assert json.loads(str(upper_result["content"])) == "HELLO"

        # 测试不存在的工具
        nonexistent_call = ChatCompletionMessageFunctionToolCall(
            id="call_none",
            function=Function(name="nonexistent", arguments="{}"),
            type="function",
        )
        with pytest.raises(ValueError, match="Tool not found"):
            merged.call_tool(nonexistent_call)


class TestAsyncToolExecution:
    """测试异步工具调用执行功能"""

    @pytest.mark.asyncio
    async def test_acall_tool_with_async_function(self):
        """测试异步工具调用 - 纯异步函数"""
        manager = AgentToolManager()

        class AddInput(BaseModel):
            a: int
            b: int

        @manager.agent_tool(InputClass=AddInput)
        async def async_add(args: AddInput):
            await asyncio.sleep(0.01)  # 模拟异步操作
            return args.a + args.b

        tool_call = ChatCompletionMessageFunctionToolCall(
            id="call_async_1",
            function=Function(name="async_add", arguments='{"a": 10, "b": 20}'),
            type="function",
        )

        result = await manager.acall_tool(tool_call)

        assert result["role"] == "tool"
        assert result["tool_call_id"] == "call_async_1"
        assert json.loads(str(result["content"])) == 30

    @pytest.mark.asyncio
    async def test_acall_tool_with_sync_function(self):
        """测试异步工具调用 - 同步函数在线程池中执行"""
        manager = AgentToolManager()

        class MultiplyInput(BaseModel):
            a: int
            b: int

        @manager.agent_tool(InputClass=MultiplyInput)
        def sync_multiply(args: MultiplyInput):
            return args.a * args.b

        tool_call = ChatCompletionMessageFunctionToolCall(
            id="call_sync_1",
            function=Function(name="sync_multiply", arguments='{"a": 5, "b": 6}'),
            type="function",
        )

        result = await manager.acall_tool(tool_call)

        assert result["role"] == "tool"
        assert result["tool_call_id"] == "call_sync_1"
        assert json.loads(str(result["content"])) == 30

    @pytest.mark.asyncio
    async def test_acall_tool_mixed_functions(self):
        """测试异步工具调用 - 混合注册异步和同步工具"""
        manager = AgentToolManager()

        class MathInput(BaseModel):
            x: int
            y: int

        @manager.agent_tool(InputClass=MathInput)
        async def async_add(args: MathInput):
            await asyncio.sleep(0.01)
            return args.x + args.y

        @manager.agent_tool(InputClass=MathInput)
        def sync_subtract(args: MathInput):
            return args.x - args.y

        # 测试异步工具
        async_call = ChatCompletionMessageFunctionToolCall(
            id="call_async",
            function=Function(name="async_add", arguments='{"x": 15, "y": 25}'),
            type="function",
        )

        async_result = await manager.acall_tool(async_call)
        assert json.loads(str(async_result["content"])) == 40

        # 测试同步工具
        sync_call = ChatCompletionMessageFunctionToolCall(
            id="call_sync",
            function=Function(name="sync_subtract", arguments='{"x": 30, "y": 10}'),
            type="function",
        )

        sync_result = await manager.acall_tool(sync_call)
        assert json.loads(str(sync_result["content"])) == 20

    @pytest.mark.asyncio
    async def test_acall_tool_nonexistent(self):
        """测试异步调用不存在的工具会抛出异常"""
        manager = AgentToolManager()

        tool_call = ChatCompletionMessageFunctionToolCall(
            id="call_nonexistent",
            function=Function(name="ghost_tool", arguments="{}"),
            type="function",
        )

        with pytest.raises(ValueError, match="Tool not found"):
            await manager.acall_tool(tool_call)

    @pytest.mark.asyncio
    async def test_acall_tool_with_complex_return(self):
        """测试异步工具调用返回复杂对象"""
        manager = AgentToolManager()

        class UserInput(BaseModel):
            name: str
            age: int

        @manager.agent_tool(InputClass=UserInput)
        async def async_get_user(args: UserInput):
            await asyncio.sleep(0.01)
            return {
                "name": args.name,
                "age": args.age,
                "category": "adult" if args.age >= 18 else "minor",
            }

        tool_call = ChatCompletionMessageFunctionToolCall(
            id="call_user",
            function=Function(
                name="async_get_user", arguments='{"name": "Alice", "age": 22}'
            ),
            type="function",
        )

        result = await manager.acall_tool(tool_call)
        content = json.loads(str(result["content"]))

        assert content["name"] == "Alice"
        assert content["age"] == 22
        assert content["category"] == "adult"

    @pytest.mark.asyncio
    async def test_acall_tool_error_handling(self):
        """测试异步工具调用错误处理"""
        manager = AgentToolManager()

        class ErrorInput(BaseModel):
            should_fail: bool

        @manager.agent_tool(InputClass=ErrorInput)
        async def async_error_tool(args: ErrorInput):
            if args.should_fail:
                raise ValueError("Async error occurred")
            return "success"

        tool_call = ChatCompletionMessageFunctionToolCall(
            id="call_error",
            function=Function(
                name="async_error_tool", arguments='{"should_fail": true}'
            ),
            type="function",
        )

        result = await manager.acall_tool(tool_call)
        content = str(result["content"])

        # 错误应该被捕获并作为字符串返回
        assert "Error executing tool" in content
        assert "Async error occurred" in content
