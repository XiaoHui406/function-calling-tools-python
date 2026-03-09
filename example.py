"""
集成演示脚本：展示工具注册、tools schema 生成、模型工具调用闭环。

本示例展示了三种工具注册方式：
1. 方式1：自动类型推导（新功能）
2. 方式2：使用 Pydantic BaseModel（原有功能）
3. 方式3：演示工具调用
"""
import asyncio
import os
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageFunctionToolCall
from openai.types.chat.chat_completion_message_tool_call import Function
from pydantic import BaseModel, Field
from typing import Any
import json
from tool_registry import tool_manager

print("=" * 70)
print("Function Calling Tools Demo")
print("=" * 70)

# =============================================================================
# 方式1：自动类型推导 - 无需定义 BaseModel（新功能，推荐）
# =============================================================================
print("\n[方式1] 带默认值的自动生成")
print("-" * 70)


@tool_manager.agent_tool()
def add_numbers(a: int, b: int):
    """
    计算两个整数的和。
    """
    print(f"[DEBUG] 执行计算: {a} + {b}")
    return {"result": a + b, "message": f"{a} + {b} = {a + b}"}


print("✅ 成功注册工具: add_numbers")
print(f"生成的参数模型: {tool_manager.tool_map['add_numbers'].InputClass.__name__}")

# =============================================================================
# 演示带默认值的情况
# =============================================================================


@tool_manager.agent_tool()
def greet_user(name: str, greeting: str = "你好"):
    """
    向用户问候。
    """
    print(f"[DEBUG] 问候用户: {name}, {greeting}")
    return {"message": f"{greeting}, {name}！", "success": True}


print("✅ 成功注册工具: greet_user")
print(f"生成的参数模型: {tool_manager.tool_map['greet_user'].InputClass.__name__}")

# =============================================================================
# 演示可选参数的情况
# =============================================================================


@tool_manager.agent_tool()
def get_user_info(user_id: int, include_email: bool = True):
    """
    获取用户信息。

    Args:
        user_id: 用户ID
        include_email: 是否包含邮箱（默认包含）
    """
    print(f"[DEBUG] 查询用户ID: {user_id}, 包含邮箱: {include_email}")
    return {
        "user_id": user_id,
        "name": "张三",
        "email": "zhangsan@example.com" if include_email else None
    }


print("✅ 成功注册工具: get_user_info")
print(f"生成的参数模型: {tool_manager.tool_map['get_user_info'].InputClass.__name__}")

# =============================================================================
# 演示许多参数的情况
# =============================================================================


@tool_manager.agent_tool()
def create_user(username: str, email: str, age: int = 18, is_active: bool = True):
    """
    创建新用户。
    """
    print(f"[DEBUG] 创建用户: {username}, {email}, age={age}")
    return {
        "user_id": 123,
        "username": username,
        "email": email,
        "age": age,
        "is_active": is_active,
        "status": "created"
    }


print("✅ 成功注册工具: create_user")
print(f"生成的参数模型: {tool_manager.tool_map['create_user'].InputClass.__name__}")

# =============================================================================
# 方式2：手动指定 Pydantic BaseModel（原有功能，功能最强）
# =============================================================================
print("\n[方式2] 手动指定 Pydantic BaseModel")
print("-" * 70)


class GetWeatherParams(BaseModel):
    """
    获取指定城市当前天气信息的输入参数。
    """
    city: str = Field(description='城市名称', max_length=50)
    unit: str = Field(
        default='celsius',
        description='温度单位，默认为摄氏度',
        pattern='^(celsius|fahrenheit|kelvin)$'
    )


@tool_manager.agent_tool(InputClass=GetWeatherParams)
def get_current_weather(params: GetWeatherParams):
    """
    根据城市名称获取当前天气。
    """
    print(f"[DEBUG] 查询城市: {params.city}, 单位: {params.unit}")
    return {
        "temperature": "25°C",
        "city": params.city,
        "description": "晴朗",
        "humidity": 60
    }


