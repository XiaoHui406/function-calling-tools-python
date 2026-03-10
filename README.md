# Function Calling Tools

一个用于 OpenAI Function Calling 的轻量级 Python 工具库，提供自动工具注册、参数校验和工具调用管理功能。

> 🌐 **English Documentation Available**: [README_en.md](README_en.md)

## ✨ 核心功能

- 🎯 **装饰器式注册**：通过简单的装饰器将 Python 函数注册为 Function Calling 工具
- 📦 **自动工具发现**：自动扫描并加载指定包下的所有工具模块
- 🔒 **类型安全**：基于 Pydantic 自动生成和校验 OpenAI 所需的 JSON Schema
- 🚀 **零侵入设计**：装饰后的函数仍可独立调用，不影响原有逻辑
- 🔄 **调用闭环管理**：统一处理工具调用、参数解析和结果封装
- 🆕 **多种参数方式**：支持 Pydantic BaseModel、自动类型推导等多种参数定义方式
- ⚡ **异步支持**：提供 `acall_tool` 方法，支持异步函数和同步函数，同步函数在线程池中执行避免阻塞

## 📋 目录

- [如何集成到你的项目中](#-如何集成到你的项目中)
- [工具定义方式](#-工具定义方式)
- [核心概念](#-核心概念)
- [完整示例](#-完整示例)
- [项目结构](#-项目结构)
- [测试](#-测试)
- [API使用](#-api-使用)

## 🔌 如何集成到你的项目中

你可以轻松地将 Function Calling Tools 集成到现有项目中，只需简单几步：

### 1. 确保依赖

你的项目需要包含 `pydantic` 和 `openai` 两个库，且 `python>=3.9`：

```bash
pip install pydantic openai
```

### 2. 复制核心文件

将 `agent_tool_manager.py` 复制到你的项目目录中。

### 3. 开始使用

现在你就可以在项目中导入并使用工具管理器了
详细使用方式请继续看文档
使用示例请查看项目中的 `example.py`

## 🎯 工具定义方式

本库支持多种工具定义方式，从简单到灵活任你选择：

### 方式1：自动类型推导（最简单）

适用于不需要复杂参数校验的场景：

```python
from agent_tool_manager import AgentToolManager

tool_manager = AgentToolManager()

@tool_manager.agent_tool()  # 不传参数，自动推导
def calculate(a: int, b: int):
    """
    计算两个整数的和。
    """
    return {"result": a + b}

# 或使用默认值
@tool_manager.agent_tool()
def greet(name: str, message: str = "你好"):
    """
    向用户问候。
    """
    return {"greeting": f"{message}, {name}！"}
```

**优势：**

- 代码简洁，无需定义额外的类
- 系统根据类型注解自动生成 Pydantic 模型
- 支持所有标准 Python 类型（int, str, float, bool, list 等）

**要求：**

- 所有参数必须有类型注解

### 方式2：使用 Pydantic BaseModel（推荐，功能最全）

适用于需要复杂校验、文档说明的场景：

```python
from pydantic import BaseModel, Field
from agent_tool_manager import AgentToolManager

tool_manager = AgentToolManager()

class WeatherParams(BaseModel):
    """天气查询参数"""
    city: str = Field(description="城市名称", min_length=1)
    unit: str = Field(default="celsius", description="温度单位")

@tool_manager.agent_tool(InputClass=WeatherParams)
def get_weather(params: WeatherParams):
    """
    获取指定城市的天气信息。
    """
    return {"city": params.city, "temperature": "25°C"}
```

**优势：**

- 完整的 Pydantic 验证功能
- 可以添加字段描述（会反映到 JSON Schema）
- 支持复杂的嵌套结构

### 需要注意：

- ✅ 必须使用类型注解（推荐使用 Python 3.12+）
- ✅ 自动生成的 Pydantic 模型将使用最严格的验证规则
- ✅ 如需字段描述，请使用 Pydantic BaseModel 方式

## 🔍 核心概念

### AgentToolManager

工具管理器，是本库的核心类，负责：

- **工具注册**：通过 `@tool_manager.agent_tool()` 装饰器注册工具
- **Schema 生成**：调用 `generate_tools()` 生成符合 OpenAI 格式的工具列表
- **工具调用**：使用 `call_tool()` 或 `await acall_tool()` 执行模型返回的工具调用请求

### 工作流程

```
1. 定义工具 → 使用装饰器注册函数
2. 生成 Schema → tool_manager.generate_tools()
3. 调用模型 → 将 Schema 传递给 OpenAI API
4. 执行工具 → tool_manager.call_tool(tool_call) 或 await tool_manager.acall_tool(tool_call)
5. 返回结果 → 将工具结果回传给模型
```

### 同步 vs 异步调用

本库支持两种工具调用方式：

- **`call_tool()`** - 同步调用，适用于传统同步代码
- **`acall_tool()`** - 异步调用，支持异步函数和同步函数

**`acall_tool()` 的特点：**

- 自动检测函数类型（协程函数或同步函数）
- 协程函数：直接 `await` 调用
- 同步函数：在 `asyncio.to_thread()` 中运行，避免阻塞事件循环
- 返回值与 `call_tool()` 相同

## 💡 完整示例

### 基本工具调用流程

```python
from agent_tool_manager import AgentToolManager
from openai import OpenAI

tool_manager = AgentToolManager()

# 初始化 OpenAI 客户端
client = OpenAI(api_key="your_key", base_url="your_base_url")

# 准备消息
messages = [
    {"role": "user", "content": "帮我计算 123 + 456"}
]

# 调用模型并传入工具
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    tools=tool_manager.generate_tools()  # 自动生成所有已注册工具的 schema
)

# 检查是否有工具调用
message = response.choices[0].message
if message.tool_calls:
    tool_call = message.tool_calls[0]

    # 执行工具
    result = tool_manager.call_tool(tool_call)

    # 将结果返回给模型
    messages.append(message)
    messages.append(result)

    # 获取最终回复
    final_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    print(final_response.choices[0].message.content)
```

### 查看已注册的工具

```python
import json
from agent_tool_manager import AgentToolManager

tool_manager = AgentToolManager()

# 查看所有工具的 JSON Schema
tools = tool_manager.generate_tools()
print(json.dumps(tools, indent=2, ensure_ascii=False))
```

### 异步工具调用示例

```python
import asyncio
from agent_tool_manager import AgentToolManager
from openai import AsyncOpenAI
tool_manager = AgentToolManager()

# 初始化异步 OpenAI 客户端
client = AsyncOpenAI(api_key="your_key", base_url="your_base_url")

# 定义工具
@tool_manager.agent_tool()
def sync_calc(a: int, b: int):
    """同步计算工具"""
    return a + b

@tool_manager.agent_tool()
async def async_search(query: str):
    """异步搜索工具"""
    # 模拟异步操作
    await asyncio.sleep(0.1)
    return {"results": f"Search results for: {query}"}

async def main():
    messages = [{"role": "user", "content": "搜索 Python 教程"}]

    # 调用模型
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tool_manager.generate_tools()
    )

    message = response.choices[0].message
    if message.tool_calls:
        tool_call = message.tool_calls[0]

        # 异步执行工具（自动处理同步和异步函数）
        result = await tool_manager.acall_tool(tool_call)

        messages.append(message)
        messages.append(result)

        final_response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        print(final_response.choices[0].message.content)

# 运行
asyncio.run(main())
```

**注意：** `acall_tool()` 会自动检测函数类型：

- 如果是异步函数（使用 `async def`），会直接 `await` 调用
- 如果是同步函数，会在后台线程中执行，避免阻塞事件循环

### 完整集成示例

查看 [`example.py`](example.py) 了解完整的集成示例：

```bash
python example.py
```

## 📁 项目结构

```
function-calling-tools-python/
├── agent_tool_manager.py    # 核心工具管理器
├── tool_registry.py          # 全局工具注册入口
├── agent_tools/              # 工具模块目录
│   └── math_tools/
│       └── math_tools.py     # 示例：数学运算工具
├── example.py                # 完整示例脚本
├── test/                     # 单元测试目录
├── pyproject.toml            # 项目配置
├── .env                      # 环境变量（需自行创建）
└── README.md                 # 项目文档
```

## 🧪 测试

本项目使用 pytest 进行单元测试，确保核心功能的稳定性。

### 运行测试

```bash
# 运行所有测试
pytest test/

# 运行所有测试并显示详细信息
pytest test/ -v

# 运行特定测试文件
pytest test/test_agent_tool_manager.py
```

### 测试覆盖

测试覆盖了以下核心功能：

- 工具注册逻辑（重复注册、装饰器功能）
- Schema 生成（带/不带文档字符串）
- 工具调用执行（参数解析、返回值处理、异常情况）
- **异步工具调用 `acall_tool`（支持协程函数和同步函数）**
- 嵌套对象支持
- 多 manager 实例独立性
- 全局 tool_manager 自动加载
- 自动类型推导（新增）

## 📚 API 使用

### 核心 API

#### `AgentToolManager`

```python
from agent_tool_manager import AgentToolManager

# 创建管理器实例
manager = AgentToolManager()
```

**主要方法：**

| 方法                                              | 说明                                     | 返回值                                  |
| ------------------------------------------------- | ---------------------------------------- | --------------------------------------- |
| `agent_tool(InputClass=None)`                     | 装饰器，注册函数为工具。InputClass 可选  | 装饰器函数                              |
| `generate_tools()`                                | 生成所有工具的 JSON Schema               | `list[ChatCompletionFunctionToolParam]` |
| `call_tool(tool_call)`                            | 同步执行工具调用并封装结果               | `ChatCompletionToolMessageParam`        |
| `acall_tool(tool_call)`                           | 异步执行工具调用，支持协程函数和同步函数 | `ChatCompletionToolMessageParam`        |
| `_create_model_from_type_hints(func, model_name)` | 私有方法：从类型注解生成模型             | `Type[BaseModel]`                       |

### 独立工具方法

除了AgentToolManager的核心方法外，还有两个重要的独立工具方法：

#### `load_tools(package_name)`

自动扫描并批量导入指定包下的所有工具模块。

```python
from agent_tool_manager import load_tools

# 自动加载 agent_tools 包下的所有工具模块
load_tools("agent_tools")
```

**特点：**

- 递归扫描包及其子包中的所有 `.py` 文件
- 自动忽略 `__pycache__` 目录和 `__init__.py` 文件
- 触发模块导入时的装饰器注册逻辑
- 工具会注册到模块中指定的AgentToolManager实例

#### `merge_managers(tool_managers)`

合并多个工具管理器，返回一个新的工具管理器实例。

```python
from agent_tool_manager import merge_managers, AgentToolManager
tool_manager = AgentToolManager()

# 创建其他工具管理器
other_manager = AgentToolManager()

# 合并多个管理器
merged_manager = merge_managers([tool_manager, other_manager])

# 使用合并后的管理器
tools = merged_manager.generate_tools()
```

**特点：**

- 自动去重，确保工具名称唯一
- 返回完整的 `AgentToolManager` 实例，支持所有管理器功能
- 可以继续注册新工具到合并后的管理器
- 适合需要完整管理器功能的场景

## 📄 许可证

MIT License

## 🔗 相关资源

- [OpenAI Function Calling 文档](https://platform.openai.com/docs/guides/function-calling)
- [Pydantic 文档](https://docs.pydantic.dev/)
- [Python dotenv 文档](https://github.com/theskumar/python-dotenv)

---

**提示**：如果遇到问题，请检查：

1. ✅ 环境变量是否正确配置
2. ✅ Python 版本是否 >= 3.12
3. ✅ 所有依赖是否正确安装
4. ✅ API 密钥是否有效且有足够额度
