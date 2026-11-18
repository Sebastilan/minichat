"""一轮对话:拼提示、带历史、两步读卡、斜杠命令"""
import json, os, re, time
import models, search
from memory import Memory

HERE = os.path.dirname(os.path.abspath(__file__))
HISTORY_TURNS = int(os.environ.get("HISTORY_TURNS", "10"))
SEARCH_ON = os.environ.get("SEARCH", "1") != "0"  # SEARCH=0 关闭联网搜索
HELP = "/模型 名字 切换模型 · /模型列表 · /记忆 看索引 · /睡 立刻整理记忆 · /帮助"


def prompt(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


class Brain:
    def __init__(self, user_dir, model_list):
        self.dir, self.models = user_dir, model_list
        os.makedirs(user_dir, exist_ok=True)
        self.chat_file = os.path.join(user_dir, "chat.jsonl")
        self.state_file = os.path.join(user_dir, "state.json")
        self.memory = Memory(user_dir)

    def state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, encoding="utf-8") as f:
                return json.load(f)
        return {"model": self.models[0]["name"], "slept_lines": 0}

    def save_state(self, **kw):
        s = {**self.state(), **kw}
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False)

    def chat_lines(self):
        if not os.path.exists(self.chat_file):
            return []
        with open(self.chat_file, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]

    def log(self, role, text):
        with open(self.chat_file, "a", encoding="utf-8") as f:
            f.write(json.dumps({"t": time.time(), "role": role, "text": text}, ensure_ascii=False) + "\n")

    def system(self):
        return prompt("prompt_chat.md") + "\n\n# 关于这位用户的记忆\n" + self.memory.preload()

    def ask(self, msgs):
        name, text = models.chat(self.models, self.state()["model"], self.system(), msgs)
        return text

    def reply(self, text):
        text = text.strip()
        if text.startswith("/"):
            return self.command(text)
        self.log("user", text)
        msgs = [{"role": l["role"], "content": l["text"]} for l in self.chat_lines()[-(HISTORY_TURNS * 2 + 1):]]  # 本句 + 前 N 轮
        out = self.ask(msgs)
        for _ in range(3):  # 最多三步:读卡或搜索,拿到内容再答
            m = re.search(r"^\s*读记忆[::]\s*(\S+)\s*$", out, re.M)
            q = SEARCH_ON and re.search(r"^\s*搜索[::]\s*(.+?)\s*$", out, re.M)
            if m:
                card = self.memory.read(m.group(1)) or "(没有这张卡)"
                feed = f"[记忆 {m.group(1)}]\n{card}\n(以上是你要读的卡,请接着回答我上一句。)"
            elif q:
                try:
                    feed = f"[搜索 {q.group(1)}]\n{search.search(q.group(1))}\n(以上是搜索结果,请据此回答我上一句,别再搜。)"
                except Exception:
                    feed = "[搜索失败]\n(没搜到,请照常回答,并告诉用户这次没能联网查。)"
            else:
                break
            msgs += [{"role": "assistant", "content": out}, {"role": "user", "content": feed}]
            out = self.ask(msgs)
        self.log("assistant", out)
        return out

    def command(self, text):
        cmd, _, arg = text.partition(" ")
        names = [m["name"] for m in self.models if models._key(m)]  # 只列已配 key 的
        if cmd == "/模型" and arg.strip():
            if arg.strip() not in names:
                return "没有这个模型。可选:" + "、".join(names)
            self.save_state(model=arg.strip())
            return "已切换到 " + arg.strip()
        if cmd in ("/模型", "/模型列表"):
            cur = self.state()["model"]
            return "\n".join(("→ " if n == cur else "  ") + n for n in names)
        if cmd == "/记忆":
            self.memory.reindex()
            return self.memory.preload()
        if cmd == "/睡":
            import sleep
            return sleep.run(self)
        return HELP
