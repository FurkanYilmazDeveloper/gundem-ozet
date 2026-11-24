# -*- coding: utf-8 -*-
"""
Gündem Özet — Türkiye ve dünya gündemini RSS'lerden tarayıp ücretsiz özetleyen
küçük masaüstü programı. Sadece Python standart kütüphanesi kullanır (ek kurulum yok).
Kaynak listesi: %APPDATA%\\GundemOzet\\kaynaklar.json (Ayarlar > Kaynakları düzenle)
"""
import json, os, re, sys, threading, queue, time, webbrowser, html, ssl
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import tkinter as tk
import tkinter.font as tkfont

APP = "Gündem Özet"
CFG_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "GundemOzet")
CFG_FILE = os.path.join(CFG_DIR, "ayarlar.json")
FEED_FILE = os.path.join(CFG_DIR, "kaynaklar.json")

GN_TR = "hl=tr&gl=TR&ceid=TR:tr"
GN_EN = "hl=en-US&gl=US&ceid=US:en"
GN = "https://news.google.com/rss/headlines/section/topic/{}?"
# kategori: turkiye | dunya | ekonomi | spor | teknoloji | global      tur: haber | blog
DEFAULT_FEEDS = [
    {"ad": "Google Haberler", "url": "https://news.google.com/rss?" + GN_TR, "kategori": "turkiye"},
    {"ad": "Google Haberler", "url": GN.format("NATION") + GN_TR, "kategori": "turkiye"},
    {"ad": "Google Haberler", "url": GN.format("WORLD") + GN_TR, "kategori": "dunya"},
    {"ad": "Google Haberler", "url": GN.format("BUSINESS") + GN_TR, "kategori": "ekonomi"},
    {"ad": "Google Haberler", "url": GN.format("SPORTS") + GN_TR, "kategori": "spor"},
    {"ad": "Google Haberler", "url": GN.format("TECHNOLOGY") + GN_TR, "kategori": "teknoloji"},
    {"ad": "Hürriyet", "url": "https://www.hurriyet.com.tr/rss/anasayfa", "kategori": "turkiye"},
    {"ad": "Milliyet", "url": "https://www.milliyet.com.tr/rss/rssnew/gundemrss.xml", "kategori": "turkiye"},
    {"ad": "Sabah", "url": "https://www.sabah.com.tr/rss/gundem.xml", "kategori": "turkiye"},
    {"ad": "NTV", "url": "https://www.ntv.com.tr/gundem.rss", "kategori": "turkiye"},
    {"ad": "NTV", "url": "https://www.ntv.com.tr/dunya.rss", "kategori": "dunya"},
    {"ad": "NTV", "url": "https://www.ntv.com.tr/ekonomi.rss", "kategori": "ekonomi"},
    {"ad": "NTV", "url": "https://www.ntv.com.tr/spor.rss", "kategori": "spor"},
    {"ad": "NTV", "url": "https://www.ntv.com.tr/teknoloji.rss", "kategori": "teknoloji"},
    {"ad": "CNN Türk", "url": "https://www.cnnturk.com/feed/rss/all/news", "kategori": "turkiye"},
    {"ad": "TRT Haber", "url": "https://www.trthaber.com/manset_articles.rss", "kategori": "turkiye"},
    {"ad": "Anadolu Ajansı", "url": "https://www.aa.com.tr/tr/rss/default?cat=guncel", "kategori": "turkiye"},
    {"ad": "Habertürk", "url": "https://www.haberturk.com/rss", "kategori": "turkiye"},
    {"ad": "T24", "url": "https://t24.com.tr/rss", "kategori": "turkiye"},
    {"ad": "Sözcü", "url": "https://www.sozcu.com.tr/feeds-rss-category-sozcu", "kategori": "turkiye"},
    {"ad": "BBC Türkçe", "url": "https://feeds.bbci.co.uk/turkce/rss.xml", "kategori": "turkiye"},
    {"ad": "DW Türkçe", "url": "https://rss.dw.com/rdf/rss-tur-all", "kategori": "dunya"},
    {"ad": "Bloomberg HT", "url": "https://www.bloomberght.com/rss", "kategori": "ekonomi"},
    {"ad": "Webtekno", "url": "https://www.webtekno.com/rss.xml", "kategori": "teknoloji", "tur": "blog"},
    {"ad": "ShiftDelete", "url": "https://shiftdelete.net/feed", "kategori": "teknoloji", "tur": "blog"},
    {"ad": "DonanımHaber", "url": "https://www.donanimhaber.com/rss/tum/", "kategori": "teknoloji", "tur": "blog"},
    {"ad": "Google News", "url": "https://news.google.com/rss?" + GN_EN, "kategori": "global"},
    {"ad": "Google News", "url": GN.format("WORLD") + GN_EN, "kategori": "global"},
    {"ad": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "kategori": "global"},
    {"ad": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "kategori": "global"},
    {"ad": "The Guardian", "url": "https://www.theguardian.com/world/rss", "kategori": "global"},
]

