"""记忆卡片:读写、索引、预加载、路径校验"""
import os, re, shutil, time

STAR_MAX_CHARS, INDEX_MAX_CHARS, BODY_MAX = 800, 1500, 200


class Memory:
    def __init__(self, user_dir):
        self.dir = os.path.join(user_dir, "memory")
        self.archive_dir = os.path.join(user_dir, "archive")
        os.makedirs(self.dir, exist_ok=True)

    def path(self, rel):
        """卡路径 主题[/子主题[/子子主题]]/名 → 绝对路径;越界或超过三层主题返回 None。"""
        rel = rel.strip().strip("/").removesuffix(".md")
        parts = rel.split("/")
        if not rel or len(parts) > 4 or any(p in ("", ".", "..") or p.startswith("_") for p in parts):
            return None
        if len(parts) == 1:  # 没给主题就放进「杂项」
            parts = ["杂项"] + parts
        return os.path.join(self.dir, *parts) + ".md"

    def rel(self, abspath):
        return os.path.relpath(abspath, self.dir).removesuffix(".md")

    def read(self, rel):
        p = self.path(rel)
        if p and os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                return f.read()
        return None

    @staticmethod
    def parse(text):
        head = dict(re.findall(r"^(星级|更新|一句话):\s*(.*)$", text, re.M))
        body = text.split("\n\n", 1)[1].strip() if "\n\n" in text else ""
        return int(head.get("星级", "1") or 1), head.get("一句话", ""), body

    def write(self, rel, stars, line, body):
        p = self.path(rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        stars = max(1, min(5, int(stars)))
        with open(p, "w", encoding="utf-8") as f:
            f.write(f"星级: {stars}\n更新: {time.strftime('%m-%d')}\n一句话: {line.strip()}\n\n{body.strip()[:BODY_MAX]}\n")

    def retire(self, rel):
        """退卡只挪进 _退/,不删。"""
        p = self.path(rel)
        dest = os.path.join(self.dir, "_退", time.strftime("%Y%m%d-%H%M%S-") + self.rel(p).replace("/", "_") + ".md")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(p, dest)

    def cards(self):
        """[(相对路径, 星级, 一句话, 正文)],跳过 _退/ 与索引。"""
        out = []
        for root, dirs, files in os.walk(self.dir):
            dirs[:] = sorted(d for d in dirs if not d.startswith("_"))
            for fn in sorted(files):
                if fn.endswith(".md") and fn != "index.md":
                    p = os.path.join(root, fn)
                    with open(p, encoding="utf-8") as f:
                        out.append((self.rel(p), *self.parse(f.read())))
        return out

    def reindex(self):
        lines = [f"★{s} {r} — {l}" for r, s, l, _ in sorted(self.cards(), key=lambda c: (-c[1], c[0]))]
        with open(os.path.join(self.dir, "index.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))

    def preload(self):
        """系统提示里的记忆段:五星卡正文 + 整份索引,各自封顶。"""
        stars = "\n".join(f"- {r}:{b}" for r, s, _, b in self.cards() if s == 5)[:STAR_MAX_CHARS]
        p = os.path.join(self.dir, "index.md")
        index = open(p, encoding="utf-8").read()[:INDEX_MAX_CHARS] if os.path.exists(p) else ""
        return f"## 五星记忆(常驻)\n{stars or '(暂无)'}\n\n## 记忆索引(要看哪张卡就回一行「读记忆: 路径」)\n{index or '(暂无)'}"

    def archive(self):
        """整理前整份存档。"""
        dest = os.path.join(self.archive_dir, time.strftime("%Y%m%d-%H%M%S"))
        shutil.copytree(self.dir, dest, dirs_exist_ok=True)
        return dest
