"""理科 一問一答の動画を quiz.json から作る（沖縄県立高校入試対策）。

使い方: python3 tools/build_quiz.py quiz.json OUTDIR
出力: OUTDIR/video.mp4, OUTDIR/thumbnail.png, OUTDIR/title.txt, OUTDIR/desc.txt, OUTDIR/frames/*.png
前提: tools/setup.sh 済み（VOICEVOX・Playwright・ffmpeg）

quiz.json の形:
{
  "day": 1,                          # 通し番号（rika/history の件数+1）
  "date": "2026/11/04（水）",
  "days_left": 119,                  # 2027/3/3 までの日数
  "field": "化学",                   # 物理 / 化学 / 生物 / 地学 / 総合
  "unit": "中1 身のまわりの物質",    # 画面表示用
  "unit_n": "ちゅういち、身のまわりの物質",  # 読み上げ用
  "title": "YouTubeタイトル（100字以内）",
  "intro": "概要欄の冒頭（1〜3行）",
  "hashtags": "#高校受験 #理科 ...",
  "thumb": ["サムネのキーワード", "最大3個"],  # 省略時は title の（…）から作る
  "questions": [
    {"q": "画面の問題文", "qn": "読み上げる問題文",
     "a": "画面の答え（短く）", "an": "読み上げる答え＋一言解説（『答えは、〜。』で始める）",
     "note": "画面の一言解説（1行、なければ空）", "review": false}
  ],
  "summary": ["今日のポイント1", "ポイント2", "ポイント3"],
  "summary_n": "まとめの読み上げ"
}
qn / an / summary_n は、化学式・記号・単位・数字を読みで書く（例：エイチツーオー、5オーム、さんじゅうど）。
"""
import os, sys, html, json, wave, subprocess
import pyopenjtalk
from playwright.sync_api import sync_playwright
from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
import thumbnail

VV = os.environ.get("VV_DIR", "/home/claude/vv")
Q_VOICE, A_VOICE = 3, 2      # 出題：ずんだもん / 答え：四国めたん
SPEED = 1.05
THINK = 5                    # 考える秒数

spec = json.load(open(sys.argv[1], encoding="utf-8"))
OUT = sys.argv[2]
FR = os.path.join(OUT, "frames"); os.makedirs(FR, exist_ok=True)
QS = spec["questions"]
ACC = {"物理": "#2563eb", "化学": "#ea580c", "生物": "#16a34a", "地学": "#7c3aed"}.get(spec["field"], "#0d9488")

FONT = "'Noto Sans CJK JP','Noto Sans JP',sans-serif"
CSS = f"""
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1920px;height:1080px;font-family:{FONT};background:#fffdf6;color:#1f2937;overflow:hidden}}
.top{{position:absolute;left:0;right:0;top:0;height:110px;background:{ACC};color:#fff;display:flex;align-items:center;
      justify-content:space-between;padding:0 80px;font-size:42px;font-weight:700}}
.wrap{{position:absolute;left:120px;right:120px;top:170px;bottom:120px}}
.no{{font-size:56px;font-weight:900;color:{ACC}}}
.tag{{display:inline-block;margin-left:24px;font-size:34px;padding:4px 20px;border-radius:30px;background:#fde68a;color:#78350f;vertical-align:middle}}
.q{{font-size:76px;line-height:1.45;font-weight:800;margin-top:36px}}
.qs{{font-size:44px;line-height:1.5;color:#6b7280;margin-top:40px}}
.ans{{font-size:44px;color:#6b7280;margin-top:36px}}
.a{{font-size:120px;font-weight:900;color:{ACC};margin:10px 0 30px;line-height:1.2}}
.note{{font-size:48px;line-height:1.5;padding:24px 32px;background:#f3f4f6;border-left:12px solid {ACC};border-radius:8px}}
.cd{{position:absolute;right:120px;bottom:150px;width:220px;height:220px;border-radius:50%;background:{ACC};color:#fff;
     font-size:130px;font-weight:900;display:flex;align-items:center;justify-content:center}}
.bar{{position:absolute;left:0;bottom:0;height:24px;background:{ACC}}}
.foot{{position:absolute;left:120px;right:120px;bottom:44px;display:flex;justify-content:space-between;font-size:30px;color:#9ca3af}}
.cover{{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:0 140px;background:{ACC};color:#fff}}
.cover .k{{font-size:54px;font-weight:700;opacity:.9}}
.cover .t{{font-size:140px;font-weight:900;margin:10px 0}}
.cover .u{{font-size:80px;font-weight:800;margin:10px 0 40px}}
.cover .d{{font-size:52px}}
.cover .left{{display:inline-block;margin-top:36px;font-size:60px;font-weight:900;background:#fff;color:{ACC};padding:10px 36px;border-radius:16px}}
ul{{list-style:none;margin-top:40px}}
li{{font-size:54px;line-height:1.5;margin-bottom:26px;padding-left:56px;position:relative}}
li:before{{content:'✔';position:absolute;left:0;color:{ACC}}}
"""
e = html.escape
HEAD = f"<div class='top'><span>沖縄県立高校入試 理科 一問一答</span><span>{e(spec['field'])}｜{e(spec['unit'])}</span></div>"
FOOT = lambda r: f"<div class='foot'><span>Day {spec['day']}　{e(spec['date'])}</span><span>{r}</span></div>"
page = lambda b: f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{b}</body></html>"

