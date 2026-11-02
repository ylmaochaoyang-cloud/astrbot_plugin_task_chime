# 本地提示音 · astrbot_plugin_task_chime

Agent 跑完一轮任务后，在你**自己这台电脑**上响一声。

不是给聊天对象听的通知音，是给你听的。你让 AI 去查资料、跑脚本、翻文件，转头去泡了杯茶——回来时它已经写完了，而你还在等。这个插件干的事就一件：活干完了，响一下。

## 功能

- **挂在 Agent 生命周期上**：订阅 `on_agent_begin` / `on_agent_done` 两个钩子，一轮任务开始时记时间，结束时算耗时。
- **只对"值得等"的活响**：本轮耗时超过 `min_seconds`（默认 8 秒）才播放，闲聊不会一直响。
- **冷却保护**：`cooldown_seconds`（默认 3 秒）内不重复播放，连续多轮任务不会变成噪音机。
- **默认只在私聊触发**：群里人多，响给你一个人没意义；需要群聊也响就把 `only_private` 关掉。
- **异步播放**：走 `winsound` 的 `SND_ASYNC`，不阻塞消息发送链路。
- **降级策略**：音效文件不存在 → 回退系统星号提示音；宿主不是 Windows 或没有 `winsound` → 整段静默跳过，不抛异常。

## 配置

插件配置页（`_conf_schema.json`）提供 5 项：

| 键 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `enable` | bool | `true` | 总开关 |
| `wav_path` | string | `C:\Windows\Media\Windows Notify System Generic.wav` | 音效文件路径，留空则用系统提示音 |
| `min_seconds` | float | `8` | 本轮耗时超过该值才响 |
| `cooldown_seconds` | float | `3` | 两次播放之间的最小间隔 |
| `only_private` | bool | `true` | 只在私聊触发 |

`C:\Windows\Media` 下挑一个顺耳的就行，比如 `Alarm01.wav`、`Windows Ding.wav`。想用自定义音效，放个 `.wav` 进去、把完整路径填上即可（只支持 wav，`winsound` 不认 mp3）。

## 系统要求

- **Windows**：能出声。其他平台不会报错，但也听不到。
- AstrBot `>= 4.28.0`：依赖 `on_agent_begin` / `on_agent_done` 事件钩子。实测版本 4.29.4，更早的版本没有验证过。
- 无第三方依赖，不需要 `requirements.txt` 里的任何包。

## 安装

把插件目录放到 `data/plugins/astrbot_plugin_task_chime/`，然后在 WebUI 插件页重载，或者从插件市场一键安装。

## 已知限制

- 只在 Agent 真正跑过一轮时触发；纯指令类插件（比如直接返回固定文本的命令）不一定走 Agent 生命周期，不会响。
- 播放的是宿主电脑的音频设备，AstrBot 跑在容器或远程服务器里时，你听不到。
- 不支持音量控制——由系统音量和 wav 本身决定。

## 反馈与联系

遇到 bug、有改进想法，去仓库提 issue：

https://github.com/ylmaochaoyang-cloud/astrbot_plugin_task_chime/issues

写清楚三件事就够了：你的系统、报错日志、复现步骤。私信我不一定看得到，issue 一定会。

## 许可

MIT