print("✅ 成功注册工具: get_current_weather（手动 BaseModel）")
print(
    f"使用的参数模型: {tool_manager.tool_map['get_current_weather'].InputClass.__name__}")


class GetTimeParams(BaseModel):
    """
    获取指定地点的当前时间。
    """
    location: str = Field(description="地点名称")
    format: str = Field(default="24h", description="时间格式")


@tool_manager.agent_tool(InputClass=GetTimeParams)
def get_current_time(params: GetTimeParams):
    """
    根据地点获取当前时间。
    """
    print(f"[DEBUG] 查询地点: {params.location}, 格式: {params.format}")
    return {
        "time": "2026-01-05 16:30:45",
        "timezone": "Asia/Shanghai",
        "location": params.location,
        "format": params.format
    }


print("✅ 成功注册工具: get_current_time（手动 BaseModel）")

# 测试缺少类型注解
print("\n[注意] 验证缺少类型注解会报错（这是正确的）")
try:
    @tool_manager.agent_tool()
    def bad_example(no_type_annotation):  # 缺少类型注解
        """这是一个错误的示例"""
        return {"error": True}

    print("❌ 测试失败，应该报错但没有")
except ValueError as e:
    print(f"✅ 正确捕获错误: {e}")

# =============================================================================
# 输出 JSON Schema
# =============================================================================
print("\n" + "=" * 70)
print("生成的 Tools Schema")
print("=" * 70)
print(json.dumps(tool_manager.generate_tools(), indent=2, ensure_ascii=False))

# =============================================================================
# 测试部分注册的函数是否仍然可以直接调用
# =============================================================================
print("\n" + "=" * 70)
print("测试直接调用（验证原函数功能未受影响）")
print("=" * 70)
print(add_numbers(a=123, b=456))
print(greet_user(name="世界"))
print(get_current_weather(GetWeatherParams(city="北京", unit="celsius")))

# =============================================================================
# 模拟 OpenAI 工具调用
# =============================================================================
print("\n" + "=" * 70)
print("模拟 OpenAI 工具调用")
print("=" * 70)

mock_calls = [
    {
        "name": "add_numbers",
        "arguments": {"a": 39, "b": 186}
    },
    {
        "name": "get_current_weather",
        "arguments": {"city": "北京", "unit": "celsius"}
    },
    {
        "name": "greet_user",
        "arguments": {"name": "世界"}  # greeting 使用默认值
    },
    {
        "name": "get_user_info",
        "arguments": {"user_id": 12345, "include_email": False}
    },
    {
        "name": "create_user",
        "arguments": {"username": "testuser", "email": "test@test.com"}
    },
]

