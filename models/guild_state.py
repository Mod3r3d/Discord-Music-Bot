"""
models/guild_state.py
---------------------
Quản lý trạng thái phát nhạc (FSM, Playback Generation, Queue Mutation Lock) cho từng Guild.
"""
import asyncio
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Deque, Dict, Optional, Set

from models.track import Track


class PlayerState(str, Enum):
    IDLE = "IDLE"
    RESOLVING = "RESOLVING"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    ERROR = "ERROR"


@dataclass
class GuildState:
    guild_id: int
    queue: Deque[Track] = field(default_factory=deque)
    current: Optional[Track] = None

    state: PlayerState = PlayerState.IDLE
    playback_generation: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    loop: bool = False
    random_mode: bool = False
    active_filter: Optional[str] = None
    filter_reapply: bool = False

    text_channel_id: Optional[int] = None
    dj_role_id: Optional[int] = None
    skip_votes: Set[int] = field(default_factory=set)

    _prefetch_task: Optional[asyncio.Task] = None
    _disconnect_task: Optional[asyncio.Task] = None

    def advance_generation(self) -> int:
        self.playback_generation += 1
        return self.playback_generation

    def clear_queue(self):
        self.queue.clear()
        self.current = None
        self.advance_generation()
        self.cancel_prefetch()

    def reset_skip_votes(self):
        self.skip_votes.clear()

    def cancel_prefetch(self):
        if self._prefetch_task and not self._prefetch_task.done():
            self._prefetch_task.cancel()
        self._prefetch_task = None

    def cancel_auto_disconnect(self):
        if self._disconnect_task and not self._disconnect_task.done():
            self._disconnect_task.cancel()
        self._disconnect_task = None


class GuildStateManager:
    def __init__(self):
        self._states: Dict[int, GuildState] = {}

    def get(self, guild_id: int) -> GuildState:
        if guild_id not in self._states:
            self._states[guild_id] = GuildState(guild_id=guild_id)
        return self._states[guild_id]

    def drop(self, guild_id: int):
        self._states.pop(guild_id, None)


guild_states = GuildStateManager()