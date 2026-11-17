# MiniChat · 给 AI 代理的说明

## 做什么
微信 / 命令行私人助手:四要素引导复杂需求、多模型可换、睡眠整理成记忆卡片 + 索引。标准库零依赖,Python ≥ 3.9。

## 入口
`python3 main.py [cli|login|wechat|sleep|selftest]`(默认 cli)。一文一职:

| 文件 | 职责 |
|---|---|
| main.py | 入口分派、命令行循环、微信用户分桶、离线自检 |
| brain.py | 一轮对话:系统提示 + 最近 N 轮 + 「读记忆:」两步取卡 + 斜杠命令 |
| models.py | 读 models.json;openai / anthropic 两个适配器;按序回退 |
| memory.py | 卡片读写、索引、预加载、路径校验、存档 |
| sleep.py | 静默判定;新聊天 → 模型出操作 JSON → 校验落盘 |
| wechat.py | iLink 扫码登录、getupdates 长轮询、sendmessage |
| prompt_chat.md / prompt_sleep.md | 对话提示(四要素)/ 整理提示,改行为先改这里 |

## 缺资源时
| 缺 | 现象 | 办法 |
|---|---|---|
| models.json | 启动即退出并提示 | 复制 models.example.json |
| API Key | 该模型报错,自动换下一个;全失败回报错 | 填 .env |
| 微信绑定 | `wechat` 提示先 login | 本人运行 `login` 扫码(不能代扫) |

## 验收
- `python3 main.py selftest` 退出码 0(不联网):四要素追问 → 模型失败回退 → 睡眠建卡并拒绝非法操作 → 五星卡常驻、其余只进索引 → 两步读卡 → 切模型 → 引原话退卡并归档。
- 真模型:命令行里一句复杂需求应得到追问,四项齐后出【问题定义】。

## 验证状态
- 离线自检:通过。
- 真模型(OpenAI 兼容网关):四要素追问与复述、睡眠建卡、引原话改卡、两步读卡均实测通过。
- 微信:按协议文档实现,请求格式用桩测核过;**真机扫码未测**。

## 限制与约定
- 不提交 data/、.env、models.json;代码里不写密钥、真名、聊天内容。
- 代码总量目标 ≈450 行,上限 500(prompts 不计);加功能先想能不能删别的。