TABS = [("Türkiye", ["turkiye"]), ("Dünya", ["dunya", "global"]), ("Ekonomi", ["ekonomi"]),
        ("Spor", ["spor"]), ("Teknoloji", ["teknoloji"])]

THEMES = {
    "koyu": dict(bg="#14161b", head="#0f1115", text="#e6e8ec", sub="#9aa0ab", muted="#6b717d",
                 line="#23262e", tab="#1e2128", tabtxt="#a9afba", accent="#e53935",
                 sumbg="#1b202b", sumbd="#2c3445", sumh="#ffb74d", sumtxt="#d7dae0",
                 cg=("#1f2a22", "#81c784"), cb=("#232a36", "#90caf9"), ch=("#36201f", "#ef9a9a"),
                 trbg="#1a1214", glbg="#10161f", tick="#d6d9df", rank="#3a3f4b", hover="#1b1e25",
                 seg="#1e2128", live="#4caf50"),
    "acik": dict(bg="#fbfbfc", head="#f1f2f5", text="#1b1d22", sub="#5f6570", muted="#8a909c",
                 line="#e6e8ec", tab="#eceef2", tabtxt="#4a505c", accent="#e53935",
                 sumbg="#fff6ea", sumbd="#f3dcb8", sumh="#d9822b", sumtxt="#33363d",
                 cg=("#e6f4e8", "#2e7d32"), cb=("#e5eefa", "#1565c0"), ch=("#fdeaea", "#c62828"),
                 trbg="#fdecec", glbg="#e9f1fb", tick="#2a2d33", rank="#c9ccd3", hover="#f1f2f5",
                 seg="#e3e5ea", live="#2e7d32"),
}

STOP = set("""ve ile bir bu şu o da de için mi mı mu mü ne çok daha en gibi kadar sonra önce olarak olan oldu
ama ya her hem ki son dakika flaş haber haberi haberler yeni nasıl neden işte dedi etti yaptı büyük ilk var yok
diye göre üzere ise ancak artık bile tüm bütün hangi kim kimdir nedir nerede açıkladı açıklama açıklaması açıkladığı
bugün yarın dün saat yıl the a an of to in on for and is are was were with at by from as after over says said new
its it be has have will not but this that who what how why than into about more amid""".split())
WORD = re.compile(r"[a-zçğıöşüâîû0-9]+")
TAG = re.compile(r"<[^>]+>")
SENT = re.compile(r"(?<=[.!?])\s+")
NOISE_PRE = re.compile(r"^\s*(son dakika( haberi)?|sıcak gelişme|flaş( gelişme| haber)?|breaking( news)?|video|canlı|özel haber)\s*[:|!\-–—]+\s*", re.I)
NOISE_SUF = re.compile(r"\s*[-–—|,]?\s*(işte (detaylar|ayrıntılar|o (anlar|görüntüler))|detaylar haberimizde|son dakika)\s*[.!]*\s*$", re.I)


