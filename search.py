"""联网搜索:抓必应搜索结果页,免 key、只用标准库"""
import html, re, urllib.parse, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


def search(q, n=5):
    """返回结果文本(每条:标题/摘要/链接);连试两次仍失败则抛异常,由调用方兜底。"""
    try:
        return _once(q, n)
    except Exception:
        return _once(q, n)


def _once(q, n):
    url = "https://cn.bing.com/search?q=" + urllib.parse.quote(q)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    page = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore")
    out = []
    for blk in re.findall(r'<li class="b_algo".*?</li>', page, re.S)[:n]:
        h = re.search(r'<h2[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', blk, re.S)
        if not h:
            continue
        p = re.search(r"<p[^>]*>(.*?)</p>", blk, re.S)
        clean = lambda s: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s))).strip()
        out.append(f"{len(out)+1}. {clean(h.group(2))}\n   {clean(p.group(1))[:200] if p else ''}\n   {html.unescape(h.group(1))}")
    if not out:
        raise RuntimeError("没解析到结果")
    return "\n".join(out)
