"""
판타지 소설 작성 현황 대시보드 v3
목차 TOC 사이드바 · 탭 네비게이션 · 집필 카드 · ApexCharts
사용: python dashboard.py  →  dashboard.html
"""
import json, sys, io, re
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent


# ── 데이터 ────────────────────────────────────────────────────────────────────

def load_json(path, fallback=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return fallback if fallback is not None else {}


def collect_data():
    cfg = load_json(BASE_DIR / "config" / "story_config.json")

    ch_dir = BASE_DIR / "data" / "chapters"
    chapters = []
    if ch_dir.exists():
        for f in sorted(ch_dir.glob("chapter_*.json")):
            ch = load_json(f)
            if ch and "_guide" not in ch:
                chapters.append(ch)

    cp = BASE_DIR / "data" / "characters" / "characters.json"
    if not cp.exists():
        cp = BASE_DIR / "data" / "characters" / "characters_template.json"
    chars = load_json(cp)

    pp = BASE_DIR / "data" / "plot" / "plot.json"
    if not pp.exists():
        pp = BASE_DIR / "data" / "plot" / "plot_template.json"
    plot = load_json(pp)

    wp = BASE_DIR / "data" / "world" / "world.json"
    if not wp.exists():
        wp = BASE_DIR / "data" / "world" / "world_template.json"
    world = load_json(wp)

    def get_files(sub, ext):
        d = BASE_DIR / "output" / sub
        return [f.name for f in sorted(d.glob("*." + ext))] if d.exists() else []

    target = cfg.get("target_chapters", 50)
    wpch   = cfg.get("words_per_chapter", 3000)
    n      = len(chapters)
    tw     = sum(c.get("word_count", 0) for c in chapters)
    wt     = target * wpch
    pct    = round(n / target * 100, 1) if target else 0
    wpct   = round(tw / wt * 100, 1) if wt else 0
    written_set = {c["chapter"] for c in chapters}
    next_ch = max(written_set) + 1 if written_set else 1

    cumulative, running = [], 0
    for c in chapters:
        running += c.get("word_count", 0)
        cumulative.append(running)

    return {
        "cfg": cfg,
        "chapters": chapters,
        "chars": chars,
        "plot": plot,
        "world": world,
        "outputs": {
            "txt":  get_files("txt",  "txt"),
            "epub": get_files("epub", "epub"),
            "pdf":  get_files("pdf",  "pdf"),
        },
        "chart_data": {
            "pct":        pct,
            "chNums":     [c["chapter"] for c in chapters],
            "chWords":    [c.get("word_count", 0) for c in chapters],
            "cumulative": cumulative,
        },
        "s": {
            "n": n, "target": target, "pct": pct, "remain": target - n,
            "tw": tw, "wt": wt, "wpct": wpct,
            "avg": tw // n if n else 0, "wpch": wpch,
            "next_ch": next_ch,
            "last_n":    chapters[-1]["chapter"] if chapters else 0,
            "last_date": chapters[-1].get("created_at", "")[:10] if chapters else "—",
        },
    }


# ── HTML 조각 생성 ─────────────────────────────────────────────────────────────

def _is_template(text):
    """템플릿 기본값 여부 확인"""
    return not text or any(k in text for k in ["이름", "제목", "입력", "예:", "설명", "_guide"])


def writing_card_html(data):
    s       = data["s"]
    plot    = data["plot"]
    cfg     = data["cfg"]
    next_ch = s["next_ch"]
    wpch    = s["wpch"]

    if next_ch > s["target"]:
        return (
            '<div class="wc done-wc">'
            '<div class="wc-icon">🎉</div>'
            '<div class="wc-big">완성!</div>'
            '<div class="wc-sub">목표 ' + str(s["target"]) + '화를 모두 완성했습니다</div>'
            '</div>'
        )

    outlines = plot.get("chapter_outlines", [])
    ol = next((o for o in outlines if o.get("chapter") == next_ch), None)

    title_h   = ""
    summary_h = ""
    tone_h    = ""
    scene_h   = ""

    if ol:
        t = ol.get("title", "")
        if t and not _is_template(t):
            title_h = '<div class="wc-ch-title">' + t + '</div>'
        sm = (ol.get("summary") or "")[:140]
        if sm and not _is_template(sm):
            summary_h = '<p class="wc-summary">' + sm + '</p>'
        et = ol.get("emotional_tone", "")
        if et and not _is_template(et):
            tone_h = '<div class="wc-tone"><span class="wc-tone-lb">감정 톤</span>' + et + '</div>'
        ks = ol.get("key_scene", "")
        if ks and not _is_template(ks):
            scene_h = '<div class="wc-tone"><span class="wc-tone-lb">핵심 장면</span>' + ks + '</div>'

    return (
        '<div class="wc">'
        '<div class="wc-left">'
        '<div class="wc-label">✏️ 다음에 쓸 화</div>'
        '<div class="wc-big">' + str(next_ch) + '화</div>'
        + title_h +
        '</div>'
        '<div class="wc-right">'
        + summary_h + tone_h + scene_h +
        '<div class="wc-footer">'
        '<span class="wc-goal">목표 ' + f'{wpch:,}' + '자</span>'
        '<code class="wc-cmd">python main.py chapter write</code>'
        '</div>'
        '</div>'
        '</div>'
    )


def toc_chapters_html(data):
    chapters   = data["chapters"]
    plot       = data["plot"]
    s          = data["s"]
    written    = {c["chapter"]: c.get("title","") for c in chapters}
    next_ch    = s["next_ch"]
    arcs       = plot.get("arcs", [])
    target     = s["target"]

    items = []

    def ch_item(i):
        t = (written.get(i, "") or "")[:18]
        if i in written:
            label = "✅ " + str(i) + "화" + (" " + t if t and not _is_template(t) else "")
            return '<a class="toc-ch ch-done" data-goto="chapters">' + label + '</a>'
        elif i == next_ch:
            return '<a class="toc-ch ch-next" data-goto="chapters">✏️ ' + str(i) + '화 <span class="ch-next-badge">다음</span></a>'
        else:
            return '<a class="toc-ch ch-todo" data-goto="chapters">○ ' + str(i) + '화</a>'

    if arcs and not _is_template(arcs[0].get("arc_name","")):
        for arc in arcs:
            arc_name = arc.get("arc_name","")
            chs_str  = str(arc.get("chapters",""))
            try:
                start, end = map(int, chs_str.split("-"))
            except Exception:
                continue
            items.append('<div class="toc-arc-hd">' + arc_name + ' <span class="toc-arc-range">' + chs_str + '화</span></div>')
            show_end = min(end, max(next_ch + 1, start + 2))
            for i in range(start, show_end + 1):
                items.append(ch_item(i))
            remaining = end - show_end
            if remaining > 0:
                items.append('<div class="toc-more">… ' + str(remaining) + '화 더</div>')
    else:
        show_up = min(next_ch + 3, target)
        for i in range(1, show_up + 1):
            items.append(ch_item(i))
        if target > show_up:
            items.append('<div class="toc-more">… 총 ' + str(target) + '화</div>')

    return "\n".join(items) if items else '<div class="toc-empty">챕터 정보 없음</div>'


def toc_chars_html(chars):
    mains = chars.get("main_characters", [])
    subs  = chars.get("sub_characters", [])
    items = []
    for c in mains:
        name = c.get("name","")
        if name and not _is_template(name):
            role = c.get("role","주인공")
            items.append('<div class="toc-char"><span class="tc-av main-av">' + name[0] + '</span>'
                         + name + ' <span class="tc-role">' + role + '</span></div>')
    for c in subs:
        name = c.get("name","")
        if name and not _is_template(name):
            role = c.get("role","조연")
            items.append('<div class="toc-char"><span class="tc-av sub-av">' + name[0] + '</span>'
                         + name + ' <span class="tc-role">' + role + '</span></div>')
    return "\n".join(items) if items else '<div class="toc-empty">캐릭터 미설정</div>'


def toc_sidebar_html(data):
    """집필 순서 기반 사이드바 TOC 생성"""
    cfg     = data["cfg"]
    s       = data["s"]
    world   = data["world"]
    chars   = data["chars"]
    plot    = data["plot"]

    # 각 단계 완료 여부
    plan_ok   = not _is_template(cfg.get("title",""))
    world_ok  = not _is_template(world.get("world_name",""))
    chars_ok  = any(not _is_template(c.get("name",""))
                    for c in chars.get("main_characters",[]))
    arcs      = [a for a in plot.get("arcs",[])
                 if not _is_template(a.get("arc_name",""))]
    plot_ok   = len(arcs) > 0
    output_ok = any(len(v) > 0 for v in data["outputs"].values())

    def badge(ok):
        return '<span class="step-done">완료</span>' if ok else '<span class="step-todo">미완</span>'

    def group(icon, label, body, opened=False, badge_html=""):
        open_attr = " open" if opened else ""
        return (
            '<details class="toc-group"' + open_attr + '>'
            + '<summary class="toc-hd">'
            + '<span class="toc-arr">▶</span>'
            + '<span class="toc-step-label">' + icon + ' ' + label + '</span>'
            + badge_html
            + '</summary>'
            + '<div class="toc-body">' + body + '</div>'
            + '</details>'
        )

    def info_row(key, val, dim=False):
        vcls = ' class="ti-v dim"' if dim else ' class="ti-v"'
        return ('<div class="toc-info-row">'
                '<span class="ti-k">' + key + '</span>'
                '<span' + vcls + '>' + val + '</span>'
                '</div>')

    # ① 기획
    title  = cfg.get("title","")
    genre  = cfg.get("genre","")
    plan_body = (
        info_row("제목", title[:18] if plan_ok else "미설정", dim=not plan_ok)
        + info_row("장르", genre if genre else "미설정", dim=not genre)
        + info_row("목표", str(s["target"]) + "화 · " + f'{s["wpch"]:,}' + "자/화")
        + '<a class="toc-ch" data-goto="overview">→ 전반 현황 보기</a>'
    )

    # ② 세계관
    wname = world.get("world_name","")
    magic = world.get("magic_system",{})
    m_name = magic.get("name","") if isinstance(magic, dict) else ""
    world_body = (
        info_row("세계", wname[:18] if world_ok else "미설정", dim=not world_ok)
        + (info_row("마법", m_name[:18]) if m_name and not _is_template(m_name) else "")
        + '<a class="toc-ch" data-goto="world">→ 세계관 설정 보기</a>'
    )

    # ③ 캐릭터
    mains = [c for c in chars.get("main_characters",[])
             if not _is_template(c.get("name",""))]
    subs  = [c for c in chars.get("sub_characters",[])
             if not _is_template(c.get("name",""))]
    if mains or subs:
        chars_body = toc_chars_html(chars) + '<a class="toc-ch" data-goto="chars">→ 캐릭터 전체 보기</a>'
    else:
        chars_body = '<div class="toc-empty">캐릭터 미설정</div><a class="toc-ch" data-goto="chars">→ 캐릭터 설정 보기</a>'

    # ④ 줄거리
    if arcs:
        plot_body = (
            "".join(
                '<div class="toc-arc-hd">'
                + a.get("arc_name","")[:20]
                + ' <span class="toc-arc-range">' + str(a.get("chapters","")) + '화</span>'
                + '</div>'
                for a in arcs
            )
            + '<a class="toc-ch" data-goto="plot">→ 줄거리 전체 보기</a>'
        )
    else:
        plot_body = '<div class="toc-empty">플롯 미설정</div><a class="toc-ch" data-goto="plot">→ 줄거리 설정 보기</a>'

    # ⑤ 집필 (항상 열림)
    write_label = "집필  " + str(s["n"]) + "/" + str(s["target"]) + "화"
    write_body  = toc_chapters_html(data)

    # ⑥ 출력
    total_files = sum(len(v) for v in data["outputs"].values())
    output_body = (
        info_row("파일", str(total_files) + "개", dim=not output_ok)
        + '<a class="toc-ch" data-goto="output">→ 파일 내보내기</a>'
    )

    return (
        group("①", "기획",   plan_body,  badge_html=badge(plan_ok))
        + group("②", "세계관", world_body, badge_html=badge(world_ok))
        + group("③", "캐릭터", chars_body, badge_html=badge(chars_ok))
        + group("④", "줄거리", plot_body,  badge_html=badge(plot_ok))
        + group("⑤", write_label, write_body, opened=True)
        + group("⑥", "출력",   output_body, badge_html=badge(output_ok))
    )


def chapter_rows(chapters):
    if not chapters:
        return '<tr><td colspan="4" class="empty-cell">아직 작성된 챕터가 없습니다</td></tr>'
    rows = []
    for c in reversed(chapters):
        w = c.get("word_count", 0)
        d = (c.get("created_at") or "")[:10] or "—"
        rows.append(
            "<tr>"
            + '<td class="td-acc">' + str(c["chapter"]) + "화</td>"
            + "<td>" + c.get("title","") + "</td>"
            + '<td class="td-r">' + f"{w:,}" + "</td>"
            + '<td class="td-d">' + d + "</td>"
            + "</tr>"
        )
    return "\n".join(rows)


def chars_grid_html(chars):
    mains = chars.get("main_characters", [])
    subs  = chars.get("sub_characters", [])
    if not mains and not subs:
        return '<div class="empty-state">캐릭터 정보가 없습니다<span>data/characters/characters_template.json 을 수정하세요</span></div>'
    items = []
    for c in mains:
        name  = c.get("name","")
        tpl   = _is_template(name)
        role  = c.get("role","주인공")
        age   = c.get("age","")
        pers  = (c.get("personality") or "")[:80]
        motiv = (c.get("motivation") or "")[:80]
        ab    = c.get("abilities",[])[:3]
        av    = name[0] if name and not tpl else "?"
        items.append(
            '<div class="char-card' + (" char-tpl" if tpl else "") + '">'
            + '<div class="char-top">'
            + '<div class="char-av av-main">' + av + '</div>'
            + '<div>'
            + '<div class="char-name">' + (name or "(미설정)") + '</div>'
            + '<span class="char-role role-main">' + role + '</span>'
            + (' <span class="char-age">' + str(age) + '세</span>' if age else "")
            + '</div></div>'
            + ('<p class="char-desc">' + pers + '</p>' if pers and not tpl else "")
            + ('<p class="char-motiv">목표: ' + motiv + '</p>' if motiv and not tpl else "")
            + (('<div class="char-abs">' + "".join('<span class="ab">' + a + '</span>' for a in ab) + '</div>') if ab and not tpl else "")
            + '</div>'
        )
    for c in subs:
        name = c.get("name","")
        tpl  = _is_template(name)
        role = c.get("role","조연")
        rel  = (c.get("relationship_to_main") or "")[:80]
        av   = name[0] if name and not tpl else "?"
        items.append(
            '<div class="char-card sub-card' + (" char-tpl" if tpl else "") + '">'
            + '<div class="char-top">'
            + '<div class="char-av av-sub">' + av + '</div>'
            + '<div>'
            + '<div class="char-name">' + (name or "(미설정)") + '</div>'
            + '<span class="char-role role-sub">' + role + '</span>'
            + '</div></div>'
            + ('<p class="char-desc">' + rel + '</p>' if rel and not tpl else "")
            + '</div>'
        )
    return "\n".join(items)


def world_tab_html(world, cfg):
    ws = cfg.get("world_setting", {})
    name     = world.get("world_name","")
    overview = (world.get("overview") or "")[:300]
    history  = (world.get("history") or "")[:200]
    conflict = (world.get("central_conflict") or "")[:160]
    culture  = (world.get("culture_and_society") or "")[:200]
    magic    = world.get("magic_system", {})
    geo      = world.get("geography", {})
    factions = world.get("factions", [])

    def safe(t): return t if t and not _is_template(t) else ""

    # magic block
    magic_html = ""
    m_name  = safe(magic.get("name",""))
    m_src   = safe(magic.get("power_source",""))
    m_rules = [r for r in magic.get("rules",[]) if safe(r)]
    m_lims  = [r for r in magic.get("limitations",[]) if safe(r)]
    if m_name or m_rules:
        magic_html = (
            '<div class="info-block">'
            '<div class="info-block-title">⚡ 마법 체계' + (' — ' + m_name if m_name else '') + '</div>'
            + ('<div class="info-sub">원천: ' + m_src + '</div>' if m_src else "")
            + ('<ul class="info-list">' + "".join('<li>' + r + '</li>' for r in m_rules) + '</ul>' if m_rules else "")
            + ('<div class="info-sub lim">한계: ' + " / ".join(m_lims) + '</div>' if m_lims else "")
            + '</div>'
        )

    # key locations
    locs = [l for l in geo.get("key_locations",[]) if safe(l.get("name",""))]
    locs_html = ""
    if locs:
        locs_html = (
            '<div class="info-block">'
            '<div class="info-block-title">📍 핵심 장소</div>'
            + "".join(
                '<div class="loc-item"><div class="loc-name">' + l.get("name","") + '</div>'
                + '<div class="loc-desc">' + (l.get("description",""))[:80] + '</div></div>'
                for l in locs
            )
            + '</div>'
        )

    # factions
    fac_list = [f for f in factions if safe(f.get("name",""))]
    fac_html = ""
    if fac_list:
        fac_html = (
            '<div class="info-block">'
            '<div class="info-block-title">⚔️ 세력</div>'
            + "".join(
                '<div class="fac-item"><div class="fac-name">' + f.get("name","") + '</div>'
                + '<div class="fac-desc">' + (f.get("description",""))[:80] + '</div></div>'
                for f in fac_list
            )
            + '</div>'
        )

    left = (
        ('<h3 class="world-name">' + name + '</h3>' if safe(name) else "")
        + ('<p class="world-overview">' + overview + '</p>' if safe(overview) else '<p class="dim-p">세계관을 설정하세요</p>')
        + ('<div class="world-conflict"><strong>핵심 갈등:</strong> ' + conflict + '</div>' if safe(conflict) else "")
        + ('<div class="world-history"><strong>역사:</strong> ' + history + '</div>' if safe(history) else "")
        + ('<div class="world-culture"><strong>문화:</strong> ' + culture + '</div>' if safe(culture) else "")
    )

    # setting tags from cfg
    ws_items = ""
    for key, label in [("era","시대"),("magic_system","마법"),("geography","지리")]:
        v = ws.get(key,"")
        if v:
            ws_items += '<div class="si"><div class="si-k">' + label + '</div><div class="si-v">' + v + '</div></div>'
    for key, label in [("writing_style","문체"),("tone","분위기")]:
        v = (cfg.get(key) or "")[:40]
        if v:
            ws_items += '<div class="si"><div class="si-k">' + label + '</div><div class="si-v">' + v + '</div></div>'
    tags = "".join('<span class="tag">' + t + '</span>' for t in cfg.get("themes",[]))

    return left, ws_items, tags, magic_html, locs_html, fac_html


def plot_tab_html(plot):
    synopsis = (plot.get("synopsis") or plot.get("logline") or "")[:300]
    arcs     = plot.get("arcs", [])
    outlines = plot.get("chapter_outlines", [])
    colors   = ["#7c3aed","#be185d","#b45309","#0f766e","#1d4ed8"]

    synopsis_h = ""
    if synopsis and not _is_template(synopsis):
        synopsis_h = '<div class="card mb"><div class="ch"><span class="ct2">시놉시스</span></div><p class="synopsis-text">' + synopsis + '</p></div>'

    arcs_h = ""
    valid_arcs = [a for a in arcs if not _is_template(a.get("arc_name",""))]
    if valid_arcs:
        arc_cards = ""
        for i, arc in enumerate(valid_arcs):
            col   = colors[i % len(colors)]
            evs   = [e for e in arc.get("key_events",[]) if e and not _is_template(e)]
            dev   = arc.get("character_development","")
            desc  = arc.get("description","")
            arc_cards += (
                '<div class="arc-card" style="border-top:3px solid ' + col + '">'
                '<div class="arc-card-hd">'
                '<div class="arc-dot-lg" style="background:' + col + '"></div>'
                '<div><div class="arc-title">' + arc.get("arc_name","") + '</div>'
                '<div class="arc-range-lg">' + str(arc.get("chapters","")) + '화</div></div>'
                '</div>'
                + ('<p class="arc-desc">' + desc[:120] + '</p>' if desc and not _is_template(desc) else "")
                + ('<ul class="arc-events">' + "".join('<li>' + e + '</li>' for e in evs) + '</ul>' if evs else "")
                + ('<div class="arc-dev">성장: ' + dev[:80] + '</div>' if dev and not _is_template(dev) else "")
                + '</div>'
            )
        arcs_h = '<div class="card mb"><div class="ch"><span class="ct2">플롯 아크</span></div><div class="arc-grid">' + arc_cards + '</div></div>'

    outlines_h = ""
    valid_ols = [o for o in outlines if not _is_template(o.get("summary",""))]
    if valid_ols:
        ol_items = ""
        for ol in valid_ols[:10]:
            ch_num  = ol.get("chapter","")
            ch_t    = ol.get("title","")
            summary = (ol.get("summary") or "")[:200]
            tone    = ol.get("emotional_tone","")
            hook    = ol.get("ending_hook","")
            ol_items += (
                '<details class="ol-item">'
                '<summary class="ol-summary">'
                '<span class="ol-num">' + str(ch_num) + '화</span>'
                '<span class="ol-title">' + (ch_t if not _is_template(ch_t) else "(제목 미설정)") + '</span>'
                '<span class="ol-arrow">▶</span>'
                '</summary>'
                '<div class="ol-body">'
                + ('<p class="ol-text">' + summary + '</p>' if summary else "")
                + ('<div class="ol-meta">감정 톤: ' + tone + '</div>' if tone and not _is_template(tone) else "")
                + ('<div class="ol-meta">복선: ' + hook + '</div>' if hook and not _is_template(hook) else "")
                + '</div></details>'
            )
        outlines_h = '<div class="card"><div class="ch"><span class="ct2">챕터 아웃라인</span><span class="cs">' + str(len(valid_ols)) + '화 설정됨</span></div>' + ol_items + '</div>'

    if not synopsis_h and not arcs_h and not outlines_h:
        return '<div class="empty-state">플롯 정보가 없습니다<span>data/plot/plot_template.json 을 수정하세요</span></div>'
    return synopsis_h + arcs_h + outlines_h


def output_tab_html(outputs, s):
    icons = {"txt":"📄","epub":"📖","pdf":"🗒️"}
    all_f = [(icons.get(fmt,"📁"),fmt,name) for fmt,files in outputs.items() for name in files]
    file_html = ""
    if all_f:
        file_html = "".join(
            '<div class="file-row"><span class="fi">' + icon + '</span>'
            + '<span class="fn">' + name + '</span>'
            + '<span class="fb ' + fmt + '">' + fmt.upper() + '</span></div>'
            for icon,fmt,name in all_f
        )
    else:
        file_html = '<div class="empty-state">내보낸 파일이 없습니다<span>python main.py publish epub</span></div>'

    ppct  = f'{min(s["pct"],  100):.1f}%'
    pwpct = f'{min(s["wpct"], 100):.1f}%'

    return (
        '<div class="card mb"><div class="ch"><span class="ct2">내보낸 파일</span></div>'
        + '<div class="file-list">' + file_html + '</div></div>'
        + '<div class="card"><div class="ch"><span class="ct2">진행률</span></div>'
        + '<div class="prog"><div class="prog-lbl"><span class="pn">챕터</span>'
        + '<span class="pv">' + str(s["n"]) + '화 / ' + str(s["target"]) + '화 (' + str(s["pct"]) + '%)</span></div>'
        + '<div class="prog-bg"><div class="prog-fill" style="width:' + ppct + ';background:linear-gradient(90deg,#7c3aed,#a78bfa)"></div></div></div>'
        + '<div class="prog"><div class="prog-lbl"><span class="pn">글자 수</span>'
        + '<span class="pv">' + f'{s["tw"]:,}' + ' / ' + f'{s["wt"]:,}' + '자 (' + str(s["wpct"]) + '%)</span></div>'
        + '<div class="prog-bg"><div class="prog-fill" style="width:' + pwpct + ';background:linear-gradient(90deg,#be185d,#f472b6)"></div></div></div>'
        + '<div class="cmd-ref"><div class="cr-title">빠른 명령어</div>'
        + '<div class="cr-item"><code>python main.py chapter write</code><span>다음 화 작성</span></div>'
        + '<div class="cr-item"><code>python main.py chapter batch 1 10</code><span>연속 작성</span></div>'
        + '<div class="cr-item"><code>python main.py publish epub</code><span>epub 내보내기</span></div>'
        + '<div class="cr-item"><code>python dashboard.py</code><span>대시보드 갱신</span></div>'
        + '</div></div>'
    )


# ── 빌드 ──────────────────────────────────────────────────────────────────────

def build_html(data):
    s   = data["s"]
    cfg = data["cfg"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    title  = cfg.get("title","판타지 소설")
    genre  = cfg.get("genre","판타지")

    # genre badge style
    genre_lower = genre.lower()
    if "로맨스" in genre or "romance" in genre_lower:
        g_cls = "gb-rose"
    elif "역사" in genre or "historical" in genre_lower:
        g_cls = "gb-amber"
    else:
        g_cls = "gb-violet"

    world_left, ws_items, tags, magic_h, locs_h, fac_h = world_tab_html(data["world"], cfg)

    last_n   = str(s["last_n"]) + "화" if s["last_n"] else "—"
    pct_bar  = f'{min(s["pct"],100):.1f}%'

    subs = {
        "%%TITLE%%":      title,
        "%%GENRE%%":      genre,
        "%%G_CLS%%":      g_cls,
        "%%NOW%%":        now,
        "%%N%%":          str(s["n"]),
        "%%TARGET%%":     str(s["target"]),
        "%%PCT%%":        str(s["pct"]),
        "%%REMAIN%%":     str(s["remain"]),
        "%%TW%%":         f'{s["tw"]:,}',
        "%%WT%%":         f'{s["wt"]:,}',
        "%%AVG%%":        f'{s["avg"]:,}',
        "%%WPCH%%":       f'{s["wpch"]:,}',
        "%%LAST_N%%":     last_n,
        "%%LAST_D%%":     s["last_date"],
        "%%WPCT%%":       str(s["wpct"]),
        "%%PCT_BAR%%":    pct_bar,
        "%%NEXT_CH%%":    str(s["next_ch"]),
        "%%WRITING%%":    writing_card_html(data),
        "%%TOC_SIDEBAR%%": toc_sidebar_html(data),
        "%%CHROWS%%":     chapter_rows(data["chapters"]),
        "%%CHARS_GRID%%": chars_grid_html(data["chars"]),
        "%%WORLD_LEFT%%": world_left,
        "%%WS_ITEMS%%":   ws_items,
        "%%TAGS%%":       tags,
        "%%MAGIC%%":      magic_h,
        "%%LOCS%%":       locs_h,
        "%%FAC%%":        fac_h,
        "%%PLOT_TAB%%":   plot_tab_html(data["plot"]),
        "%%OUTPUT_TAB%%": output_tab_html(data["outputs"], s),
        "%%DATA%%":       json.dumps(data["chart_data"], ensure_ascii=False),
    }

    html = TEMPLATE
    for k, v in subs.items():
        html = html.replace(k, v)
    return html


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main():
    print("데이터 수집 중...")
    data = collect_data()
    print("HTML 생성 중...")
    html = build_html(data)
    out  = BASE_DIR / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    s = data["s"]
    print(f"\n✅ 대시보드 생성: {out}")
    print(f"   다음 화: {s['next_ch']}화  |  완성: {s['n']}/{s['target']}화 ({s['pct']}%)")
    print(f"   총 글자: {s['tw']:,}자")

# ── HTML 템플릿 ───────────────────────────────────────────────────────────────

TEMPLATE = ""
_T = []

_T.append("<!DOCTYPE html>")
_T.append('<html lang="ko"><head>')
_T.append('<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">')
_T.append("<title>%%TITLE%% — 집필 대시보드</title>")
_T.append('<link rel="preconnect" href="https://fonts.googleapis.com">')
_T.append('<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Noto+Serif+KR:wght@400;600;700&display=swap" rel="stylesheet">')
_T.append("<style>")
_T.append("""
:root{
  --bg:#f7f0e6;--sb:#2b1a0d;--sf:#ffffff;--sf2:#fdf5e8;
  --bd:#e4d0b8;--bd2:#cdb899;
  --acc:#bf4e1a;--acc-dim:rgba(191,78,26,.12);
  --rose:#7c3214;--rose-dim:rgba(124,50,20,.10);
  --amber:#c87a1a;--amber-dim:rgba(200,122,26,.10);
  --green:#4a7c59;--blue:#3a5fa0;
  --t:#2b1a0d;--td:#8a6a52;--tm:#b09a84;
  --r:10px;--rs:7px;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden;font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--t)}
a{color:inherit;text-decoration:none}
/* sidebar light-text overrides (dark brown bg) */
.sb{color:#f5e8d4}
.sb-title{color:#faf3ea !important}
.toc-group summary{color:#b09070 !important}
.toc-group summary:hover{color:#faf3ea !important}
.toc-arc-hd{color:#e07a3a !important}
.toc-arc-range{color:#7a5a3e !important}
.toc-ch{color:#b09070 !important}
.toc-ch:hover{color:#faf3ea !important;background:rgba(255,255,255,.07) !important}
.ch-done{color:#6b5040 !important}
.ch-done:hover{color:#b09070 !important}
.ch-next{color:#f5c89a !important;background:rgba(191,78,26,.2) !important;border-left-color:#bf4e1a !important}
.ch-next:hover{background:rgba(191,78,26,.32) !important}
.ch-next-badge{background:#bf4e1a !important}
.ch-todo{color:#5a3d2c !important}
.toc-more,.toc-empty{color:#5a3d2c !important}
.toc-char{color:#b09070 !important}
.toc-char:hover{color:#faf3ea !important;background:rgba(255,255,255,.07) !important}
.tc-role{color:#5a3d2c !important}
.sp-row{color:#b09070 !important}
.sp-val{color:#faf3ea !important}
.cta-sub{color:#7a5a44 !important}
.sb .gb-rose{background:rgba(191,78,26,.25) !important;color:#f5c89a !important;border-color:rgba(191,78,26,.4) !important}
.sb .gb-amber{background:rgba(200,122,26,.25) !important;color:#fcd87a !important;border-color:rgba(200,122,26,.4) !important}
.sb .gb-violet{background:rgba(191,78,26,.2) !important;color:#f5c89a !important;border-color:rgba(191,78,26,.35) !important}

/* ── LAYOUT ─────────────── */
.app{display:flex;height:100vh;overflow:hidden}

/* ── SIDEBAR ────────────── */
.sb{width:240px;min-width:240px;height:100vh;background:var(--sb);
  border-right:1px solid var(--bd);display:flex;flex-direction:column;overflow:hidden}
.sb-head{padding:20px 16px 14px;border-bottom:1px solid var(--bd);flex-shrink:0}
.sb-title{font-family:'Noto Serif KR',serif;font-size:.95rem;font-weight:700;
  color:var(--t);margin-bottom:6px;line-height:1.3}
.gb{display:inline-block;font-size:.65rem;font-weight:600;padding:2px 8px;
  border-radius:99px;margin-top:2px}
.gb-rose  {background:var(--rose-dim);color:#e8793a;border:1px solid rgba(124,50,20,.35)}
.gb-amber {background:var(--amber-dim);color:#c87a1a;border:1px solid rgba(200,122,26,.4)}
.gb-violet{background:var(--acc-dim);color:#bf4e1a;border:1px solid rgba(191,78,26,.35)}

/* mini progress in sidebar */
.sb-prog{padding:10px 16px;border-bottom:1px solid var(--bd);flex-shrink:0}
.sp-row{display:flex;justify-content:space-between;font-size:.72rem;color:var(--td);margin-bottom:5px}
.sp-val{color:var(--t);font-weight:600}
.sp-bg{background:var(--bd2);border-radius:99px;height:4px}
.sp-fill{height:100%;border-radius:99px;background:linear-gradient(90deg,#bf4e1a,#c87a1a)}

/* TOC scroll area */
.toc-scroll{flex:1;overflow-y:auto;padding:8px 0}
.toc-scroll::-webkit-scrollbar{width:3px}
.toc-scroll::-webkit-scrollbar-thumb{background:var(--bd2);border-radius:2px}

/* details/summary toggle */
details.toc-group{border-bottom:1px solid var(--bd)}
details.toc-group summary{
  list-style:none;cursor:pointer;
  display:flex;align-items:center;gap:6px;
  padding:10px 16px;font-size:.73rem;font-weight:600;
  text-transform:uppercase;letter-spacing:.05em;color:var(--td);
  user-select:none;transition:color .15s}
details.toc-group summary::-webkit-details-marker{display:none}
details.toc-group summary:hover{color:var(--t)}
.toc-arr{font-size:.6rem;transition:transform .2s;flex-shrink:0}
details[open] .toc-arr{transform:rotate(90deg)}
.toc-body{padding:4px 0 8px}

.toc-arc-hd{padding:4px 16px 2px;font-size:.68rem;font-weight:600;
  text-transform:uppercase;letter-spacing:.05em;color:var(--acc);opacity:.7}
.toc-arc-range{color:var(--td);font-weight:400}
.toc-ch{display:block;padding:5px 16px 5px 24px;font-size:.78rem;color:var(--td);
  cursor:pointer;transition:all .12s;border-left:2px solid transparent;margin-left:0}
.toc-ch:hover{color:var(--t);background:var(--sf)}
.ch-done{color:#6b6880;font-size:.75rem}
.ch-done:hover{color:var(--td)}
.ch-next{color:#f5c89a;font-weight:600;border-left-color:var(--acc);
  background:rgba(191,78,26,.15);padding-left:12px}
.ch-next:hover{background:rgba(191,78,26,.28)}
.ch-next-badge{font-size:.6rem;background:var(--acc);color:#fff;
  padding:1px 5px;border-radius:99px;margin-left:4px;font-weight:500}
.ch-todo{color:var(--tm)}
.toc-more{padding:3px 16px 3px 24px;font-size:.72rem;color:var(--tm)}
.toc-empty{padding:8px 16px;font-size:.75rem;color:var(--tm)}
.toc-char{display:flex;align-items:center;gap:8px;padding:5px 16px;
  font-size:.78rem;color:var(--td);cursor:pointer;transition:all .12s}
.toc-char:hover{color:var(--t);background:var(--sf)}
.tc-av{width:22px;height:22px;border-radius:50%;display:flex;align-items:center;
  justify-content:center;font-size:.65rem;font-weight:700;flex-shrink:0}
.main-av{background:linear-gradient(135deg,#bf4e1a,#e8793a)}
.sub-av{background:linear-gradient(135deg,#7c3214,#c87a1a)}
.tc-role{font-size:.65rem;color:var(--tm)}

/* 단계 배지 & 정보 행 */
.toc-step-label{flex:1;font-size:.73rem}
.step-done{font-size:.58rem;font-weight:700;padding:1px 5px;border-radius:3px;
  background:rgba(74,124,89,.25);color:#4a7c59;flex-shrink:0}
.step-todo{font-size:.58rem;font-weight:700;padding:1px 5px;border-radius:3px;
  background:rgba(90,61,44,.25);color:#9b7a5e;flex-shrink:0}
.toc-info-row{display:flex;align-items:baseline;gap:5px;
  padding:3px 16px 3px 24px;font-size:.74rem}
.ti-k{color:#5a3d2c;flex-shrink:0;width:28px;font-size:.68rem}
.ti-v{color:#b09070}
.ti-v.dim{color:#5a3d2c}

/* sidebar bottom CTA */
.sb-cta{padding:12px 14px;border-top:1px solid var(--bd);flex-shrink:0}
.cta-btn{display:block;width:100%;padding:10px;border-radius:var(--rs);
  background:linear-gradient(135deg,#bf4e1a,#c87a1a);border:none;
  color:#fff;font-size:.8rem;font-weight:600;cursor:pointer;text-align:center;
  font-family:inherit;transition:opacity .15s}
.cta-btn:hover{opacity:.85}
.cta-sub{font-size:.68rem;color:var(--tm);text-align:center;margin-top:6px}

/* ── MAIN ───────────────── */
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}

/* topbar */
.topbar{height:52px;border-bottom:1px solid var(--bd);display:flex;
  align-items:center;justify-content:space-between;padding:0 24px;flex-shrink:0}
.topbar-title{font-family:'Noto Serif KR',serif;font-size:.9rem;font-weight:600;
  display:flex;align-items:center;gap:8px}
.topbar-r{font-size:.73rem;color:var(--td);display:flex;align-items:center;gap:12px}
.updated-dot{width:6px;height:6px;border-radius:50%;background:#059669;flex-shrink:0}

/* tabs */
.tab-nav{display:flex;align-items:center;gap:2px;padding:10px 24px 0;
  border-bottom:1px solid var(--bd);flex-shrink:0}
.tab-btn{padding:7px 16px;border:none;background:transparent;color:var(--td);
  font-size:.82rem;font-weight:500;cursor:pointer;border-radius:var(--rs) var(--rs) 0 0;
  font-family:inherit;transition:all .15s;position:relative;bottom:-1px}
.tab-btn:hover{color:var(--t);background:var(--sf)}
.tab-btn.on{color:#2b1a0d;background:#fff;border:1px solid var(--bd);
  border-bottom:1px solid #fff;font-weight:600}

/* content area */
.content{flex:1;overflow-y:auto;padding:20px 24px}
.content::-webkit-scrollbar{width:4px}
.content::-webkit-scrollbar-thumb{background:var(--bd2);border-radius:2px}
.tab-pane{display:none;flex-direction:column;gap:16px}
.tab-pane.on{display:flex}

/* ── WRITING CARD ──────── */
.wc{background:var(--sf);border:1px solid var(--bd);border-radius:var(--r);
  padding:20px 24px;display:flex;gap:28px;align-items:flex-start;
  border-top:3px solid var(--acc);position:relative;overflow:hidden}
.wc::before{content:'';position:absolute;top:0;left:0;right:0;bottom:0;
  background:radial-gradient(ellipse at 0% 0%,rgba(191,78,26,.07),transparent 60%);
  pointer-events:none}
.wc-left{flex-shrink:0;min-width:120px}
.wc-label{font-size:.7rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;
  color:var(--acc);margin-bottom:6px}
.wc-big{font-family:'Noto Serif KR',serif;font-size:2.8rem;font-weight:700;
  line-height:1;color:var(--t);margin-bottom:4px}
.wc-ch-title{font-size:.9rem;color:#bf4e1a;font-weight:500}
.wc-right{flex:1}
.wc-summary{font-size:.84rem;color:var(--td);line-height:1.7;margin-bottom:10px}
.wc-tone{font-size:.78rem;color:var(--td);margin-bottom:6px;line-height:1.5}
.wc-tone-lb{display:inline-block;font-size:.65rem;font-weight:600;
  background:var(--acc-dim);color:#bf4e1a;padding:1px 6px;border-radius:4px;
  margin-right:6px}
.wc-footer{display:flex;align-items:center;gap:12px;margin-top:10px;flex-wrap:wrap}
.wc-goal{font-size:.75rem;color:var(--td);background:var(--sf2);
  padding:4px 10px;border-radius:99px;border:1px solid var(--bd)}
.wc-cmd{font-size:.75rem;background:#fdf5e8;color:#bf4e1a;padding:5px 12px;
  border-radius:6px;border:1px solid var(--bd);cursor:pointer;
  user-select:all;transition:background .15s;font-weight:500}
.wc-cmd:hover{background:#f5e8d4}
.done-wc{border-top-color:var(--green);flex-direction:column;align-items:center;
  text-align:center;padding:32px}
.done-wc .wc-icon{font-size:2rem;margin-bottom:8px}
.done-wc .wc-big{font-size:1.8rem}
.done-wc .wc-sub{color:var(--td);font-size:.85rem;margin-top:6px}

/* ── KPI CARDS ─────────── */
.kpi-row{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
.kpi{background:var(--sf);border:1px solid var(--bd);border-radius:var(--r);
  padding:18px 18px 14px;position:relative;overflow:hidden}
.kpi::after{content:'';position:absolute;top:0;left:0;right:0;height:2px}
.ki::after{background:linear-gradient(90deg,#bf4e1a,#e8793a)}
.kb::after{background:linear-gradient(90deg,#c87a1a,#f0aa4a)}
.kg::after{background:linear-gradient(90deg,#5a8c4a,#8ab87a)}
.ka::after{background:linear-gradient(90deg,#6b3a1e,#9b6a3a)}
.kp::after{background:linear-gradient(90deg,#c44a38,#e87a6a)}
.kpi-lb{font-size:.68rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;
  color:var(--td);margin-bottom:8px}
.kpi-v{font-size:1.8rem;font-weight:800;line-height:1;margin-bottom:5px;letter-spacing:-.02em}
.kpi-s{font-size:.7rem;color:var(--td)}

/* ── CARDS ──────────────── */
.card{background:var(--sf);border:1px solid var(--bd);border-radius:var(--r);padding:18px 20px}
.mb{margin-bottom:0}
.ch{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
.ct2{font-size:.7rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--td)}
.cs{font-size:.68rem;color:var(--tm)}
.chart-box{min-height:200px}
.g2{display:grid;grid-template-columns:240px 1fr;gap:14px}
.g2w{display:grid;grid-template-columns:1fr 1fr;gap:14px}

/* ── TABLE ──────────────── */
table{width:100%;border-collapse:collapse}
thead th{text-align:left;padding:0 10px 8px;font-size:.68rem;font-weight:600;
  text-transform:uppercase;letter-spacing:.06em;color:var(--td);border-bottom:1px solid var(--bd)}
tbody td{padding:9px 10px;font-size:.85rem;border-bottom:1px solid var(--bd)}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover td{background:var(--sf2)}
.td-acc{color:var(--acc);font-weight:700;width:52px}
.td-r{text-align:right;color:var(--td);width:68px}
.td-d{color:var(--td);font-size:.76rem;width:90px}
.empty-cell{text-align:center;color:var(--td);padding:28px}

/* ── CHARACTER CARDS ─────── */
.chars-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:12px}
.char-card{background:var(--sf2);border:1px solid var(--bd);border-radius:var(--rs);
  padding:14px 16px}
.sub-card{border-left:2px solid var(--rose)}
.char-card:not(.sub-card){border-left:2px solid var(--acc)}
.char-tpl{opacity:.35}
.char-top{display:flex;align-items:center;gap:10px;margin-bottom:8px}
.char-av{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;
  justify-content:center;font-weight:700;font-size:.9rem;flex-shrink:0}
.av-main{background:linear-gradient(135deg,#bf4e1a,#e8793a)}
.av-sub{background:linear-gradient(135deg,#7c3214,#c87a1a)}
.char-name{font-weight:600;font-size:.87rem}
.char-role{font-size:.63rem;font-weight:600;padding:2px 7px;border-radius:99px;
  display:inline-block;margin-top:2px}
.role-main{background:var(--acc-dim);color:#bf4e1a}
.role-sub{background:var(--rose-dim);color:#7c3214}
.char-age{font-size:.68rem;color:var(--td)}
.char-desc{font-size:.76rem;color:var(--td);line-height:1.5;margin-top:4px}
.char-motiv{font-size:.72rem;color:var(--tm);line-height:1.4;margin-top:3px}
.char-abs{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px}
.ab{font-size:.65rem;padding:2px 7px;border-radius:99px;
  background:var(--acc-dim);color:#bf4e1a;border:1px solid rgba(191,78,26,.25)}

/* ── WORLD TAB ───────────── */
.world-name{font-family:'Noto Serif KR',serif;font-size:1.1rem;font-weight:700;
  margin-bottom:8px;color:#7c3214}
.world-overview{font-size:.85rem;color:var(--td);line-height:1.7;margin-bottom:8px}
.world-conflict{font-size:.8rem;color:var(--td);padding:9px 12px;background:var(--sf2);
  border-radius:6px;border-left:2px solid var(--acc);line-height:1.5;margin-bottom:6px}
.world-history,.world-culture{font-size:.78rem;color:var(--td);
  padding:7px 10px;border-radius:6px;background:var(--sf2);margin-bottom:6px;line-height:1.5}
.dim-p{color:var(--tm);font-size:.85rem}
.si-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}
.si{background:var(--sf2);border-radius:6px;padding:9px 12px}
.si-k{font-size:.65rem;text-transform:uppercase;letter-spacing:.05em;color:var(--td);margin-bottom:2px}
.si-v{font-size:.82rem;font-weight:500}
.tags{display:flex;flex-wrap:wrap;gap:5px;margin-top:10px}
.tag{font-size:.68rem;font-weight:500;padding:3px 9px;border-radius:99px;
  background:var(--acc-dim);color:#bf4e1a;border:1px solid rgba(191,78,26,.3)}
.info-block{background:var(--sf2);border-radius:var(--rs);padding:12px 14px;margin-top:12px}
.info-block-title{font-size:.78rem;font-weight:600;margin-bottom:8px;color:var(--t)}
.info-sub{font-size:.75rem;color:var(--td);margin-bottom:4px}
.info-sub.lim{color:#c87a1a}
.info-list{padding-left:14px;font-size:.78rem;color:var(--td);line-height:1.8}
.loc-item,.fac-item{padding:6px 0;border-bottom:1px solid var(--bd)}
.loc-item:last-child,.fac-item:last-child{border-bottom:none}
.loc-name,.fac-name{font-size:.82rem;font-weight:600;margin-bottom:2px}
.loc-desc,.fac-desc{font-size:.75rem;color:var(--td)}

/* ── PLOT TAB ────────────── */
.synopsis-text{font-size:.875rem;color:var(--td);line-height:1.8}
.arc-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.arc-card{background:var(--sf2);border-radius:var(--rs);padding:14px 16px}
.arc-card-hd{display:flex;align-items:center;gap:10px;margin-bottom:8px}
.arc-dot-lg{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.arc-title{font-weight:600;font-size:.88rem}
.arc-range-lg{font-size:.72rem;color:var(--td)}
.arc-desc{font-size:.78rem;color:var(--td);line-height:1.5;margin-bottom:6px}
.arc-events{padding-left:14px;font-size:.76rem;color:var(--td);line-height:1.7}
.arc-dev{font-size:.74rem;color:#c87a1a;margin-top:6px;font-style:italic}
/* chapter outline accordion */
details.ol-item{border-bottom:1px solid var(--bd)}
details.ol-item:last-child{border-bottom:none}
details.ol-item summary.ol-summary{
  list-style:none;cursor:pointer;display:flex;align-items:center;gap:10px;
  padding:10px 0;font-size:.85rem;user-select:none}
details.ol-item summary::-webkit-details-marker{display:none}
.ol-num{color:var(--acc);font-weight:700;width:36px;flex-shrink:0}
.ol-title{flex:1}
.ol-arrow{font-size:.6rem;color:var(--td);transition:transform .2s}
details.ol-item[open] .ol-arrow{transform:rotate(90deg)}
.ol-body{padding:0 0 12px 46px}
.ol-text{font-size:.82rem;color:var(--td);line-height:1.6;margin-bottom:6px}
.ol-meta{font-size:.76rem;color:var(--tm);margin-top:4px}

/* ── OUTPUT TAB ──────────── */
.file-list{display:flex;flex-direction:column;gap:7px}
.file-row{display:flex;align-items:center;gap:10px;padding:10px 12px;
  background:var(--sf2);border-radius:var(--rs);border:1px solid var(--bd)}
.fi{font-size:1rem}.fn{flex:1;font-size:.82rem;color:var(--td)}
.fb{font-size:.64rem;font-weight:700;padding:2px 7px;border-radius:4px;text-transform:uppercase}
.fb.txt{background:var(--acc-dim);color:#bf4e1a}
.fb.epub{background:var(--amber-dim);color:#c87a1a}
.fb.pdf{background:rgba(74,124,89,.15);color:#4a7c59}
.prog{margin-bottom:12px}
.prog-lbl{display:flex;justify-content:space-between;font-size:.74rem;margin-bottom:5px}
.pn{color:var(--td)}.pv{color:var(--t);font-weight:600}
.prog-bg{background:var(--bd2);border-radius:99px;height:5px}
.prog-fill{height:100%;border-radius:99px}
.cmd-ref{margin-top:14px;border-top:1px solid var(--bd);padding-top:12px}
.cr-title{font-size:.7rem;font-weight:600;text-transform:uppercase;
  letter-spacing:.05em;color:var(--td);margin-bottom:8px}
.cr-item{display:flex;align-items:center;gap:10px;padding:5px 0;font-size:.78rem;color:var(--td)}
.cr-item code{background:#fdf5e8;color:#bf4e1a;padding:3px 9px;border-radius:5px;
  font-size:.73rem;border:1px solid var(--bd)}

/* ── EMPTY STATE ─────────── */
.empty-state{text-align:center;padding:32px;color:var(--td);font-size:.84rem;line-height:1.7}
.empty-state span{display:block;color:var(--tm);font-family:monospace;
  font-size:.76rem;margin-top:6px}
""")
_T.append("</style></head><body>")
_T.append('<div class="app">')

# SIDEBAR
_T.append('<aside class="sb">')
_T.append('<div class="sb-head">')
_T.append('<div class="sb-title">%%TITLE%%</div>')
_T.append('<span class="gb %%G_CLS%%">%%GENRE%%</span>')
_T.append('</div>')

_T.append('<div class="sb-prog">')
_T.append('<div class="sp-row"><span>집필 진행</span><span class="sp-val">%%N%%화 / %%TARGET%%화</span></div>')
_T.append('<div class="sp-bg"><div class="sp-fill" style="width:%%PCT_BAR%%"></div></div>')
_T.append('</div>')

_T.append('<div class="toc-scroll">%%TOC_SIDEBAR%%</div>')

_T.append('<div class="sb-cta">')
_T.append('<button class="cta-btn" onclick="gotoTab(\'overview\')">✏️ %%NEXT_CH%%화 집필하기</button>')
_T.append('<div class="cta-sub">다음에 쓸 화: %%NEXT_CH%%화</div>')
_T.append('</div>')
_T.append('</aside>') # /sidebar

# MAIN
_T.append('<div class="main">')
_T.append('<header class="topbar">')
_T.append('<div class="topbar-title"><div class="updated-dot"></div>%%TITLE%% 집필 대시보드</div>')
_T.append('<div class="topbar-r"><span>%%NOW%%</span></div>')
_T.append('</header>')

_T.append('<nav class="tab-nav">')
for tab, label in [("overview","전반"),("chapters","챕터"),("chars","캐릭터"),("world","세계관"),("plot","줄거리"),("output","출력")]:
    on = ' on' if tab == 'overview' else ''
    _T.append(f'<button class="tab-btn{on}" data-tab="{tab}">{label}</button>')
_T.append('</nav>')

_T.append('<div class="content">')

# ── 전반 tab
_T.append('<div id="pane-overview" class="tab-pane on">')
_T.append('%%WRITING%%')
_T.append('<div class="kpi-row">')
_T.append('<div class="kpi ki"><div class="kpi-lb">완성 화수</div><div class="kpi-v" style="color:#bf4e1a">%%N%%<span style="font-size:1rem;font-weight:500">화</span></div><div class="kpi-s">목표 %%TARGET%%화</div></div>')
_T.append('<div class="kpi kb"><div class="kpi-lb">완성률</div><div class="kpi-v" style="color:#c87a1a">%%PCT%%<span style="font-size:.9rem">%</span></div><div class="kpi-s">%%REMAIN%%화 남음</div></div>')
_T.append('<div class="kpi kg"><div class="kpi-lb">총 글자 수</div><div class="kpi-v" style="color:#4a7c59;font-size:1.45rem">%%TW%%</div><div class="kpi-s">목표 %%WT%%자</div></div>')
_T.append('<div class="kpi ka"><div class="kpi-lb">평균 글자/화</div><div class="kpi-v" style="color:#6b3a1e;font-size:1.45rem">%%AVG%%</div><div class="kpi-s">목표 %%WPCH%%자</div></div>')
_T.append('<div class="kpi kp"><div class="kpi-lb">마지막 작성</div><div class="kpi-v" style="color:#c44a38;font-size:1.15rem;padding-top:5px">%%LAST_N%%</div><div class="kpi-s">%%LAST_D%%</div></div>')
_T.append('</div>') # /kpi-row

_T.append('<div class="g2">')
_T.append('<div class="card"><div class="ch"><span class="ct2">완성률</span></div><div id="c-radial" class="chart-box"></div></div>')
_T.append('<div class="card"><div class="ch"><span class="ct2">화수별 글자 수</span><span class="cs">단위: 자</span></div><div id="c-bar" class="chart-box"></div></div>')
_T.append('</div>')
_T.append('<div class="card"><div class="ch"><span class="ct2">누적 글자 수 추이</span><span class="cs">합계 %%TW%%자</span></div><div id="c-area" class="chart-box"></div></div>')
_T.append('</div>') # /pane-overview

# ── 챕터 tab
_T.append('<div id="pane-chapters" class="tab-pane">')
_T.append('<div class="card"><div class="ch"><span class="ct2">챕터 목록</span><span class="cs">%%N%%화 완성</span></div>')
_T.append('<table><thead><tr><th>화수</th><th>제목</th><th style="text-align:right">글자 수</th><th>작성일</th></tr></thead>')
_T.append('<tbody>%%CHROWS%%</tbody></table></div>')
_T.append('<div class="card"><div class="ch"><span class="ct2">화수별 글자 수</span></div><div id="c-bar2" class="chart-box"></div></div>')
_T.append('</div>') # /pane-chapters

# ── 캐릭터 tab
_T.append('<div id="pane-chars" class="tab-pane">')
_T.append('<div class="card"><div class="ch"><span class="ct2">캐릭터</span></div>')
_T.append('<div class="chars-grid">%%CHARS_GRID%%</div></div>')
_T.append('</div>')

# ── 세계관 tab
_T.append('<div id="pane-world" class="tab-pane">')
_T.append('<div class="g2w">')
_T.append('<div class="card"><div class="ch"><span class="ct2">세계관</span></div>')
_T.append('%%WORLD_LEFT%%')
_T.append('<div class="si-grid">%%WS_ITEMS%%</div>')
_T.append('<div class="tags">%%TAGS%%</div>')
_T.append('%%MAGIC%%%%LOCS%%</div>')
_T.append('<div class="card"><div class="ch"><span class="ct2">세력 & 지리</span></div>')
_T.append('%%FAC%%</div>')
_T.append('</div>')
_T.append('</div>')

# ── 줄거리 tab
_T.append('<div id="pane-plot" class="tab-pane">%%PLOT_TAB%%</div>')

# ── 출력 tab
_T.append('<div id="pane-output" class="tab-pane">%%OUTPUT_TAB%%</div>')

_T.append('</div>') # /content
_T.append('</div>') # /main
_T.append('</div>') # /app

# SCRIPTS
_T.append('<script src="https://cdn.jsdelivr.net/npm/apexcharts@3.48.0/dist/apexcharts.min.js"></script>')
_T.append('<script>')
_T.append("""
// ── Tab switching
function gotoTab(name){
  document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('on'));
  document.querySelectorAll('.tab-pane').forEach(p=>p.classList.remove('on'));
  const btn=document.querySelector('.tab-btn[data-tab="'+name+'"]');
  const pane=document.getElementById('pane-'+name);
  if(btn)btn.classList.add('on');
  if(pane)pane.classList.add('on');
}
document.querySelectorAll('.tab-btn').forEach(btn=>{
  btn.addEventListener('click',()=>gotoTab(btn.dataset.tab));
});
// TOC links
document.querySelectorAll('[data-goto]').forEach(el=>{
  el.addEventListener('click',e=>{e.preventDefault();gotoTab(el.dataset.goto);});
});

// ── Charts
const D=%%DATA%%;
const DK={
  chart:{background:'transparent',foreColor:'#8a6a52',
    fontFamily:"'Inter',sans-serif",toolbar:{show:false},
    animations:{enabled:true,easing:'easeinout',speed:700}},
  theme:{mode:'light'},
  grid:{borderColor:'#e4d0b8',strokeDashArray:3,padding:{left:2,right:2}},
  tooltip:{theme:'light',style:{fontFamily:"'Inter',sans-serif"}}
};

// Radial
new ApexCharts(document.getElementById('c-radial'),{
  ...DK,chart:{...DK.chart,type:'radialBar',height:230},
  series:[D.pct],
  plotOptions:{radialBar:{hollow:{size:'60%'},
    dataLabels:{name:{show:true,color:'#8a6a52',fontSize:'11px',offsetY:-8},
      value:{show:true,color:'#2b1a0d',fontSize:'1.9rem',fontWeight:'800',
        formatter:v=>v+'%',offsetY:5}},
    track:{background:'#e4d0b8',strokeWidth:'97%'}}},
  fill:{type:'gradient',gradient:{shade:'light',type:'horizontal',
    gradientToColors:['#c87a1a'],stops:[0,100]}},
  colors:['#bf4e1a'],labels:['완성률'],
}).render();

// Bar (reusable)
function mkBar(id){
  const el=document.getElementById(id); if(!el)return;
  if(!D.chNums.length){
    el.innerHTML='<div style="display:flex;align-items:center;justify-content:center;height:200px;color:#8a6a52;font-size:.82rem">챕터 데이터가 없습니다</div>';
    return;
  }
  new ApexCharts(el,{...DK,
    chart:{...DK.chart,type:'bar',height:230},
    series:[{name:'글자 수',data:D.chWords}],
    xaxis:{categories:D.chNums.map(n=>n+'화'),
      labels:{style:{colors:'#b09a84',fontSize:'10px'}},
      axisBorder:{show:false},axisTicks:{show:false}},
    yaxis:{labels:{style:{colors:'#6b6880',fontSize:'10px'},
      formatter:v=>v>=1000?(v/1000).toFixed(1)+'k':v}},
    plotOptions:{bar:{borderRadius:4,columnWidth:'55%'}},
    colors:['#bf4e1a'],
    fill:{type:'gradient',gradient:{shade:'light',type:'vertical',
      gradientToColors:['#c87a1a'],stops:[0,100]}},
    dataLabels:{enabled:false},
  }).render();
}
mkBar('c-bar'); mkBar('c-bar2');

// Area
(()=>{
  const el=document.getElementById('c-area');
  if(!D.cumulative.length){
    el.innerHTML='<div style="display:flex;align-items:center;justify-content:center;height:200px;color:#8a6a52;font-size:.82rem">챕터 데이터가 없습니다</div>';
    return;
  }
  new ApexCharts(el,{...DK,
    chart:{...DK.chart,type:'area',height:200},
    series:[{name:'누적 글자 수',data:D.cumulative}],
    xaxis:{categories:D.chNums.map(n=>n+'화'),
      labels:{style:{colors:'#b09a84',fontSize:'10px'}},
      axisBorder:{show:false},axisTicks:{show:false}},
    yaxis:{labels:{style:{colors:'#6b6880',fontSize:'10px'},
      formatter:v=>v>=1000?Math.round(v/1000)+'k':v}},
    stroke:{curve:'smooth',width:2},
    fill:{type:'gradient',gradient:{shadeIntensity:1,opacityFrom:.2,opacityTo:0,stops:[0,90]}},
    colors:['#c87a1a'],dataLabels:{enabled:false},
    markers:{size:D.chNums.length<=12?4:0,colors:['#c87a1a'],
      strokeColors:'#fff',strokeWidth:2},
  }).render();
})();
""")
_T.append('</script></body></html>')

TEMPLATE = "\n".join(_T)

if __name__ == '__main__':
    main()
