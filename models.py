"""多模型:两种协议适配,失败按序回退"""
import json, os, urllib.request


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _post(url, headers, body, timeout=120):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _key(m):
    return os.environ.get(m.get("key_env", ""), "")


def openai(m, system, msgs):
    body = {"model": m["model"], "messages": [{"role": "system", "content": system}] + msgs}
    r = _post(m["base_url"].rstrip("/") + "/chat/completions", {"Authorization": "Bearer " + _key(m)}, body)
    return r["choices"][0]["message"]["content"]


def anthropic(m, system, msgs):
    body = {"model": m["model"], "max_tokens": 2048, "system": system, "messages": msgs}
    hdr = {"x-api-key": _key(m), "anthropic-version": "2023-06-01"}
    r = _post(m["base_url"].rstrip("/") + "/messages", hdr, body)
    return "".join(b.get("text", "") for b in r["content"])


ADAPTERS = {"openai": openai, "anthropic": anthropic}


def chat(models, prefer, system, msgs):
    """按 prefer 优先、其余按列表顺序试;返回 (模型名, 回答)。"""
    order = sorted(models, key=lambda m: m["name"] != prefer)
    errors = []
    for m in order:
        try:
            text = ADAPTERS[m["protocol"]](m, system, msgs)
            if text and text.strip():
                return m["name"], text.strip()
            errors.append(f"{m['name']}: 空回答")
        except Exception as e:  # 网络、鉴权、格式错都回退下一个
            errors.append(f"{m['name']}: {e}")
    raise RuntimeError("所有模型都失败了:\n" + "\n".join(errors))