for i, mock_call in enumerate(mock_calls, 1):
    tool_call = ChatCompletionMessageFunctionToolCall(
        id=f"call_{i:03d}",
        type="function",
        function=Function(
            name=mock_call["name"],
            arguments=json.dumps(mock_call["arguments"], ensure_ascii=False)
        )
    )

    print(f"\n调用 {i}: {mock_call['name']}")
    print(f"参数: {mock_call['arguments']}")

    try:
        output = tool_manager.call_tool(tool_call)
        assert type(output['content']) is str
        print(
            f"结果: {json.dumps(json.loads(output['content']), indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"❌ 错误: {e}")

# =============================================================================
# Function Calling 完整测试
# =============================================================================

# 加载环境变量配置
load_dotenv()
api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")
model = os.getenv("MODEL")

# 检查必需的环境变量
if not api_key:
    print("\n⚠️  警告: 缺少环境变量 API_KEY，跳过在线测试")
    print("请在 .env 文件中配置 API_KEY, BASE_URL, MODEL")
elif not base_url:
    print("\n⚠️  警告: 缺少环境变量 BASE_URL，跳过在线测试")
elif not model:
    print("\n⚠️  警告: 缺少环境变量 MODEL，跳过在线测试")
else:
    print("\n" + "=" * 70)
    print("OpenAI Function Calling 在线测试")
    print("=" * 70)

    def send_messages(messages):
        """发送消息到模型并附带已注册的 tools Schema，返回模型消息。"""
        try:
            assert type(model) is str
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tool_manager.generate_tools()
            )
            return response.choices[0].message
        except Exception as e:
            print(f"❌ 调用模型失败: {e}")
            raise

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )

    def run_function_calling_test():
        """
        运行 function calling 完整测试流程。
        """
        print("\n示例问题 1: 39+186=?")

        # 初始化对话消息
        messages: list[Any] = [
            {"role": "user", "content": "39+186=?"}
        ]

        print("\n[步骤1] 发送消息到模型...")
        message = send_messages(messages)

        # 检查模型是否返回了工具调用
        if not message.tool_calls:
            print(f"\n模型直接回复（未使用工具）: {message.content}")
            return

        assert isinstance(
            message.tool_calls[0], ChatCompletionMessageFunctionToolCall)

        print(f"\n[步骤2] 模型请求调用工具: {message.tool_calls[0].function.name}")
        print(f"工具参数: {message.tool_calls[0].function.arguments}")

        # 执行工具调用
        tool = message.tool_calls[0]
        messages.append(message)

        try:
            print(f"\n[步骤3] 执行工具调用...")
            output = tool_manager.call_tool(tool)
            print(f"工具执行结果: {output['content']}")
            messages.append(output)
        except Exception as e:
            print(f"❌ 工具调用失败: {e}")
            return

        # 第二次调用：获取最终回复
        print(f"\n[步骤4] 将工具结果返回给模型...")
        message = send_messages(messages)
        print(f"\n模型最终回复: {message.content}")
        print("\n✅ 测试 1 完成")

        # 示例问题 2
        print("\n" + "-" * 70)
        print("\n示例问题 2: 查询北京的天气")

        messages = [
            {"role": "user", "content": "查询北京的天气，使用摄氏度"}
        ]

        print("\n[步骤1] 发送消息到模型...")
        message = send_messages(messages)

        if not message.tool_calls:
            print(f"\n模型直接回复: {message.content}")
            return

        assert type(message.tool_calls[0]
                    ) is ChatCompletionMessageFunctionToolCall
        print(f"\n[步骤2] 模型请求调用工具: {message.tool_calls[0].function.name}")
        print(f"工具参数: {message.tool_calls[0].function.arguments}")

        tool = message.tool_calls[0]
        messages.append(message)

        try:
            print(f"\n[步骤3] 执行工具调用...")
            output = tool_manager.call_tool(tool)
            print(f"工具执行结果: {output['content']}")
            messages.append(output)
        except Exception as e:
            print(f"❌ 工具调用失败: {e}")
            return

        print(f"\n[步骤4] 将工具结果返回给模型...")
        message = send_messages(messages)
        print(f"\n模型最终回复: {message.content}")
        print("\n✅ 测试 2 完成")

    # 运行测试
    try:
        run_function_calling_test()
    except Exception as e:
        print(f"\n❌ 在线测试失败: {e}")
        print("请检查网络连接或 API 配置")

print("\n" + "=" * 70)
print("=" * 70)


# =============================================================================
# 异步工具调用演示
# =============================================================================
print("\n" + "=" * 70)
print("异步工具调用演示 (acall_tool)")
print("=" * 70)


# 定义异步工具
@tool_manager.agent_tool()
async def async_search_data(query: str, limit: int = 5):
    """
    异步搜索数据。

    Args:
        query: 搜索关键词
        limit: 返回结果数量限制
    """
    print(f"[ASYNC DEBUG] 异步搜索: {query}, limit={limit}")
    # 模拟异步操作（如网络请求）
    await asyncio.sleep(0.1)
    return {
        "query": query,
        "results": [f"Result {i} for {query}" for i in range(limit)],
        "total": limit
    }