def clean_title(t):
    for _ in range(2):
        t = NOISE_PRE.sub("", t)
        t = NOISE_SUF.sub("", t)
    t = t.strip(" -–|!")
    return t[:1].upper() + t[1:] if t else t


# ---------------------------------------------------------------- ayarlar
def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    try:
        os.makedirs(CFG_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def system_theme():
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                           r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        return "acik" if winreg.QueryValueEx(k, "AppsUseLightTheme")[0] else "koyu"
    except Exception:
        return "koyu"


# ---------------------------------------------------------------- metin işleme
def tr_lower(s):
    return s.replace("I", "ı").replace("İ", "i").lower()


def clean(s):
    s = html.unescape(TAG.sub(" ", s or ""))
    return re.sub(r"\s+", " ", s).strip()


def tokens(s):
    out = set()
    for w in WORD.findall(tr_lower(s)):
        if len(w) < 3 or w in STOP:
            continue
        out.add(w[:5] if not w.isdigit() else w)   # kaba Türkçe kök: ilk 5 harf
    return out


# ---------------------------------------------------------------- RSS okuma
def local(tag):
    return tag.rsplit("}", 1)[-1].lower()


def child_text(el, *names):
    for c in el:
        if local(c.tag) in names:
            if local(c.tag) == "link" and c.get("href"):
                return c.get("href")
            if c.text and c.text.strip():
                return c.text.strip()
    return ""


def parse_date(s):
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)
    except Exception:
        try:
            d = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
        except Exception:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d


def parse_feed(data, feed):
    root = ET.fromstring(data)
    items = []
    for el in root.iter():
        if local(el.tag) not in ("item", "entry"):
            continue
        title = clean(child_text(el, "title"))
        if not title:
            continue
        src = feed["ad"]
        for c in el:
            if local(c.tag) == "source" and c.text:
                src = c.text.strip()
        if "news.google" in feed["url"] and " - " in title:
            title = title.rsplit(" - ", 1)[0].strip()
        title = clean_title(title)
        if not title:
            continue
        desc = clean(child_text(el, "description", "summary", "content"))
        if "news.google" in feed["url"]:
            desc = ""          # Google açıklamaları sadece bağlantı listesi
        items.append(dict(
            title=title, desc=desc[:600], link=child_text(el, "link", "guid"),
            src=src, cat=feed["kategori"], blog=feed.get("tur") == "blog",
            date=parse_date(child_text(el, "pubdate", "published", "updated", "date")),
        ))
        if len(items) >= 60:
            break
    return items


CTX = ssl.create_default_context()


def fetch(feed):
    req = urllib.request.Request(feed["url"], headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GundemOzet/1.0",
        "Accept": "application/rss+xml, application/xml, text/xml, */*"})
    try:
        with urllib.request.urlopen(req, timeout=12, context=CTX) as r:
            return parse_feed(r.read(3_000_000), feed)
    except Exception:
        return None


