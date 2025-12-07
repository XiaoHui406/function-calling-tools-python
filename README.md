# Function Calling Tools

一个用于 OpenAI Function Calling 的轻量级 Python 工具库，提供自动工具注册、参数校验和工具调用管理功能。

## ✨ 核心功能

- 🎯 **装饰器式注册**：通过简单的装饰器将 Python 函数注册为 Function Calling 工具
- 📦 **自动工具发现**：自动扫描并加载指定包下的所有工具模块
- 🔒 **类型安全**：基于 Pydantic 自动生成和校验 OpenAI 所需的 JSON Schema
- 🚀 **零侵入设计**：装饰后的函数仍可独立调用，不影响原有逻辑
- 🔄 **调用闭环管理**：统一处理工具调用、参数解析和结果封装

## 📋 目录

- [安装](#安装)
- [快速开始](#快速开始)
- [核心概念](#核心概念)
- [API 使用](#api-使用)
- [工具定义](#工具定义)
- [完整示例](#完整示例)
- [项目结构](#项目结构)

## 🚀 安装

### 环境要求

- Python >= 3.12

### 使用 uv（推荐）

```bash
# 克隆仓库
git clone https://github.com/XiaoHui406/function-calling-tools-python.git
cd function-call-tools-python

# 使用 uv 安装依赖
uv sync
```

### 使用 pip

```bash
# 克隆仓库
git clone https://github.com/XiaoHui406/function-calling-tools-python.git
cd function-call-tools-python

# 安装依赖
pip install -e .
```

## ⚡ 快速开始

### 1. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
API_KEY=your_openai_api_key
BASE_URL=https://api.openai.com/v1
MODEL=gpt-4o-mini
```

### 2. 运行示例

```bash
python test.py
```

示例输出：

```
========== Function Calling 测试流程 ==========

用户提问: <function calling test> 39+186=?

[步骤1] 发送消息到模型...

[步骤2] 模型请求调用工具: add
工具参数: {"a": 39, "b": 186}

[步骤3] 执行工具调用...
工具执行结果: 225

[步骤4] 将工具结果返回给模型...

✅ 模型最终回复: 39 + 186 = 225

========== 测试完成 ==========
```

## 🔍 核心概念

### AgentToolManager

工具管理器，是本库的核心类，负责：

- **工具注册**：通过 `@tool_manager.agent_tool()` 装饰器注册工具
- **Schema 生成**：调用 `generate_tools()` 生成符合 OpenAI 格式的工具列表
- **工具调用**：使用 `call_tool()` 执行模型返回的工具调用请求
- **自动加载**：通过 `load_tools()` 批量导入工具模块

### 工作流程

```
1. 定义工具 → 使用 Pydantic 定义参数 + 装饰器注册
2. 生成 Schema → tool_manager.generate_tools()
3. 调用模型 → 将 Schema 传递给 OpenAI API
4. 执行工具 → tool_manager.call_tool(tool_call)
5. 返回结果 → 将工具结果回传给模型
```

## 📁 项目结构

```
function-call-tools/
├── agent_tool_manager.py    # 核心工具管理器
├── tool_registry.py          # 全局工具注册入口
├── agent_tools/              # 工具模块目录
│   └── math_tools/
│       └── math_tools.py     # 示例：数学运算工具
├── test.py                   # 完整示例与测试
├── pyproject.toml            # 项目配置
├── .env                      # 环境变量（需自行创建）
└── README.md                 # 项目文档
```

## 🛠️ 工具定义

### 步骤 1：创建工具模块

在 `agent_tools/` 目录下创建你的工具模块（支持嵌套子目录）。

### 步骤 2：定义参数模型

使用 Pydantic 的 `BaseModel` 定义工具的输入参数：

```python
from pydantic import BaseModel, Field

class CalculateInput(BaseModel):
    """计算工具的输入参数"""
    expression: str = Field(description="要计算的数学表达式")
```

### 步骤 3：使用装饰器注册工具

```python
from tool_registry import tool_manager

@tool_manager.agent_tool(InputClass=CalculateInput)
def calculate(params: CalculateInput):
    """
    计算数学表达式的值。
    """
    result = eval(params.expression)  # 生产环境请使用安全的计算方法
    return {"result": result}
```

### 工具定义规范

1. **参数类型**：函数参数必须是继承自 `BaseModel` 的类
2. **函数文档**：使用 docstring 描述工具功能（会作为 tool description）
3. **字段描述**：使用 `Field(description=...)` 描述参数含义
4. **返回值**：返回可 JSON 序列化的数据（dict、str、int 等）

### 完整示例

查看 [`agent_tools/math_tools/math_tools.py`](agent_tools/math_tools/math_tools.py) 了解完整示例。

## 💡 完整示例

### 基本工具调用流程

```python
from tool_registry import tool_manager
from openai import OpenAI

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
from tool_registry import tool_manager

# 查看所有工具的 JSON Schema
tools = tool_manager.generate_tools()
print(json.dumps(tools, indent=2, ensure_ascii=False))
```

## 🔧 环境配置

### 必需的环境变量

在 `.env` 文件中配置以下变量：

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `API_KEY` | OpenAI API 密钥 | `sk-xxx...` |
| `BASE_URL` | API 基础 URL | `https://api.openai.com/v1` |
| `MODEL` | 使用的模型名称 | `gpt-4o-mini` |

### 示例 .env 文件

```env
API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx
BASE_URL=https://api.openai.com/v1
MODEL=gpt-4o-mini
```

## 📚 API 使用

### 核心 API

#### `AgentToolManager`

```python
from agent_tool_manager import AgentToolManager

# 创建管理器实例
manager = AgentToolManager()
```

**主要方法**：

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `agent_tool(InputClass)` | 装饰器，注册函数为工具 | 装饰器函数 |
| `generate_tools()` | 生成所有工具的 JSON Schema | `list[ChatCompletionFunctionToolParam]` |
| `call_tool(tool_call)` | 执行工具调用并封装结果 | `ChatCompletionToolMessageParam` |
| `load_tools(package_name)` | 自动扫描并加载工具模块 | `None` |

### 使用全局实例

为了方便使用，建议通过 `tool_registry` 使用全局单例：

```python
from tool_registry import tool_manager

# 直接使用预配置的全局实例
@tool_manager.agent_tool(InputClass=MyInput)
def my_tool(params: MyInput):
    pass
```

### 自动加载机制

`tool_registry.py` 在导入时会自动执行 `load_tools("agent_tools")`，递归扫描并导入该包下的所有 `.py` 文件（排除 `__init__.py`），触发工具注册。

### 添加新工具的步骤

1. 在 `agent_tools/` 下创建工具模块（支持嵌套目录）
2. 定义继承 `BaseModel` 的参数类
3. 使用 `@tool_manager.agent_tool` 装饰器
4. 编写清晰的 docstring（作为工具描述）
5. 返回可 JSON 序列化的数据

### 运行示例

```bash
# 查看完整的 function calling 调用流程
python test.py
```

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