def qbody(i, q, extra=""):
    tag = "<span class='tag'>復習</span>" if q.get("review") else ""
    return (HEAD + f"<div class='wrap'><div class='no'>第{i+1}問{tag}</div><div class='q'>{e(q['q'])}</div>{extra}</div>"
            + FOOT(f"{i+1} / {len(QS)}"))

# 1) 画像
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1920, "height": 1080})
    def shot(name, body):
        pg.set_content(page(body)); pg.wait_for_timeout(80); pg.screenshot(path=f"{FR}/{name}.png")
    shot("open", f"<div class='cover'><div class='k'>沖縄県立高校入試 理科</div><div class='t'>一問一答 Day {spec['day']}</div>"
                 f"<div class='u'>{e(spec['field'])}｜{e(spec['unit'])}</div><div class='d'>{e(spec['date'])}　全{len(QS)}問・{THINK}秒で答えよう</div>"
                 f"<div><span class='left'>入試まで あと {spec['days_left']} 日</span></div></div>")
    for i, q in enumerate(QS):
        shot(f"q{i:02d}", qbody(i, q))
        for k in range(THINK, 0, -1):
            w = int(1920 * (THINK - k + 1) / THINK)
            shot(f"q{i:02d}_c{k}", qbody(i, q) + f"<div class='cd'>{k}</div><div class='bar' style='width:{w}px'></div>")
        note = f"<div class='note'>{e(q['note'])}</div>" if q.get("note") else ""
        shot(f"a{i:02d}", HEAD + f"<div class='wrap'><div class='no'>第{i+1}問</div><div class='qs'>{e(q['q'])}</div>"
                             f"<div class='ans'>答え</div><div class='a'>{e(q['a'])}</div>{note}</div>" + FOOT(f"{i+1} / {len(QS)}"))
    lis = "".join(f"<li>{e(x)}</li>" for x in spec.get("summary", []))
    shot("end", HEAD + f"<div class='wrap'><div class='no'>今日のまとめ</div><ul>{lis}</ul></div>"
                + FOOT(f"入試まで あと {spec['days_left']} 日"))
    b.close()
thumbnail.make(spec, f"{OUT}/thumbnail.png")

