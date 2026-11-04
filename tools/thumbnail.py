"""YouTube用サムネイル（1280x720 PNG）を quiz.json から作る。

build_quiz.py から呼ばれ OUTDIR/thumbnail.png を出力する。単体でも実行できる:
  python3 tools/thumbnail.py quiz.json thumbnail.png

キーワードは quiz.json の "thumb"（例 ["密度","有機物","気体"]）。
無ければ title の（…）内を「・」で分けて使う。最大3個。
"""
import html, json, re, sys
from playwright.sync_api import sync_playwright

COLORS = {"物理": "#2563eb", "化学": "#ea580c", "生物": "#16a34a", "地学": "#7c3aed"}
FONT = "'Noto Sans CJK JP','Noto Sans JP',sans-serif"


def keywords(spec):
    kw = spec.get("thumb")
    if not kw:
        m = re.search(r"（(.+?)）", spec.get("title", ""))
        kw = re.split(r"[・、]", m.group(1)) if m else []
    return [k.strip() for k in kw if k.strip()][:3]


def body(spec):
    e = html.escape
    acc = COLORS.get(spec["field"], "#0d9488")
    # 単元名は長い日があるので、学年とテーマを分けて字数でサイズを決める
    grade, _, theme = spec["unit"].partition(" ")
    if not theme:
        grade, theme = "", spec["unit"]
    size = 124 if len(theme) <= 8 else 104 if len(theme) <= 10 else 86 if len(theme) <= 13 else 70
    grade_html = f"<span class='g'>{e(grade)}</span>" if grade else ""
    chips = "".join(f"<span class='c'>{e(k)}</span>" for k in keywords(spec))
    return f"""<html><head><meta charset='utf-8'><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1280px;height:720px;overflow:hidden;font-family:{FONT};background:{acc};color:#fff;position:relative}}
.top{{position:absolute;left:56px;right:56px;top:40px;display:flex;justify-content:space-between;align-items:center}}
.k{{font-size:50px;font-weight:900}}
.f{{font-size:46px;font-weight:900;background:#fff;color:{acc};padding:4px 30px;border-radius:14px}}
.day{{position:absolute;left:56px;top:122px;font-size:118px;font-weight:900;line-height:1.1}}
.panel{{position:absolute;left:0;right:0;top:268px;height:318px;background:#fffdf6;color:#1f2937;padding:26px 56px;
        display:flex;flex-direction:column;justify-content:center}}
.u{{font-size:{size}px;font-weight:900;line-height:1.2;white-space:nowrap}}
.g{{font-size:56px;color:{acc};margin-right:22px}}
.cs{{margin-top:22px;white-space:nowrap}}
.c{{display:inline-block;font-size:42px;font-weight:800;color:{acc};border:5px solid {acc};border-radius:40px;padding:0 26px;margin-right:16px}}
.left{{position:absolute;left:56px;right:56px;bottom:26px;font-size:62px;font-weight:900;text-align:right}}
.left b{{color:#fde047;font-size:84px;font-weight:900}}
</style></head><body>
<div class='top'><span class='k'>沖縄県立高校入試 理科</span><span class='f'>{e(spec['field'])}</span></div>
<div class='day'>一問一答 Day{spec['day']}</div>
<div class='panel'><div class='u'>{grade_html}{e(theme)}</div><div class='cs'>{chips}</div></div>
<div class='left'>{"いよいよ今日が入試" if spec['days_left'] == 0 else f"入試まで あと <b>{spec['days_left']}</b> 日"}</div>
</body></html>"""


def make(spec, path):
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 720})
        pg.set_content(body(spec))
        pg.wait_for_timeout(80)
        # 単元名は1行に収まるまで縮める。キーワードがはみ出す場合は警告する
        over = pg.evaluate("""() => {
            const u = document.querySelector('.u'), w = 1280 - 112;
            for (let s = parseInt(getComputedStyle(u).fontSize); u.scrollWidth > w && s > 40; s -= 2) u.style.fontSize = s + 'px';
            return [...document.querySelectorAll('.u,.cs')].filter(el => el.scrollWidth > w).map(el => el.className);
        }""")
        pg.screenshot(path=path)
        b.close()
    if over:
        print(f"WARN thumbnail overflow: {over}（quiz.json の thumb を短くする）", flush=True)


if __name__ == "__main__":
    make(json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2])
