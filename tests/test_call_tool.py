from jarvis.tools.call import CallTool
from jarvis.brain import respond

def test_call_tool():
    tool = CallTool()
    res = tool.run(target="Tony Stark")
    assert res["target"] == "Tony Stark"
    assert res["encrypted"] is True
    assert "established" in res["message"].lower()

def test_brain_calling_intent():
    reply = respond("call my friend")
    assert "call" in reply.speech.lower() or "satellite" in reply.speech.lower()
    assert any(a["tool"] == "call" for a in reply.actions)

def test_brain_hang_up_intent():
    reply = respond("hang up")
    assert "terminated" in reply.speech.lower() or "closed" in reply.speech.lower()
    assert any(a["tool"] == "call" and a["args"].get("status") == "ended" for a in reply.actions)
