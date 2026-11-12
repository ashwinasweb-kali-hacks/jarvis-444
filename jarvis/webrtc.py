"""Lightweight WebRTC signaling room.

In-memory store so two browsers (PC + tablet + glasses) can exchange SDP offers
and ICE candidates to set up a real peer-to-peer audio call. This daemon does
not proxy media — once the peers have each other's SDP, the browsers connect
directly via WebRTC RTCPeerConnection.

Rooms expire after 30 minutes of inactivity to keep memory bounded.
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Dict, Optional

_ROOMS: Dict[str, Dict[str, Any]] = {}
_ROOM_TTL_SEC = 30 * 60


def _now() -> float:
    return time.time()


def _gc() -> None:
    dead = [r for r, d in _ROOMS.items() if _now() - d["updated"] > _ROOM_TTL_SEC]
    for r in dead:
        del _ROOMS[r]


def signal_room(
    room: str,
    peer: str,
    *,
    sdp: Optional[Dict[str, Any]] = None,
    candidate: Optional[Dict[str, Any]] = None,
    get_state: bool = False,
) -> Dict[str, Any]:
    """Post or retrieve signaling state for a room.

    Returns the full peer state of the room after the update.
    """
    _gc()
    state = _ROOMS.setdefault(
        room,
        {"updated": _now(), "peers": {}, "messages": []},
    )
    state["updated"] = _now()

    if get_state:
        return {
            "room": room,
            "peers": state["peers"],
            "messages": state["messages"][-50:],
        }

    peer_state = state["peers"].setdefault(
        peer, {"joined": _now(), "sdp": None, "candidates": []}
    )
    peer_state["updated"] = _now()

    if sdp is not None:
        peer_state["sdp"] = sdp
        state["messages"].append(
            {"t": _now(), "peer": peer, "type": "sdp", "sdp": sdp}
        )

    if candidate is not None:
        peer_state["candidates"].append(candidate)
        state["messages"].append(
            {"t": _now(), "peer": peer, "type": "candidate", "candidate": candidate}
        )

    return {
        "room": room,
        "peers": state["peers"],
        "messages": state["messages"][-50:],
    }


def list_rooms() -> Dict[str, Any]:
    _gc()
    return {
        "rooms": [
            {
                "room": r,
                "peers": list(d["peers"].keys()),
                "updated": d["updated"],
            }
            for r, d in _ROOMS.items()
        ]
    }


__all__ = ["signal_room", "list_rooms"]
