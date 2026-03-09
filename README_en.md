# Function Calling Tools

A lightweight Python toolkit for OpenAI Function Calling, providing automatic tool registration, parameter validation, and tool invocation management.

## ✨ Core Features

- 🎯 **Decorator-based Registration**: Register Python functions as Function Calling tools via simple decorators
- 📦 **Automatic Tool Discovery**: Automatically scan and load all tool modules in specified packages
- 🔒 **Type Safety**: Automatically generate and validate OpenAI-compatible JSON Schema based on Pydantic
- 🚀 **Zero-Intrusion Design**: Decorated functions can still be called independently without affecting original logic
- 🔄 **Closed-Loop Invocation Management**: Unified handling of tool calls, parameter parsing, and result encapsulation
- 🆕 **Multiple Parameter Styles**: Support for Pydantic BaseModel, automatic type inference, and more
- ⚡ **Async Support**: Provides `acall_tool` method supporting both async and sync functions, with sync functions executed in thread pool to avoid blocking

## 📋 Table of Contents

- [How to Integrate into Your Project](#-how-to-integrate-into-your-project)
- [Tool Definition Styles](#-tool-definition-styles)
- [Core Concepts](#-core-concepts)
- [Complete Example](#-complete-example)
- [Project Structure](#-project-structure)
- [Testing](#-testing)
- [API Usage](#-api-usage)

## 🔌 How to Integrate into Your Project

You can easily integrate Function Calling Tools into your existing project with just a few simple steps:

### 1. Ensure Dependencies

Your project needs to include `pydantic` and `openai` libraries, and `python>=3.9`:

```bash
pip install pydantic openai
```

### 2. Copy Core Files

Copy `agent_tool_manager.py` to your project directory.

### 3. Start Using

Now you can import and use the tool manager in your project.
For detailed usage, please continue reading the documentation.
For usage examples, please refer to `example.py` in the project.

## 🎯 Tool Definition Styles

This library supports multiple tool definition styles, from simple to flexible:

### Style 1: Automatic Type Inference (Simplest)

For scenarios without complex parameter validation:

```python
from agent_tool_manager import AgentToolManager

tool_manager = AgentToolManager()

@tool_manager.agent_tool()  # No parameters, automatic inference
def calculate(a: int, b: int):
    """
    Calculate the sum of two integers.
    """
    return {"result": a + b}

# Or with default values
@tool_manager.agent_tool()
def greet(name: str, message: str = "Hello"):
    """
    Greet a user.
    """
    return {"greeting": f"{message}, {name}!"}
```

**Advantages:**

- Concise code, no need to define extra classes
- System automatically generates Pydantic models based on type annotations
- Supports all standard Python types (int, str, float, bool, list, etc.)

**Requirements:**

- All parameters must have type annotations

### Style 2: Using Pydantic BaseModel (Recommended, Full-Featured)

For scenarios requiring complex validation and documentation:

```python
from pydantic import BaseModel, Field
from agent_tool_manager import AgentToolManager

tool_manager = AgentToolManager()

class WeatherParams(BaseModel):
    """Weather query parameters"""
    city: str = Field(description="City name", min_length=1)
    unit: str = Field(default="celsius", description="Temperature unit")

@tool_manager.agent_tool(InputClass=WeatherParams)
def get_weather(params: WeatherParams):
    """
    Get weather information for a specified city.
    """
    return {"city": params.city, "temperature": "25°C"}
```

**Advantages:**

- Complete Pydantic validation capabilities
- Can add field descriptions (reflected in JSON Schema)
- Supports complex nested structures

### Notes:

- ✅ Must use type annotations (Python 3.12+ recommended)
- ✅ Automatically generated Pydantic models use strictest validation rules
- ✅ For field descriptions, use the Pydantic BaseModel style

## 🔍 Core Concepts

### AgentToolManager

The tool manager is the core class of this library, responsible for:

- **Tool Registration**: Register functions as tools via `@tool_manager.agent_tool()` decorator
- **Schema Generation**: Call `generate_tools()` to generate OpenAI-compatible tool list
- **Tool Invocation**: Use `call_tool()` or `await acall_tool()` to execute tool calls from model

### Workflow

```
1. Define Tools → Use decorators to register functions
2. Generate Schema → tool_manager.generate_tools()
3. Call Model → Pass Schema to OpenAI API
4. Execute Tools → tool_manager.call_tool(tool_call) or await tool_manager.acall_tool(tool_call)
5. Return Results → Pass tool results back to model
```

### Sync vs Async Invocation

This library supports two tool invocation methods:

- **`call_tool()`** - Synchronous call, suitable for traditional synchronous code
- **`acall_tool()`** - Asynchronous call, supports both async and sync functions

**Features of `acall_tool()`:**

- Automatically detects function type (coroutine function or sync function)
- Coroutine functions: directly `await` call
- Sync functions: run in `asyncio.to_thread()` to avoid blocking event loop
- Same return value as `call_tool()`

## 💡 Complete Example

### Basic Tool Calling Flow

```python
from agent_tool_manager import AgentToolManager
from openai import OpenAI

tool_manager = AgentToolManager()

# Initialize OpenAI client
client = OpenAI(api_key="your_key", base_url="your_base_url")

# Prepare messages
messages = [
    {"role": "user", "content": "Help me calculate 123 + 456"}
]

# Call model with tools
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    tools=tool_manager.generate_tools()  # Auto-generate schema for all registered tools
)

# Check if tool calls exist
message = response.choices[0].message
if message.tool_calls:
    tool_call = message.tool_calls[0]

    # Execute tool
    result = tool_manager.call_tool(tool_call)

    # Return result to model
    messages.append(message)
    messages.append(result)

    # Get final response
    final_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    print(final_response.choices[0].message.content)
```

### View Registered Tools

```python
import json
from agent_tool_manager import AgentToolManager

tool_manager = AgentToolManager()

# View JSON Schema for all tools
tools = tool_manager.generate_tools()
print(json.dumps(tools, indent=2, ensure_ascii=False))
```

### Async Tool Calling Example

```python
import asyncio
from agent_tool_manager import AgentToolManager
from openai import AsyncOpenAI

tool_manager = AgentToolManager()

# Initialize async OpenAI client
client = AsyncOpenAI(api_key="your_key", base_url="your_base_url")

# Define tools
@tool_manager.agent_tool()
def sync_calc(a: int, b: int):
    """Synchronous calculation tool"""
    return a + b

@tool_manager.agent_tool()
async def async_search(query: str):
    """Asynchronous search tool"""
    # Simulate async operation
    await asyncio.sleep(0.1)
    return {"results": f"Search results for: {query}"}

async def main():
    messages = [{"role": "user", "content": "Search for Python tutorials"}]

    # Call model
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tool_manager.generate_tools()
    )

    message = response.choices[0].message
    if message.tool_calls:
        tool_call = message.tool_calls[0]

        # Execute tool async (automatically handles sync and async functions)
        result = await tool_manager.acall_tool(tool_call)

        messages.append(message)
        messages.append(result)

        final_response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        print(final_response.choices[0].message.content)

# Run
asyncio.run(main())
```

**Note:** `acall_tool()` automatically detects function types:

- If async function (using `async def`), directly `await` call
- If sync function, runs in background thread to avoid blocking event loop

### Full Integration Example

See [`example.py`](example.py) for a complete integration example:

```bash
python example.py
```

## 📁 Project Structure

```
function-call-tools/
├── agent_tool_manager.py     # Core tool manager
├── tool_registry.py          # Global tool registration entry
├── agent_tools/              # Tool modules directory
│   └── math_tools/
│       └── math_tools.py     # Example: Math operations tools
├── example.py                # Complete example script
├── test/                     # Unit tests directory
├── pyproject.toml            # Project configuration
├── .env                      # Environment variables (create yourself)
└── README.md                 # Project documentation
```

## 🧪 Testing

This project uses pytest for unit testing to ensure core functionality stability.

### Running Tests

```bash
# Run all tests
pytest test/

# Run all tests with verbose output
pytest test/ -v

# Run specific test file
pytest test/test_agent_tool_manager.py
```

### Test Coverage

Tests cover the following core features:

- Tool registration logic (duplicate registration, decorator functionality)
- Schema generation (with/without docstrings)
- Tool invocation execution (parameter parsing, return value handling, exceptions)
- **Async tool invocation `acall_tool` (supports coroutine and sync functions)**
- Nested object support
- Multiple manager instance independence
- Global tool_manager auto-loading
- Automatic type inference (new)

## 📚 API Usage

### Core API

#### `AgentToolManager`

```python
from agent_tool_manager import AgentToolManager

# Create manager instance
manager = AgentToolManager()
```

**Main Methods:**

| Method                                            | Description                                                             | Return Value                            |
| ------------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------- |
| `agent_tool(InputClass=None)`                     | Decorator to register function as tool; InputClass optional             | Decorator function                      |
| `generate_tools()`                                | Generate JSON Schema for all tools                                      | `list[ChatCompletionFunctionToolParam]` |
| `call_tool(tool_call)`                            | Synchronously execute tool call and encapsulate result                  | `ChatCompletionToolMessageParam`        |
| `acall_tool(tool_call)`                           | Asynchronously execute tool call, supports coroutine and sync functions | `ChatCompletionToolMessageParam`        |
| `_create_model_from_type_hints(func, model_name)` | Private method: generate model from type hints                          | `Type[BaseModel]`                       |

### Standalone Tool Methods

In addition to AgentToolManager's core methods, there are two important standalone tool methods:

#### `load_tools(package_name)`

Automatically scan and batch import all tool modules in specified package.

```python
from agent_tool_manager import load_tools

# Auto-load all tool modules under agent_tools package
load_tools("agent_tools")
```

**Features:**

- Recursively scan package and all subpackages for `.py` files
- Auto-ignore `__pycache__` directories and `__init__.py` files
- Trigger decorator registration logic during module import
- Tools register to specified AgentToolManager instance in module

#### `merge_managers(tool_managers)`

Merge multiple tool managers and return a new tool manager instance.

```python
from agent_tool_manager import merge_managers, AgentToolManager

tool_manager = AgentToolManager()

# Create other tool managers
other_manager = AgentToolManager()

# Merge multiple managers
merged_manager = merge_managers([tool_manager, other_manager])

# Use merged manager
tools = merged_manager.generate_tools()
```

**Features:**

- Auto-deduplication to ensure unique tool names
- Returns complete `AgentToolManager` instance supporting all manager features
- Can continue registering new tools to merged manager
- Suitable for scenarios requiring full manager functionality

**Difference from `merge_tools`:**

- `merge_tools`: Returns tool list, suitable for direct API calls
- `merge_managers`: Returns manager instance, suitable for scenarios requiring continued manager operations

### Using Global Instance

For convenience, it's recommended to use the global singleton via `tool_registry`:

```python
from agent_tool_manager import AgentToolManager

tool_manager = AgentToolManager()

# Style 1: Auto-create parameter model (new, simplest)
@tool_manager.agent_tool()
def auto_tool(a: int, b: str):
    """Auto mode"""
    pass

# Style 2: Manually specify BaseModel (original, most powerful)
class MyInput(BaseModel):
    name: str

@tool_manager.agent_tool(InputClass=MyInput)
def manual_tool(params: MyInput):
    """Manual mode"""
    pass
```

## 📄 License

MIT License

## 🔗 Related Resources

- [OpenAI Function Calling Documentation](https://platform.openai.com/docs/guides/function-calling)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Python dotenv Documentation](https://github.com/theskumar/python-dotenv)

---

**Tips:** If you encounter issues, please check:

1. ✅ Environment variables are correctly configured
2. ✅ Python version is >= 3.12
3. ✅ All dependencies are correctly installed
4. ✅ API key is valid and has sufficient quota
