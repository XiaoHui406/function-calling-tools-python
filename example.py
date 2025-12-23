"""
集成演示脚本：展示工具注册、tools schema 生成、模型工具调用闭环。
"""
import os
from dotenv import load_dotenv
from agent_tool_manager import AgentToolManager
from openai.types.chat import ChatCompletionMessageFunctionToolCall
from pydantic import BaseModel, Field
from typing import Any
import json
from openai import OpenAI
from tool_registry import tool_manager

'''
以下是一个使用agent_tool_manager的例子
'''


class GetWeatherParams(BaseModel):
    """
    获取指定城市当前天气信息的输入参数。
    """
    city: str = Field(description='城市名称')
    unit: str = Field(default='celsius', description='温度单位，默认为摄氏度')


'''
一个被tool_manager.agent_tool装饰的function需满足以下条件：
1.传入参数只能是一个继承了BaseModel的类，这是为了使用BaseModel的model_json_schema()方法生成json schema
2.(可选)在function的开头使用(''''''，三引号)描述函数的功能，这段描述会用于生成tool的description
3.(可选)function的传入参数类中的属性使用Field填写description，这段描述会用于生成属性的description
'''


@tool_manager.agent_tool(InputClass=GetWeatherParams)
def get_current_weather(params: GetWeatherParams):
    """
    根据城市名称获取当前天气。
    """
    # 实际的函数逻辑（这里只是一个占位符）
    print(f"正在查询 {params.city} 的天气，单位为 {params.unit}。")
    return {"temperature": "25°C", "city": params.city}


print("\n------------- 测试tools生成 --------------")
print(json.dumps(tool_manager.generate_tools(), indent=4, ensure_ascii=False))

print("\n--- 测试函数调用（验证原函数功能未受影响）---")
print(get_current_weather(GetWeatherParams(city="北京")))


# 加载环境变量配置
load_dotenv()
api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")
model = os.getenv("MODEL")

# 检查必需的环境变量
if not api_key:
    raise ValueError("缺少环境变量 API_KEY，请在 .env 文件中配置")
if not base_url:
    raise ValueError("缺少环境变量 BASE_URL，请在 .env 文件中配置")
if not model:
    raise ValueError("缺少环境变量 MODEL，请在 .env 文件中配置")


def send_messages(messages):
    """
    发送消息到模型并附带已注册的 tools Schema，返回模型消息。
    """
    assert model is not None
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tool_manager.generate_tools()
        )
        return response.choices[0].message
    except Exception as e:
        print(f"❌ 调用模型失败: {e}")
        raise


# 创建 OpenAI 客户端
client = OpenAI(
    api_key=api_key,
    base_url=base_url,
)


def run_function_calling_test():
    """
    运行 function calling 完整测试流程。
    """
    print("\n========== Function Calling 测试流程 ==========")

    # 初始化对话消息
    messages: list[Any] = [
        {"role": "user", "content": "<function calling test> 39+186=? "}
    ]

    print(f"\n用户提问: {messages[0]['content']}")

    # 第一次调用：获取模型响应
    print("\n[步骤1] 发送消息到模型...")
    message = send_messages(messages)

    # 检查模型是否返回了工具调用
    if not message.tool_calls:
        print(f"\n模型直接回复（未使用工具）: {message.content}")
        return

    assert type(message.tool_calls[0]) is ChatCompletionMessageFunctionToolCall
    print(f"\n[步骤2] 模型请求调用工具: {message.tool_calls[0].function.name}")
    print(f"工具参数: {message.tool_calls[0].function.arguments}")

    # 执行工具调用
    tool: ChatCompletionMessageFunctionToolCall = message.tool_calls[0]
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
    print(f"\n✅ 模型最终回复: {message.content}")
    print("\n========== 测试完成 ==========\n")


if __name__ == "__main__":
    # 运行 function calling 测试
    run_function_calling_test()