# ---------------------------------------------------------------- kümeleme + özet
def cluster(items):
    """Aynı olayı anlatan haberleri tek başlıkta toplar."""
    now = datetime.now(timezone.utc)
    clusters, index = [], defaultdict(list)
    seen = set()
    for it in sorted(items, key=lambda x: x["date"] or now, reverse=True):
        key = tr_lower(it["title"])[:80]
        if (key, it["src"]) in seen:
            continue
        seen.add((key, it["src"]))
        tk_ = tokens(it["title"])
        it["tok"] = tk_
        best, best_s = None, 0.0
        cand = Counter(ci for t in tk_ for ci in index[t])
        for ci, shared in cand.items():
            if shared < 2:
                continue
            c = clusters[ci]
            s = max(len(tk_ & m["tok"]) / max(1, min(len(tk_), len(m["tok"]))) for m in c["items"][:6])
            if s > best_s:
                best, best_s = ci, s
        if best is not None and best_s >= 0.5:
            c = clusters[best]
        else:
            c = dict(items=[], words=Counter())
            clusters.append(c)
            best = len(clusters) - 1
        c["items"].append(it)
        c["words"].update(tk_ | tokens(it["desc"][:200]))
        for t in tk_:
            if best not in index[t]:
                index[t].append(best)

    out = []
    for c in clusters:
        its = c["items"]
        srcs = {i["src"] for i in its}
        dates = [i["date"] for i in its if i["date"]]
        newest = max(dates) if dates else now
        age_h = max(0.0, (now - newest).total_seconds() / 3600)
        if age_h > 36:
            continue
        recent = sum(1 for d in dates if (now - d) < timedelta(hours=2))
        score = len(srcs) * 3 + len(its) + max(0, 12 - age_h) * 0.5
        # başlık: kelimeleri kümeye en çok uyan, makul uzunluktaki başlık
        title = max(its, key=lambda i: (sum(c["words"][t] for t in i["tok"]) / (1 + abs(len(i["title"]) - 70) / 40)))["title"]
        out.append(dict(title=title, summary=summarize(c, title), n=len(srcs), blogs=sum(1 for i in its if i["blog"]),
                        link=its[0]["link"], score=score, hot=recent >= 3 and len(srcs) >= 3,
                        cat=Counter(i["cat"] for i in its).most_common(1)[0][0]))
    out.sort(key=lambda x: x["score"], reverse=True)
    return out


def summarize(c, title):
    """Ücretsiz, çıkarımsal özet: kümenin ortak kelimelerini en iyi taşıyan cümle."""
    tl = tr_lower(title)
    best, best_s = "", 0
    for it in c["items"]:
        for s in SENT.split(it["desc"]):
            s = s.strip()
            if not (35 <= len(s) <= 240) or tr_lower(s)[:50] == tl[:50]:
                continue
            tk_ = tokens(s)
            sc = sum(c["words"][t] for t in tk_) / (len(tk_) ** 0.5 + 1)
            if sc > best_s:
                best, best_s = s, sc
    if not best:
        alts = [i["title"] for i in c["items"] if tr_lower(i["title"]) != tl]
        best = alts[0] if alts else ""
    return best


def daily_summary(cl):
    if not cl:
        return "Henüz haber yok. İnternet bağlantınızı kontrol edin ya da ⟳ ile yeniden tarayın."
    t = cl[0]
    s = f"En çok konuşulan: {t['title']} ({t['n']} kaynak)."
    rest = [c["title"] for c in cl[1:4]]
    if rest:
        s += "\nÖne çıkan diğer konular:\n" + "\n".join("• " + r for r in rest)
    return s


