from jarvis.tools.pc_automation import PCAutomationTool
from jarvis.brain import respond

def test_pc_automation_tool_registered():
    tool = PCAutomationTool()
    assert tool.name == "pc_automation"
    assert tool.risk == "safe"

def test_brain_automation_intents():
    reply = respond("open notepad")
    assert "notepad" in reply.speech.lower()
    assert any(a["tool"] == "pc_automation" and a["args"].get("target") == "notepad" for a in reply.actions)

    reply_calc = respond("open calculator")
    assert "calculator" in reply_calc.speech.lower()
    assert any(a["tool"] == "pc_automation" and a["args"].get("target") == "calc" for a in reply_calc.actions)

    reply_vol = respond("volume up")
    assert "volume" in reply_vol.speech.lower()
    assert any(a["tool"] == "pc_automation" and a["args"].get("action") == "volume_up" for a in reply_vol.actions)
