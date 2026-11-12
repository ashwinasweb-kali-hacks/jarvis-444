"""JARVIS Tools package. Registers standard tools with default registry."""
from jarvis.tools.base import Tool, ToolRegistry, get_default_registry
from jarvis.tools.call import CallTool
from jarvis.tools.filesystem import ListDirTool, ProcessListTool, ReadFileTool, WriteFileTool
from jarvis.tools.globalfone import GlobalFoneCallTool
from jarvis.tools.network import NetworkStatusTool
from jarvis.tools.notes import ReadNoteTool, WriteNoteTool
from jarvis.tools.panels import ClosePanelTool, OpenPanelTool
from jarvis.tools.pc_automation import PCAutomationTool
from jarvis.tools.power import FormatDiskTool, ShutdownTool
from jarvis.tools.system_stats import SystemStatsTool

registry = get_default_registry()
registry.register(SystemStatsTool())
registry.register(OpenPanelTool())
registry.register(ClosePanelTool())
registry.register(ReadNoteTool())
registry.register(WriteNoteTool())
registry.register(NetworkStatusTool())
registry.register(ShutdownTool())
registry.register(FormatDiskTool())
registry.register(CallTool())
registry.register(GlobalFoneCallTool())
registry.register(PCAutomationTool())
registry.register(ReadFileTool())
registry.register(ListDirTool())
registry.register(WriteFileTool())
registry.register(ProcessListTool())

__all__ = [
    "Tool",
    "ToolRegistry",
    "get_default_registry",
    "SystemStatsTool",
    "OpenPanelTool",
    "ClosePanelTool",
    "ReadNoteTool",
    "WriteNoteTool",
    "NetworkStatusTool",
    "ShutdownTool",
    "FormatDiskTool",
    "CallTool",
    "GlobalFoneCallTool",
    "PCAutomationTool",
    "ReadFileTool",
    "ListDirTool",
    "WriteFileTool",
    "ProcessListTool",
]
