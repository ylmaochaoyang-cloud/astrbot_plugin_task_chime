"""任务完成提示音：Agent 跑完一轮并真的把回复发出去后，在宿主电脑播放一个音效。

钩子：
  on_agent_begin(event, run_context)   —— 只用来记开始时刻
  after_message_sent(event, ...)       —— 只有回复真的发给用户时才响

为什么不再用 on_agent_done：那是"每一次 agent 运行"的钩子。主 Agent 结束会触发，
子代理（例如识屏、检索这类子程序）结束也会触发，而它们共用同一个事件对象。
结果是用户只发了一句话，提示音响了两三次。

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

#: 未走到发送就中断的事件不会自己清理，留个上限。
MAX_PENDING = 256
PENDING_TTL_SECONDS = 15 * 60


@register(
    "task_chime",
    "本地提示音",
    "Agent 完成一轮任务后，在宿主电脑播放提示音",
    "1.0.1",
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
        # 以事件对象为键：同一条用户消息，无论经过几次 agent 运行，只算一轮。
        self._started_at: dict[int, tuple[float, str]] = {}
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

    def _prune(self, now: float) -> None:
        if len(self._started_at) <= MAX_PENDING:
            return
        stale = [key for key, (started, _) in self._started_at.items()
                 if now - started > PENDING_TTL_SECONDS]
        for key in stale:
            self._started_at.pop(key, None)

    @filter.on_agent_begin()
    async def on_begin(self, event: AstrMessageEvent, run_context=None) -> None:
        now = time.monotonic()
        try:
            umo = event.unified_msg_origin
        except Exception:
            umo = "_"
        # 子代理也会进来，取最早的那次，别把计时重置成"刚刚开始"。
        self._started_at.setdefault(id(event), (now, umo))
        self._prune(now)

    @filter.after_message_sent()
    async def on_sent(self, event: AstrMessageEvent, *args, **kwargs) -> None:
        if not self.enabled:
            return

        entry = self._started_at.pop(id(event), None)
        if entry is None:
            # 没有对应的 agent 轮次：插件主动推送、群发提醒之类，不响。
            return
        started, _umo = entry
        elapsed = time.monotonic() - started

        if self.only_private:
            try:
                if event.get_message_type().value != "FriendMessage":
                    return
            except Exception:
                pass

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
