"""
Function calling 工具管理器：封装工具注册、schema 生成、调用与自动加载。
"""
import importlib
import os
from pydantic import BaseModel, Field
from typing import Callable, Type
from openai.types.chat import ChatCompletionMessageFunctionToolCall, ChatCompletionFunctionToolParam, ChatCompletionToolMessageParam
from openai.types.shared_params import FunctionDefinition
import json


class AgentTool(BaseModel):
    '''
    func: 加入function_calling的函数，其传入的参数中只能是一个继承了BaseModel的类
    InputClass: 继承BaseModel的传入参数类
    '''
    func: Callable
    InputClass: Type[BaseModel]

    def to_json_schema(self) -> ChatCompletionFunctionToolParam:
        name = self.func.__name__
        description = self.func.__doc__.strip(
        ) if self.func.__doc__ else f'调用函数{self.func.__name__}'
        parameters = self.InputClass.model_json_schema()

        return ChatCompletionFunctionToolParam(
            type='function',
            function=FunctionDefinition(
                name=name, description=description, parameters=parameters)
        )


class AgentToolManager:
    """
    工具管理器：提供工具注册、schema 生成、工具调用和自动加载。
    - agent_tool: 将函数注册为工具，保持原函数可调用
    - generate_tools: 生成 OpenAI tools 所需的 JSON Schema
    - call_tool: 解析 tool_calls，实例化参数模型并调用函数，返回工具消息
    - load_tools: 扫描并动态导入指定包下的工具模块
    """

    def __init__(self):
        self.tool_name_list: list[str] = []
        self.tool_map: dict[str, AgentTool] = {}

    def agent_tool(self, InputClass: Type[BaseModel]):
        """
        装饰器：注册函数为工具。要求函数参数为继承 BaseModel 的类，用于自动生成 JSON Schema。
        返回原函数以保持调用不变。
        """
        def decorator(func: Callable):
            tool_name: str = func.__name__
            if func.__name__ in self.tool_name_list:
                raise ValueError(
                    f"Tool name conflict：名为 '{tool_name}' 的tool已被注册。请重命名该function或确保tool名称唯一。"
                )
            tool: AgentTool = AgentTool(func=func, InputClass=InputClass)
            self.tool_map[func.__name__] = tool
            self.tool_name_list.append(tool_name)
            return func
        return decorator

    def generate_tools(self) -> list[ChatCompletionFunctionToolParam]:
        """
        将已注册的工具转换为 OpenAI Chat Completions 的 tools 参数结构。
        """
        tools: list[ChatCompletionFunctionToolParam] = []
        for (name, tool) in self.tool_map.items():
            tools.append(tool.to_json_schema())
        return tools

    def call_tool(self, tool_call: ChatCompletionMessageFunctionToolCall) -> ChatCompletionToolMessageParam:
        """
        执行模型返回的工具调用：解析参数、实例化 Pydantic 模型、调用函数并封装为 tool 消息。
        """
        tool_call_id, tool_name, arguments = tool_call.id, tool_call.function.name, json.loads(
            tool_call.function.arguments)

        if tool_name not in self.tool_name_list:
            raise ValueError(
                f"Tool not found：未发现名为 '{tool_name}' 的tool"
            )

        func, InputClass = self.tool_map[tool_name].func, self.tool_map[tool_name].InputClass

        tool_args = InputClass(**arguments)
        content = func(tool_args)

        tool_callback: ChatCompletionToolMessageParam = ChatCompletionToolMessageParam(
            role='tool', tool_call_id=tool_call_id, content=json.dumps(content, ensure_ascii=False))
        return tool_callback

    def load_tools(self, package_name: str):
        """
        扫描并动态导入指定基础包下的子模块，自动注册工具。忽略 __pycache__ 与 __init__.py。
        """
        try:
            # 1. 基础导入：先找到顶层包的位置
            # 例如导入 'agent_tools'，获取它的物理路径
            base_package = importlib.import_module(package_name)
            # package.__path__ 是一个列表，通常取第一个路径
            if not hasattr(base_package, "__path__"):
                return  # 如果是单文件而非包，直接返回（因为上面import_module已经加载了）

            base_path = base_package.__path__[0]

        except ImportError as e:
            raise ValueError(f"无法导入基础包 '{package_name}': {e}")

        print(f"--- 开始扫描工具目录: {base_path} ---")

        # 2. 使用 os.walk 遍历物理文件系统
        for root, dirs, files in os.walk(base_path):
            # 忽略 __pycache__ 目录
            if '__pycache__' in dirs:
                dirs.remove('__pycache__')

            for file in files:
                if file.endswith(".py") and file != "__init__.py":
                    # 3. 构造模块路径
                    # 算出当前文件相对于基础包的相对路径
                    # 例如: root='/.../agent_tools/math_tools', base_path='/.../agent_tools'
                    # rel_path = 'math_tools'
                    rel_path = os.path.relpath(root, base_path)

                    if rel_path == ".":
                        # 文件就在 agent_tools 根目录下
                        module_name = f"{package_name}.{file[:-3]}"
                    else:
                        # 文件在子目录中，需要把路径分隔符 (/) 换成点 (.)
                        # Windows下是 \, Linux下是 /，os.path.sep 自动处理
                        sub_package = rel_path.replace(os.path.sep, ".")
                        module_name = f"{package_name}.{sub_package}.{file[:-3]}"

                    # 4. 动态导入
                    try:
                        importlib.import_module(module_name)
                        print(f"✅ 成功加载模块: {module_name}")
                    except Exception as e:
                        print(f"❌ 加载模块 '{module_name}' 失败: {e}")
