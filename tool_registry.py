"""
工具注册入口：提供全局唯一的 tool_manager，并在导入时加载 agent_tools 包下的工具模块。
"""
from agent_tool_manager import AgentToolManager

# 创建全局唯一的实例
tool_manager = AgentToolManager()

# 自动扫描并加载根目录下 agent_tools 目录中的工具模块
# 可以修改为其他目录
tool_manager.load_tools("agent_tools")
