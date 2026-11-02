"""任务完成提示音：Agent 跑完一轮后，在宿主电脑上播放一个音效。

钩子：
  on_agent_begin(event, run_context)
  on_agent_done(event, run_context, response)
参考 astrbot/core/star/register/star_handler.py:503 / :531

音效：Windows 自带 wav，winsound 异步播放，不阻塞消息流。
"""
from __future__ import annotations

import os
import time

from astrbot.api import logger, AstrBotConfig
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

try:
    import winsound
except ImportError:  # 非 Windows 宿主，静默降级
    winsound = None

DEFAULT_WAV = r"C:\Windows\Media\Windows Notify System Generic.wav"


@register(
    "task_chime",
    "本地提示音",
    "Agent 完成一轮任务后，在宿主电脑播放提示音",
    "1.0.0",
)
class TaskChime(Star):
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        cfg = config or {}
        self.enabled: bool = bool(cfg.get("enable", True))
        self.wav_path: str = cfg.get("wav_path") or DEFAULT_WAV
        self.min_seconds: float = float(cfg.get("min_seconds", 8))
        self.cooldown: float = float(cfg.get("cooldown_seconds", 3))
        self.only_private: bool = bool(cfg.get("only_private", True))
        self._started_at: dict[str, float] = {}
        self._last_played: float = 0.0
        if self.wav_path and not os.path.exists(self.wav_path):
            logger.warning(f"[task_chime] 音效文件不存在，回退到系统提示音: {self.wav_path}")
            self.wav_path = ""

    def _play(self) -> None:
        if winsound is None:
            return
        if self.wav_path:
            winsound.PlaySound(self.wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)

    @filter.on_agent_begin()
    async def on_begin(self, event: AstrMessageEvent, run_context=None) -> None:
        try:
            umo = event.unified_msg_origin
        except Exception:
            umo = "_"
        self._started_at[umo] = time.monotonic()

    @filter.on_agent_done()
    async def on_done(self, event: AstrMessageEvent, run_context=None, response=None) -> None:
        if not self.enabled:
            return

        if self.only_private:
            try:
                if event.get_message_type().value != "FriendMessage":
                    return
            except Exception:
                pass

        try:
            umo = event.unified_msg_origin
        except Exception:
            umo = "_"
        started = self._started_at.pop(umo, None)
        elapsed = (time.monotonic() - started) if started else 0.0
        if elapsed < self.min_seconds:
            return

        now = time.monotonic()
        if now - self._last_played < self.cooldown:
            return
        self._last_played = now

        try:
            self._play()
            logger.info(f"[task_chime] 提示音已播放，本轮耗时 {elapsed:.1f}s")
        except Exception as exc:
            logger.warning(f"[task_chime] 播放失败: {exc}")