# 定义同步工具（用于测试 acall_tool 自动处理同步函数）
@tool_manager.agent_tool()
def sync_process_data(data: str, uppercase: bool = True):
    """
    同步处理数据。

    Args:
        data: 要处理的数据
        uppercase: 是否转换为大写
    """
    print(f"[SYNC DEBUG] 同步处理数据: {data}")
    # 模拟一些处理时间
    import time
    time.sleep(0.05)
    if uppercase:
        data = data.upper()
    return {"processed": data, "length": len(data)}


print("✅ 成功注册异步工具: async_search_data")
print("✅ 成功注册同步工具: sync_process_data")


async def run_async_demo():
    """运行异步工具调用演示"""

    print("\n" + "-" * 70)
    print("测试 1: 异步调用 async_search_data")
    print("-" * 70)

    # 创建模拟的 tool_call
    tool_call = ChatCompletionMessageFunctionToolCall(
        id="async_call_001",
        type="function",
        function=Function(
            name="async_search_data",
            arguments=json.dumps(
                {"query": "Python", "limit": 3}, ensure_ascii=False)
        )
    )

    print(f"调用工具: async_search_data")
    print(f"参数: {{'query': 'Python', 'limit': 3}}")

    try:
        # 使用 acall_tool 异步调用
        output = await tool_manager.acall_tool(tool_call)
        content = output['content']
        assert isinstance(content, str)
        print(
            f"结果: {json.dumps(json.loads(content), indent=2, ensure_ascii=False)}")
        print("✅ 异步调用成功")
    except Exception as e:
        print(f"❌ 错误: {e}")

    print("\n" + "-" * 70)
    print("测试 2: 异步调用 sync_process_data (同步函数)")
    print("-" * 70)

    # 创建模拟的 tool_call
    tool_call = ChatCompletionMessageFunctionToolCall(
        id="async_call_002",
        type="function",
        function=Function(
            name="sync_process_data",
            arguments=json.dumps(
                {"data": "hello world", "uppercase": True}, ensure_ascii=False)
        )
    )

    print(f"调用工具: sync_process_data")
    print(f"参数: {{'data': 'hello world', 'uppercase': True}}")

    try:
        # 使用 acall_tool 异步调用同步函数（会自动在线程池中执行）
        output = await tool_manager.acall_tool(tool_call)
        content = output['content']
        assert isinstance(content, str)
        print(
            f"结果: {json.dumps(json.loads(content), indent=2, ensure_ascii=False)}")
        print("✅ 异步调用同步函数成功")
    except Exception as e:
        print(f"❌ 错误: {e}")

    print("\n" + "-" * 70)
    print("测试 3: 多个工具顺序异步调用")
    print("-" * 70)

    tasks = []

    # 创建多个 tool_call
    for i in range(3):
        tool_call = ChatCompletionMessageFunctionToolCall(
            id=f"async_call_00{3+i}",
            type="function",
            function=Function(
                name="async_search_data",
                arguments=json.dumps(
                    {"query": f"Query {i}", "limit": 2}, ensure_ascii=False)
            )
        )
        tasks.append(tool_manager.acall_tool(tool_call))

    # 并发执行所有任务
    print("并发调用 3 个异步工具...")
    results = await asyncio.gather(*tasks)

    for i, result in enumerate(results):
        print(
            f"结果 {i+1}: {json.dumps(json.loads(result['content']), ensure_ascii=False)}")

    print("✅ 并发异步调用成功")


# 运行异步演示
print("\n正在运行异步演示...")
try:
    asyncio.run(run_async_demo())
except Exception as e:
    print(f"❌ 异步演示失败: {e}")

print("\n" + "=" * 70)
print("演示完成！")
print("=" * 70)
