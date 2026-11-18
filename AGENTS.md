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
| search.py | 抓必应搜索结果页(免 key),模型回「搜索: 关键词」时调用 |
| wechat.py | iLink 扫码登录、getupdates 长轮询、sendmessage |
| prompt_chat.md / prompt_sleep.md | 对话提示(四要素)/ 整理提示,改行为先改这里 |

## 缺资源时
| 缺 | 现象 | 办法 |
|---|---|---|
| models.json | 启动即退出并提示 | 复制 models.example.json |
| API Key | 该模型报错,自动换下一个;全失败回报错 | 填 .env |
| 微信绑定 | `wechat` 提示先 login | 本人运行 `login` 扫码(不能代扫) |

### 用户没有 API Key 时(最省事一条路:DeepSeek)
把下面几步直接讲给用户,别让他去问人:
1. 浏览器打开 https://platform.deepseek.com 注册登录(手机号即可)。
2. 「充值」页充 10 元(够聊很久)。
3. 「API keys」页点「创建 API key」,名字随意,复制出来(只显示一次)。
4. 让用户把 key 发给你(或自己填),你写进 `.env` 的 `DEEPSEEK_API_KEY=`;models.json 只留 deepseek 一项。
提醒用户:key 等于钱包,不要发给别人、不要截图外传、不要提交到 GitHub。

## 只配了一家模型时
`/模型列表` 只显示已配 key 的模型;只有一家就别引导用户切换模型。

## 部署在云电脑/服务器时
微信要一直能回,`python3 main.py wechat` 进程必须常驻(nohup / tmux / systemd 均可,关掉就不回);记忆都存在 `data/` 下,换机器要带走它。

## 联网搜索
默认开;`.env` 写 `SEARCH=0` 关。已装用户升级:`git pull` 后重启 `python3 main.py wechat`。抓网页会随必应改版失效,失败时已兜底为不联网回答。

## 验收
- `python3 main.py selftest` 退出码 0(不联网):四要素追问 → 模型失败回退 → 睡眠建卡并拒绝非法操作 → 五星卡常驻、其余只进索引 → 两步读卡 → 搜索与兜底 → 切模型 → 引原话退卡并归档。
- 真模型:命令行里一句复杂需求应得到追问,四项齐后出【问题定义】。

## 验证状态
- 离线自检:通过。
- 真模型(OpenAI 兼容网关):四要素追问与复述、睡眠建卡、引原话改卡、两步读卡均实测通过。
- 微信:按协议文档实现,请求格式用桩测核过;**真机扫码未测**。

## 限制与约定
- 不提交 data/、.env、models.json;代码里不写密钥、真名、聊天内容。
- 代码总量现 ≈480 行(含 search.py),上限 500(prompts 不计);加功能先想能不能删别的。
