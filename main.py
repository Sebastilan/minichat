"""入口:命令行对话、微信、登录、整理、自检"""
import glob, hashlib, json, os, sys, tempfile, threading

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(HERE, ".env")):  # 自己解析 .env,不依赖第三方包
    for line in open(os.path.join(HERE, ".env"), encoding="utf-8"):
        k, sep, v = line.strip().partition("=")
        if sep and not k.startswith("#"):
            os.environ.setdefault(k.strip(), v.strip().strip('"'))
import brain, models, sleep, wechat  # noqa: E402  读完 .env 再导入

DATA = os.environ.get("MINICHAT_DATA", os.path.join(HERE, "data"))


def model_list():
    path = os.environ.get("MINICHAT_MODELS", os.path.join(HERE, "models.json"))
    if not os.path.exists(path):
        sys.exit("缺 models.json:复制 models.example.json 改成你的模型,密钥写进 .env")
    return models.load(path)


def cli():
    b = brain.Brain(os.path.join(DATA, "me"), model_list())
    print("命令行对话(/退出 结束;" + brain.HELP + ")")
    while True:
        try:
            text = input("你> ").strip()
        except EOFError:
            break
        if text in ("/退出", "/q"):
            break
        if text:
            print("助手>", b.reply(text))
    print(sleep.run(b))  # 命令行没有后台,退出时整理一次


def run_wechat():
    bots = glob.glob(os.path.join(DATA, "_bots", "*.json"))
    if not bots:
        sys.exit("还没绑定微信:先运行 python main.py login")
    ms, brains, lock = model_list(), {}, threading.Lock()

    def handle(uid, text):  # 一人一个目录,目录名用 ID 哈希,不落真名
        name = hashlib.sha256(uid.encode()).hexdigest()[:12]
        with lock:
            b = brains.setdefault(name, brain.Brain(os.path.join(DATA, name), ms))
        try:
            return b.reply(text)
        except Exception as e:
            return "抱歉,出错了:" + str(e)[:200]

    def on_idle():
        for b in list(brains.values()):
            try:
                if sleep.due(b):
                    print(os.path.basename(b.dir), sleep.run(b))
            except Exception as e:
                print("整理出错:", e)

    for p in bots:
        threading.Thread(target=wechat.serve, args=(p, handle, on_idle), daemon=True).start()
    print(f"微信收发已启动({len(bots)} 个 bot),Ctrl-C 退出")
    threading.Event().wait()


def sleep_all():  # 给 cron 用:整理所有人
    for d in sorted(glob.glob(os.path.join(DATA, "*"))):
        if os.path.isdir(d) and not os.path.basename(d).startswith("_"):
            print(os.path.basename(d), sleep.run(brain.Brain(d, model_list())))


def fake(m, system, msgs):
    """离线假模型:按提示词与最后一句做固定回答。"""
    last = msgs[-1]["content"]
    if "整理长期记忆" in system:
        if "不喝咖啡了" in last:
            return json.dumps([{"op": "retire", "path": "偏好/饮食/咖啡", "quote": "我已经不喝咖啡了"}])
        return "好的:" + json.dumps([
            {"op": "new", "path": "个人/称呼", "stars": 5, "line": "叫他小王", "body": "用户希望被称呼为小王。"},
            {"op": "new", "path": "偏好/饮食/咖啡", "stars": 3, "line": "早上喝美式", "body": "每天早上一杯美式。"},
            {"op": "edit", "path": "偏好/不存在", "quote": "小王", "body": "x"},
            {"op": "new", "path": "a/b/c/d/e", "body": "太深"}], ensure_ascii=False)
    assert "四要素" in system and "记忆索引" in system
    if last.startswith("[记忆 偏好/饮食/咖啡]"):
        assert "美式" in last
        return "你每天早上喝一杯美式。"
    if "喝什么" in last:
        return "读记忆: 偏好/饮食/咖啡"
    if "计划" in last:
        return "好,先问两句:你手里已有什么(输入)?最后想要什么样的计划(输出)?"
    return "记住了。"


def selftest():
    def bad(m, s, msgs):
        raise ConnectionError("模拟断网")
    models.ADAPTERS.update(fake=fake, bad=bad)
    ms = [{"name": "坏的", "protocol": "bad"}, {"name": "假", "protocol": "fake"}]
    b = brain.Brain(os.path.join(tempfile.mkdtemp(), "me"), ms)
    assert "输入" in b.reply("帮我做个周末出游计划"), "四要素追问 + 失败回退"
    b.reply("叫我小王就行,我每天早上喝一杯美式")
    r = sleep.run(b)
    assert "新 2" in r and "拒绝 2" in r, r
    sysprompt = b.system()
    assert "用户希望被称呼为小王" in sysprompt and "每天早上一杯美式" not in sysprompt, "五星卡常驻,其余只进索引"
    assert "★3 偏好/饮食/咖啡 — 早上喝美式" in sysprompt
    assert "美式" in b.reply("我早上一般喝什么?"), "两步读卡"
    assert "已切换" in b.reply("/模型 假") and "→ 假" in b.reply("/模型列表")
    b.reply("我已经不喝咖啡了")
    assert "退 1" in sleep.run(b) and b.memory.read("偏好/饮食/咖啡") is None
    assert glob.glob(os.path.join(b.memory.dir, "_退", "*咖啡.md")) and os.listdir(b.memory.archive_dir)
    print("selftest ok:四要素→回退→睡眠→五星预加载→读卡→切模型→退卡归档")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "cli"
    acts = {"cli": cli, "wechat": run_wechat, "sleep": sleep_all, "selftest": selftest,
            "login": lambda: wechat.login(os.path.join(DATA, "_bots"))}
    acts.get(cmd, lambda: print("用法:python main.py [cli|login|wechat|sleep|selftest]"))()