# ---------------------------------------------------------------- arayüz
class Ticker:
    def __init__(self, parent, label, color, bg, fg, font, app):
        self.app, self.fg, self.font = app, fg, font
        f = tk.Frame(parent, bg=bg, height=28)
        f.pack(fill="x", side="top")
        f.pack_propagate(False)
        tk.Label(f, text=f" {label} ", bg=color, fg="white", font=app.f_lbl, padx=6).pack(side="left", fill="y")
        self.c = tk.Canvas(f, bg=bg, highlightthickness=0, height=28)
        self.c.pack(side="left", fill="both", expand=True)
        self.c.bind("<Enter>", lambda e: setattr(self, "paused", True))
        self.c.bind("<Leave>", lambda e: setattr(self, "paused", False))
        self.paused, self.ids, self.alive = False, [], True
        self.c.after(40, self.tick)

    def set(self, heads):
        self.c.delete("all")
        self.ids = []
        if not heads:
            self.c.create_text(10, 14, anchor="w", text="Haberler yükleniyor…", fill=self.fg, font=self.font)
            return
        width = max(self.c.winfo_width(), 400)
        x, seq = 10, list(heads)
        while True:
            for title, link in seq:
                i = self.c.create_text(x, 14, anchor="w", text=f"{title}     •     ", fill=self.fg, font=self.font)
                self.c.tag_bind(i, "<Button-1>", lambda e, l=link: l and webbrowser.open(l))
                self.c.tag_bind(i, "<Enter>", lambda e: self.c.config(cursor="hand2"))
                self.c.tag_bind(i, "<Leave>", lambda e: self.c.config(cursor=""))
                self.ids.append(i)
                x = self.c.bbox(i)[2]
            if x > width * 2:
                break

    def tick(self):
        if not self.alive:
            return
        try:
            if self.ids and not self.paused and self.app.root.state() != "iconic":
                self.c.move("all", -1, 0)
                first = self.ids[0]
                b = self.c.bbox(first)
                if b and b[2] < 0:
                    last = self.c.bbox(self.ids[-1])
                    self.c.move(first, last[2] - b[0], 0)
                    self.ids.append(self.ids.pop(0))
            self.c.after(30, self.tick)
        except tk.TclError:
            pass


