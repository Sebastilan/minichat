"""睡眠整理:新聊天交模型出操作,校验后落盘"""
import json, os, re, time
import models
from brain import prompt

IDLE_MIN = float(os.environ.get("SLEEP_IDLE_MIN", "5"))
OPS = ("new", "edit", "retire", "star")


def due(brain):
    """有没整理的聊天,且已静默 IDLE_MIN 分钟。"""
    lines = brain.chat_lines()
    return len(lines) > brain.state().get("slept_lines", 0) and time.time() - lines[-1]["t"] > IDLE_MIN * 60


def check(mem, op, said):
    """返回拒绝理由;合格返回 None。"""
    kind, rel, quote = op.get("op"), str(op.get("path", "")), str(op.get("quote", "")).strip()
    p = mem.path(rel)
    exists = bool(p) and os.path.isfile(p)
    if kind not in OPS:
        return "未知操作"
    if not p:
        return "路径不合法(主题最多三层)"
    if kind == "new" and (exists or not str(op.get("body", "")).strip()):
        return "卡已存在或正文为空"
    if kind != "new" and not exists:
        return "卡不存在"
    if kind in ("edit", "retire") and (len(quote) < 2 or quote not in said):
        return "改/退须引用户原话"
    return None


def apply(mem, ops, said):
    done, bad = {k: 0 for k in OPS}, []
    for op in ops if isinstance(ops, list) else []:
        try:
            why = check(mem, op, said) if isinstance(op, dict) else "格式不对"
            if why:
                bad.append(f"{op}:{why}")
                continue
            kind, rel = op["op"], op["path"]
            if kind == "retire":
                mem.retire(rel)
            else:
                s, l, b = mem.parse(mem.read(rel)) if kind != "new" else (3, "", "")
                if kind == "star":
                    mem.write(rel, op.get("stars", s), l, b)
                else:
                    mem.write(rel, op.get("stars", s), op.get("line", l), op.get("body", b))
            done[kind] += 1
        except Exception as e:
            bad.append(f"{op}:{e}")
    return done, bad


def run(brain):
    lines, st = brain.chat_lines(), brain.state()
    new = lines[st.get("slept_lines", 0):]
    if not new:
        return "没有新聊天,不用整理。"
    talk = "\n".join(("用户" if l["role"] == "user" else "助手") + ": " + l["text"] for l in new)
    said = "\n".join(l["text"] for l in new if l["role"] == "user")
    mem = brain.memory
    cards = "\n\n".join(f"### {r}\n星级 {s} · {l}\n{b}" for r, s, l, b in mem.cards())[:6000]
    msg = f"# 现有记忆卡\n{cards or '(还没有卡)'}\n\n# 新聊天\n{talk}"
    _, out = models.chat(brain.models, st["model"], prompt("prompt_sleep.md"), [{"role": "user", "content": msg}])
    m = re.search(r"\[.*\]", out, re.S)
    try:
        ops = json.loads(m.group(0)) if m else []
    except ValueError:
        return "整理失败:模型没回合法 JSON,下次再试。"
    if ops:
        mem.archive()
    done, bad = apply(mem, ops, said)
    mem.reindex()
    brain.save_state(slept_lines=len(lines))
    summary = f"整理完:新 {done['new']} 改 {done['edit']} 退 {done['retire']} 调星 {done['star']}"
    return summary + (f";拒绝 {len(bad)} 条:" + ";".join(bad) if bad else "")