# 2) 音声と動画
ort = Onnxruntime.load_once(filename=f"{VV}/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so.1.17.3")
syn = Synthesizer(ort, OpenJtalk(os.path.join(os.path.dirname(pyopenjtalk.__file__), "open_jtalk_dic_utf_8-1.11")))
with VoiceModelFile.open(f"{VV}/vvms/0.vvm") as m: syn.load_voice_model(m)

ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-r", "30", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2"]
segs, n = [], 0
def seg(img, text=None, voice=Q_VOICE, dur=None, pad=0.8):
    """画像1枚の区間を作る。text があれば読み上げ、なければ dur 秒の無音。戻り値は実際の長さ。"""
    global n
    fn = f"{FR}/seg{n:03d}.mp4"; n += 1
    if text:
        wav = fn[:-4] + ".wav"
        q = syn.create_audio_query(text, voice); q.speed_scale = SPEED
        open(wav, "wb").write(syn.synthesis(q, voice))
        with wave.open(wav) as w: dur = w.getnframes() / w.getframerate() + pad
        ain = ["-i", wav]; af = ["-af", f"adelay=250|250,apad,atrim=duration={dur:.2f}"]
    else:
        ain = ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]; af = []
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", f"{FR}/{img}.png", *ain,
                    "-vf", f"trim=duration={dur:.2f},format=yuv420p", *af, *ENC, "-t", f"{dur:.2f}", fn], check=True)
    segs.append(fn)
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", fn],
                                capture_output=True, text=True).stdout)

opening_n = (f"沖縄県立高校入試、理科の一問一答、デイ{spec['day']}。今日のテーマは、{spec['unit_n']}です。"
             f"入試まで、あと{spec['days_left']}日。問題のあと、{THINK}秒で答えを考えてね。")
t = seg("open", opening_n, Q_VOICE)
starts = []
for i, q in enumerate(QS):
    starts.append(t)
    t += seg(f"q{i:02d}", f"第{i+1}問。" + q["qn"], Q_VOICE, pad=0.3)
    for k in range(THINK, 0, -1): t += seg(f"q{i:02d}_c{k}", dur=1.0)
    t += seg(f"a{i:02d}", q["an"], A_VOICE)
    print(i + 1, f"{t:.0f}s", flush=True)
end_start = t
t += seg("end", spec["summary_n"] + "　また明日も、いっしょにがんばろう。", A_VOICE, pad=1.5)

with open(f"{FR}/list.txt", "w") as f: f.writelines(f"file '{x}'\n" for x in segs)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{FR}/list.txt",
                "-c", "copy", "-movflags", "+faststart", f"{OUT}/video.mp4"], check=True)

# 3) タイトルと概要欄
def mmss(x): x = int(x); return f"{x//60:02d}:{x%60:02d}"
cut = lambda s, k=28: s if len(s) <= k else s[:k] + "…"
chap = ["00:00 オープニング"] + [f"{mmss(s)} 第{i+1}問 {cut(q['q'])}" for i, (s, q) in enumerate(zip(starts, QS))] + [f"{mmss(end_start)} 今日のまとめ"]
answers = "\n".join(f"第{i+1}問：{q['a']}" for i, q in enumerate(QS))
desc = (f"{spec.get('intro','').strip()}\n\n" + "\n".join(chap) +
        f"\n\n■ 答え一覧（見る前に動画で解いてみよう）\n{answers}\n\n"
        "沖縄県立高校の一般入試（理科）に向けて、中学1〜3年の理科を毎日5分の一問一答で復習するチャンネルです。毎朝6時30分ごろ更新。\n"
        "※ 問題はオリジナルです。学校や教科書の表記と違うときは、学校で習った表記を優先してください。\n"
        "音声：VOICEVOX:ずんだもん / VOICEVOX:四国めたん\n\n" + spec.get("hashtags", "#高校受験 #理科 #一問一答")
        ).replace("<", "＜").replace(">", "＞")
title = spec["title"].replace("<", "＜").replace(">", "＞")[:100]
open(f"{OUT}/title.txt", "w", encoding="utf-8").write(title)
open(f"{OUT}/desc.txt", "w", encoding="utf-8").write(desc[:4900])
print(f"done {t:.1f}s  title={len(title)} desc={len(desc)}")