class App:
    def __init__(self):
        try:  # net yazı için Windows DPI farkındalığı
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        self.cfg = {"tema": "sistem", "aralik_dk": 10, "ustte": False, "geometri": "460x720"}
        self.cfg.update(load_json(CFG_FILE, {}))
        if not os.path.exists(FEED_FILE):
            save_json(FEED_FILE, DEFAULT_FEEDS)
        self.root = tk.Tk()
        self.root.title(APP)
        self.root.geometry(self.cfg["geometri"])
        self.root.minsize(380, 480)
        self.root.attributes("-topmost", self.cfg["ustte"])
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        fam = "Segoe UI" if "Segoe UI" in tkfont.families() else "DejaVu Sans"
        self.f = lambda size, w="normal": (fam, size, w)
        self.f_lbl = self.f(8, "bold")
        self.tab = 0
        self.data = {}          # kategori-sekme -> küme listesi
        self.ticks = ([], [])
        self.meta = "Taranıyor…"
        self.busy = False
        self.q = queue.Queue()
        self.timer = None
        self.build()
        self.refresh()
        self.root.after(300, self.poll)
        self.root.mainloop()

    # --- tema
    @property
    def th(self):
        t = self.cfg["tema"]
        return THEMES[system_theme() if t == "sistem" else t]

    def set_theme(self, t):
        self.cfg["tema"] = t
        save_json(CFG_FILE, self.cfg)
        self.build()

    # --- yardımcılar
    def btn(self, parent, text, cmd, bg, fg, font=None, padx=6, **kw):
        l = tk.Label(parent, text=text, bg=bg, fg=fg, font=font or self.f(11), padx=padx, cursor="hand2", **kw)
        l.bind("<Button-1>", lambda e: cmd())
        return l

    def chip(self, parent, text, colors):
        tk.Label(parent, text=text, bg=colors[0], fg=colors[1], font=self.f(8), padx=6, pady=1).pack(side="left", padx=(0, 5))

    # --- arayüzü kur (tema değişince baştan kurulur)
    def build(self):
        for t in getattr(self, "tickers", []):
            t.alive = False
        for w in self.root.winfo_children():
            if not isinstance(w, tk.Toplevel):
                w.destroy()
        T = self.th
        self.root.configure(bg=T["bg"])

        head = tk.Frame(self.root, bg=T["head"])
        head.pack(fill="x")
        tk.Label(head, text="●", fg=T["accent"], bg=T["head"], font=self.f(11)).pack(side="left", padx=(12, 4), pady=8)
        tk.Label(head, text="GÜNDEM · Özet", fg=T["text"], bg=T["head"], font=self.f(11, "bold")).pack(side="left")
        moon = "☀" if T is THEMES["acik"] else "🌙"
        for txt, cmd in (("⚙", self.settings), (moon, self.toggle_theme), ("📌", self.toggle_top), ("⟳", self.refresh)):
            fg = T["accent"] if (txt == "📌" and self.cfg["ustte"]) else T["sub"]
            self.btn(head, txt, cmd, T["head"], fg).pack(side="right", padx=(0, 4))

        m = tk.Frame(self.root, bg=T["bg"])
        m.pack(fill="x", padx=14, pady=(8, 6))
        self.meta_l = tk.Label(m, text=self.meta, fg=T["muted"], bg=T["bg"], font=self.f(8))
        self.meta_l.pack(side="left")
        self.live_l = tk.Label(m, text="● Canlı", fg=T["live"], bg=T["bg"], font=self.f(8, "bold"))
        self.live_l.pack(side="right")

        tabs = tk.Frame(self.root, bg=T["bg"])
        tabs.pack(fill="x", padx=14, pady=(0, 8))
        for i, (name, _) in enumerate(TABS):
            on = i == self.tab
            self.btn(tabs, name, lambda i=i: self.select_tab(i), T["accent"] if on else T["tab"],
                     "white" if on else T["tabtxt"], self.f(9, "bold" if on else "normal"), padx=9, pady=2
                     ).pack(side="left", padx=(0, 5))

        # alt kısım (önce paketlenir ki her zaman görünsün)
        foot = tk.Frame(self.root, bg=T["head"])
        foot.pack(fill="x", side="bottom")
        tk.Label(foot, text=f"Her {self.cfg['aralik_dk']} dk'da otomatik tarama", fg=T["muted"],
                 bg=T["head"], font=self.f(8)).pack(side="left", padx=12, pady=5)
        seg = tk.Frame(foot, bg=T["seg"])
        seg.pack(side="right", padx=10, pady=4)
        for key, txt in (("koyu", "🌙 Koyu"), ("acik", "☀ Açık"), ("sistem", "💻 Sistem")):
            on = self.cfg["tema"] == key
            self.btn(seg, txt, lambda k=key: self.set_theme(k), T["accent"] if on else T["seg"],
                     "white" if on else T["sub"], self.f(8), padx=6).pack(side="left", padx=1, pady=1)

        tk_frame = tk.Frame(self.root, bg=T["bg"])
        tk_frame.pack(fill="x", side="bottom")
        tk.Frame(tk_frame, bg=T["line"], height=1).pack(fill="x")
        self.tickers = [Ticker(tk_frame, "TÜRKİYE", "#e53935", T["trbg"], T["tick"], self.f(9), self),
                        Ticker(tk_frame, "GLOBAL", "#1e88e5", T["glbg"], T["tick"], self.f(9), self)]

        # kaydırılabilir orta alan
        mid = tk.Frame(self.root, bg=T["bg"])
        mid.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(mid, bg=T["bg"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=T["bg"])
        self.win_id = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self.on_resize)
        self.root.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-e.delta / 120), "units"))
        self.root.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.root.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        self.root.after(50, self.render)

    def on_resize(self, e):
        self.canvas.itemconfigure(self.win_id, width=e.width)
        w = e.width - 70
        if abs(getattr(self, "_wrap", 0) - w) > 20:
            self._wrap = w
            self.render()

    def render(self):
        T = self.th
        wrap = getattr(self, "_wrap", 380)
        for w in self.inner.winfo_children():
            w.destroy()
        cl = self.data.get(self.tab, [])
        box = tk.Frame(self.inner, bg=T["sumbg"], highlightbackground=T["sumbd"], highlightthickness=1)
        box.pack(fill="x", padx=14, pady=(0, 10))
        tk.Label(box, text="✦ GÜNÜN ÖZETİ", fg=T["sumh"], bg=T["sumbg"], font=self.f(8, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        tk.Label(box, text=daily_summary(cl) if self.data else "Kaynaklar taranıyor, biraz bekleyin…",
                 fg=T["sumtxt"], bg=T["sumbg"], font=self.f(9), wraplength=wrap, justify="left"
                 ).pack(anchor="w", padx=12, pady=(0, 10))
        for n, c in enumerate(cl[:25], 1):
            tk.Frame(self.inner, bg=T["line"], height=1).pack(fill="x", padx=14)
            row = tk.Frame(self.inner, bg=T["bg"], cursor="hand2")
            row.pack(fill="x", padx=14, pady=8)
            tk.Label(row, text=str(n), fg=T["rank"], bg=T["bg"], font=self.f(13, "bold"), width=2, anchor="nw").pack(side="left", anchor="n")
            body = tk.Frame(row, bg=T["bg"])
            body.pack(side="left", fill="x", expand=True)
            tk.Label(body, text=c["title"], fg=T["text"], bg=T["bg"], font=self.f(10, "bold"),
                     wraplength=wrap - 20, justify="left").pack(anchor="w")
            if c["summary"]:
                tk.Label(body, text=c["summary"], fg=T["sub"], bg=T["bg"], font=self.f(9),
                         wraplength=wrap - 20, justify="left").pack(anchor="w", pady=(2, 0))
            tags = tk.Frame(body, bg=T["bg"])
            tags.pack(anchor="w", pady=(5, 0))
            self.chip(tags, f"{c['n']} kaynak", T["cg"])
            if c["blogs"]:
                self.chip(tags, f"+{c['blogs']} blog", T["cb"])
            if c["hot"]:
                self.chip(tags, "🔥 Yükselişte", T["ch"])
            self.bind_row(row, c["link"], T)
        self.canvas.yview_moveto(0)
        self.tickers[0].set(self.ticks[0])
        self.tickers[1].set(self.ticks[1])

    def bind_row(self, row, link, T):
        def walk(w):
            yield w
            for ch in w.winfo_children():
                yield from walk(ch)
        ws = list(walk(row))
        def paint(color):
            for w in ws:
                if w.cget("bg") in (T["bg"], T["hover"]):
                    w.configure(bg=color)
        for w in ws:
            w.bind("<Button-1>", lambda e: link and webbrowser.open(link))
            w.bind("<Enter>", lambda e: paint(T["hover"]))
            w.bind("<Leave>", lambda e: paint(T["bg"]))

    # --- eylemler
    def select_tab(self, i):
        self.tab = i
        self.build()

    def toggle_theme(self):
        self.set_theme("acik" if self.th is THEMES["koyu"] else "koyu")

    def toggle_top(self):
        self.cfg["ustte"] = not self.cfg["ustte"]
        self.root.attributes("-topmost", self.cfg["ustte"])
        save_json(CFG_FILE, self.cfg)
        self.build()

    def settings(self):
        T = self.th
        w = tk.Toplevel(self.root, bg=T["bg"])
        w.title("Ayarlar")
        w.resizable(False, False)
        w.transient(self.root)
        lab = dict(bg=T["bg"], fg=T["text"], font=self.f(9))
        tk.Label(w, text="Tema", **lab).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 4))
        v = tk.StringVar(value=self.cfg["tema"])
        fr = tk.Frame(w, bg=T["bg"]); fr.grid(row=0, column=1, sticky="w", padx=10, pady=(14, 4))
        for key, txt in (("koyu", "Koyu"), ("acik", "Açık"), ("sistem", "Sistem")):
            tk.Radiobutton(fr, text=txt, value=key, variable=v, bg=T["bg"], fg=T["text"], selectcolor=T["tab"],
                           activebackground=T["bg"], font=self.f(9)).pack(side="left")
        tk.Label(w, text="Tarama aralığı (dk)", **lab).grid(row=1, column=0, sticky="w", padx=14, pady=4)
        sp = tk.Spinbox(w, from_=3, to=120, width=6, font=self.f(9))
        sp.delete(0, "end"); sp.insert(0, self.cfg["aralik_dk"])
        sp.grid(row=1, column=1, sticky="w", padx=10)
        top = tk.BooleanVar(value=self.cfg["ustte"])
        tk.Checkbutton(w, text="Pencere hep üstte kalsın", variable=top, bg=T["bg"], fg=T["text"],
                       selectcolor=T["tab"], activebackground=T["bg"], font=self.f(9)
                       ).grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=4)
        tk.Label(w, text="Kaynak eklemek/çıkarmak için listeyi düzenleyin,\nkaydedip ⟳ ile yeniden tarayın.",
                 bg=T["bg"], fg=T["sub"], font=self.f(8), justify="left").grid(row=3, column=0, columnspan=2, sticky="w", padx=14, pady=(8, 2))

        def open_feeds():
            try:
                os.startfile(FEED_FILE)
            except Exception:
                webbrowser.open("file:///" + FEED_FILE)

        def ok():
            try:
                self.cfg["aralik_dk"] = max(3, int(sp.get()))
            except ValueError:
                pass
            self.cfg["ustte"] = top.get()
            self.cfg["tema"] = v.get()
            self.root.attributes("-topmost", self.cfg["ustte"])
            save_json(CFG_FILE, self.cfg)
            w.destroy()
            self.build()
            self.schedule()

        b = tk.Frame(w, bg=T["bg"]); b.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=12)
        self.btn(b, "Kaynakları düzenle", open_feeds, T["tab"], T["text"], self.f(9), padx=10, pady=3).pack(side="left")
        self.btn(b, "Kaydet", ok, T["accent"], "white", self.f(9, "bold"), padx=14, pady=3).pack(side="right")

    # --- tarama
    def schedule(self):
        if self.timer:
            self.root.after_cancel(self.timer)
        self.timer = self.root.after(self.cfg["aralik_dk"] * 60_000, self.refresh)

    def refresh(self):
        if self.busy:
            return
        self.busy = True
        self.meta = "Taranıyor…"
        try:
            self.meta_l.config(text=self.meta)
        except tk.TclError:
            pass
        threading.Thread(target=self.worker, daemon=True).start()
        self.schedule()

    def worker(self):
        feeds = load_json(FEED_FILE, DEFAULT_FEEDS) or DEFAULT_FEEDS
        items, ok = [], 0
        with ThreadPoolExecutor(max_workers=8) as ex:
            for res in ex.map(fetch, feeds):
                if res:
                    ok += 1
                    items.extend(res)
        data = {}
        for i, (_, cats) in enumerate(TABS):
            data[i] = cluster([it for it in items if it["cat"] in cats])
        tr = cluster([it for it in items if it["cat"] in ("turkiye", "ekonomi", "spor")])
        gl = cluster([it for it in items if it["cat"] in ("global", "dunya")])
        ticks = ([(c["title"], c["link"]) for c in tr[:15]], [(c["title"], c["link"]) for c in gl[:15]])
        srcs = len({i["src"] for i in items})
        meta = f"Son tarama: {time.strftime('%H:%M')} · {srcs} kaynak · {len(items):,} haber".replace(",", ".")
        self.q.put((data, ticks, meta, ok))

    def poll(self):
        try:
            data, ticks, meta, ok = self.q.get_nowait()
            self.busy = False
            self.meta = meta if ok else "Bağlantı yok — kaynaklara ulaşılamadı"
            if ok:
                self.data, self.ticks = data, ticks
            self.build()
        except queue.Empty:
            pass
        self.root.after(500, self.poll)

    def quit(self):
        try:
            self.cfg["geometri"] = self.root.geometry()
            save_json(CFG_FILE, self.cfg)
        finally:
            self.root.destroy()


if __name__ == "__main__":
    App()
