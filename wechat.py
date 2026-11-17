"""微信官方 iLink:扫码登录、长轮询收、回复"""
import base64, json, os, random, re, time, urllib.parse, urllib.request, uuid

BASE = "https://ilinkai.weixin.qq.com"
# 前三段须是官方插件版本(openclaw-weixin 3.x),自家版本只能放后缀
BASE_INFO = {"channel_version": "3.0.0/minichat-0.1.0", "bot_agent": "MiniChat/0.1"}
APP = {"iLink-App-Id": "bot", "iLink-App-ClientVersion": str(3 << 16)}  # 3.0.0 按 0x00MMNNPP


def _headers(token=None):
    h = {**APP, "Content-Type": "application/json", "AuthorizationType": "ilink_bot_token",
         "X-WECHAT-UIN": base64.b64encode(str(random.getrandbits(32)).encode()).decode()}
    return {**h, "Authorization": "Bearer " + token} if token else h


def _req(url, body=None, headers=APP, timeout=45):
    data = None if body is None else json.dumps(body).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data, headers), timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


def login(bots_dir):
    """扫码绑定;成功后 token 存 bots_dir/<bot_id>.json(权限 600)。"""
    for _ in range(3):  # 二维码过期最多换 3 张
        q = _req(BASE + "/ilink/bot/get_bot_qrcode?bot_type=3", {"local_token_list": []}, _headers())
        print("\n请用要绑定的微信扫这个二维码(电脑浏览器打开链接,手机微信扫):\n" + q["qrcode_img_content"] + "\n")
        host, pin = BASE, None
        while True:
            url = f"{host}/ilink/bot/get_qrcode_status?qrcode={urllib.parse.quote(q['qrcode'])}"
            try:
                s = _req(url + (f"&verify_code={urllib.parse.quote(pin)}" if pin else ""))
            except Exception:
                s = {"status": "wait"}
            st = s.get("status", "wait")
            if "need_verifycode" in st:
                pin = input("手机上显示的数字:").strip()
            elif st == "scaned":
                pin = None
                print("已扫码,请在手机上确认…")
            elif st == "scaned_but_redirect" and s.get("redirect_host"):
                host = "https://" + s["redirect_host"]
            elif st == "confirmed":
                bot = {"token": s["bot_token"], "bot_id": s["ilink_bot_id"], "baseurl": s.get("baseurl") or BASE,
                       "owner": s.get("ilink_user_id", ""), "buf": ""}
                os.makedirs(bots_dir, exist_ok=True)
                path = os.path.join(bots_dir, re.sub(r"[^\w.-]", "_", bot["bot_id"]) + ".json")
                save(path, bot)
                return print("绑定成功,现在运行:python main.py wechat")
            elif st == "binded_redirect":
                return print("这个 bot 已经绑定过,直接运行 python main.py wechat")
            elif st in ("expired", "verify_code_blocked"):
                print("二维码过期,换一张…")
                break
    print("多次过期,请稍后重新运行 python main.py login")


def save(path, bot):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(bot, f)


def text_of(msg):
    """取文字;语音取微信给的转写。"""
    parts = [(it.get("text_item") or {}).get("text", "") if it.get("type") == 1 else
             (it.get("voice_item") or {}).get("text", "") for it in msg.get("item_list") or [] if it.get("type") in (1, 3)]
    return "\n".join(p for p in parts if p).strip()


def send(bot, to, context_token, text):
    for i in range(0, len(text), 2000):  # 长回复分段发
        msg = {"from_user_id": "", "to_user_id": to, "client_id": uuid.uuid4().hex, "message_type": 2, "message_state": 2,
               "context_token": context_token, "item_list": [{"type": 1, "text_item": {"text": text[i:i + 2000]}}]}
        r = _req(bot["baseurl"] + "/ilink/bot/sendmessage", {"msg": msg, "base_info": BASE_INFO}, _headers(bot["token"]))
        if r.get("ret"):
            raise RuntimeError(f"发送失败 ret={r.get('ret')} {r.get('errmsg', '')}")


def serve(path, handle, on_idle):
    """一个 bot 的收发循环:handle(用户ID, 文本)→回复;每轮轮询后调 on_idle()。"""
    with open(path) as f:
        bot = json.load(f)
    delay = 1
    while True:
        try:
            r = _req(bot["baseurl"] + "/ilink/bot/getupdates", {"get_updates_buf": bot["buf"], "base_info": BASE_INFO},
                     _headers(bot["token"]))
            if -14 in (r.get("ret"), r.get("errcode")):
                print("会话失效(-14),按官方做法暂停 1 小时;仍不行请重新 login")
                time.sleep(3600)
                continue
            if r.get("ret") or r.get("errcode"):
                raise RuntimeError(f"getupdates ret={r.get('ret')} errcode={r.get('errcode')} {r.get('errmsg', '')}")
            delay = 1
            if r.get("get_updates_buf"):
                bot["buf"] = r["get_updates_buf"]
                save(path, bot)
            for m in r.get("msgs") or []:
                text = text_of(m) if m.get("message_type") == 1 else ""
                if text:
                    send(bot, m["from_user_id"], m.get("context_token", ""), handle(m["from_user_id"], text))
            on_idle()
        except Exception as e:  # 断线、超时、服务端错:退避重试
            print("微信轮询出错,%ds 后重试:%s" % (delay, e))
            time.sleep(delay)
            delay = min(delay * 2, 60)
