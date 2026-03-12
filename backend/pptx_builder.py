"""
Module de conversion du cours Markdown en présentation PowerPoint (.pptx).
Thème académique sombre – design splitté et soigné.
"""

import re
from io import BytesIO

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from lxml import etree

# ═══════════════════════════════════════════════════════
#  PALETTE
# ═══════════════════════════════════════════════════════
C_BG           = RGBColor(0x08, 0x08, 0x18)   # Fond principal – très sombre
C_BG_CARD      = RGBColor(0x0F, 0x0F, 0x24)   # Fond slides contenu
C_PANEL        = RGBColor(0x5B, 0x5E, 0xE8)   # Panneau gauche titre (violet vif)
C_ACCENT       = RGBColor(0x63, 0x66, 0xF1)   # Accent principal
C_ACCENT2      = RGBColor(0x81, 0x8C, 0xF8)   # Accent clair
C_ACCENT_DARK  = RGBColor(0x1E, 0x20, 0x5C)   # Violet très sombre
C_ACCENT_MID   = RGBColor(0x2D, 0x30, 0x7A)   # Violet intermédiaire
C_WHITE        = RGBColor(0xFF, 0xFF, 0xFF)
C_TEXT_LIGHT   = RGBColor(0xE2, 0xE8, 0xF0)
C_TEXT_MUTED   = RGBColor(0x94, 0xA3, 0xB8)
C_TABLE_HDR    = RGBColor(0x3B, 0x3E, 0xB8)
C_TABLE_ROW1   = RGBColor(0x12, 0x12, 0x28)
C_TABLE_ROW2   = RGBColor(0x18, 0x18, 0x34)
C_SUCCESS      = RGBColor(0x34, 0xD3, 0x99)
C_BULLET       = RGBColor(0x6E, 0x75, 0xF9)   # Couleur des marqueurs bullets

SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)

TITLE_PANEL_W  = Inches(4.4)    # Largeur du panneau gauche (slide titre)
LEFT_BAR_W     = Inches(0.09)   # Barre gauche accent sur slides contenu

MAX_BULLETS_SINGLE = 5
MAX_BULLETS_COL    = 7
MAX_CHARS          = 400

CHIFFRES_ROMAINS = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']
CIRCLED_NUMS     = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩',
                    '⑪', '⑫']


# ═══════════════════════════════════════════════════════
#  UTILITAIRES MARKDOWN
# ═══════════════════════════════════════════════════════

def _clean(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*',     r'\1', text)
    text = re.sub(r'`(.+?)`',       r'\1', text)
    text = re.sub(r'__(.+?)__',     r'\1', text)
    return text.strip()


def _truncate(text: str, max_chars: int = MAX_CHARS) -> str:
    text = _clean(text)
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(' ', 1)[0] + '…'


def _parse_inline(text: str) -> list[tuple[str, bool]]:
    """Retourne (texte, est_gras) pour préserver le gras Markdown."""
    segments, last = [], 0
    for m in re.finditer(r'\*\*(.+?)\*\*|__(.+?)__', text):
        if m.start() > last:
            plain = re.sub(r'\*(.+?)\*', r'\1', text[last:m.start()])
            plain = re.sub(r'`(.+?)`',   r'\1', plain)
            if plain:
                segments.append((plain, False))
        segments.append((_clean(m.group(1) or m.group(2)), True))
        last = m.end()
    if last < len(text):
        tail = re.sub(r'\*(.+?)\*', r'\1', text[last:])
        tail = re.sub(r'`(.+?)`',   r'\1', tail)
        if tail.strip():
            segments.append((tail, False))
    return segments or [(_clean(text), False)]


def _extract_bullets(text: str, max_b: int = MAX_BULLETS_COL * 2) -> list[str]:
    bullets = []
    for line in text.split('\n'):
        line = line.strip()
        if re.match(r'^[-*•]\s', line):
            b = line[2:].strip()
            if b:
                bullets.append(b)
        elif re.match(r'^\d+\.\s', line):
            b = re.sub(r'^\d+\.\s', '', line).strip()
            if b:
                bullets.append(b)
        if len(bullets) >= max_b:
            break
    return bullets


def _first_paragraph(text: str) -> str:
    for block in text.split('\n\n'):
        block = block.strip()
        if block and not block.startswith('|') and not block.startswith('#'):
            return _truncate(block)
    return ''


def _wrap_text(text: str, width: int = 90) -> list[str]:
    words = text.split()
    lines, current = [], ''
    for word in words:
        if len(current) + len(word) + 1 <= width:
            current = (current + ' ' + word).strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


def _parse_md_table(text: str) -> tuple[list[str], list[list[str]]]:
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    tbl = [l for l in lines if l.startswith('|')]
    if len(tbl) < 2:
        return [], []
    def parse_row(line):
        return [_clean(c.strip()) for c in line.strip('|').split('|')]
    headers = parse_row(tbl[0])
    rows = [parse_row(l) for l in tbl[2:] if not re.match(r'^\|[-:| ]+\|$', l)]
    return headers, rows


def _parse_definitions(text: str) -> list[tuple[str, str]]:
    items = []
    for line in text.split('\n'):
        line = line.strip().lstrip('-').lstrip('*').strip()
        m = re.match(r'\*\*(.+?)\*\*\s*[:\-–]\s*(.+)', line)
        if m:
            items.append((_clean(m.group(1)), m.group(2).strip()))
            continue
        m2 = re.match(r'^([^:\-]{3,40})\s*[:\-–]\s*(.{10,})', line)
        if m2:
            items.append((_clean(m2.group(1)), m2.group(2).strip()))
    return items[:12]


# ═══════════════════════════════════════════════════════
#  HELPERS PPTX
# ═══════════════════════════════════════════════════════

def _fill_solid(shape, color: RGBColor):
    shape.fill.solid()
    shape.fill.fore_color.rgb = color


def _no_line(shape):
    shape.line.fill.background()


def _rect(slide, left, top, width, height, color: RGBColor):
    """Ajoute un rectangle plein sans bord."""
    s = slide.shapes.add_shape(1, Inches(left), Inches(top), Inches(width), Inches(height))
    _fill_solid(s, color)
    _no_line(s)
    return s


def _rounded_rect(slide, left, top, width, height, color: RGBColor):
    """Rectangle arrondi plein sans bord (type 5)."""
    s = slide.shapes.add_shape(5, Inches(left), Inches(top), Inches(width), Inches(height))
    _fill_solid(s, color)
    _no_line(s)
    return s


def _tb(slide, left, top, width, height):
    return slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )


def _set_bg(slide, color: RGBColor):
    bg = slide.background
    bg.fill.solid()
    bg.fill.fore_color.rgb = color


def _run_fmt(run, size_pt: int, color: RGBColor, bold=False, italic=False):
    run.font.size    = Pt(size_pt)
    run.font.color.rgb = color
    run.font.bold    = bold
    run.font.italic  = italic
    run.font.name    = 'Calibri'


def _add_runs(para, raw_text: str, size_pt: int, color: RGBColor, base_bold=False):
    for seg_text, is_bold in _parse_inline(raw_text):
        run = para.add_run()
        run.text = seg_text
        _run_fmt(run, size_pt, color, bold=(base_bold or is_bold))


def _add_transparent_rect(slide, left, top, width, height, color: RGBColor, opacity: int):
    """Rectangle avec transparence. opacity: 0=invisible, 100=opaque (%)."""
    s = slide.shapes.add_shape(1, Inches(left), Inches(top), Inches(width), Inches(height))
    s.line.fill.background()
    sp = s._element
    spPr = sp.find(qn('p:spPr'))
    # Remplace le fill existant par un solidFill avec alpha
    for child in list(spPr):
        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        if tag in ('solidFill', 'gradFill', 'pattFill', 'noFill', 'blipFill'):
            spPr.remove(child)
    ns = 'http://schemas.openxmlformats.org/drawingml/2006/main'
    solid = etree.SubElement(spPr, f'{{{ns}}}solidFill')
    clr   = etree.SubElement(solid, f'{{{ns}}}srgbClr')
    clr.set('val', f'{color[0]:02X}{color[1]:02X}{color[2]:02X}')
    alpha = etree.SubElement(clr, f'{{{ns}}}alpha')
    alpha.set('val', str(opacity * 1000))   # 100000 = 100% opaque
    return s


def _section_badge(slide, label: str, left: float, top: float):
    """Badge pill arrondi pour l'étiquette de section."""
    badge_w = min(len(label) * 0.085 + 0.4, 5.0)
    pill = _rounded_rect(slide, left, top, badge_w, 0.28, C_ACCENT_MID)
    tb = _tb(slide, left + 0.1, top + 0.02, badge_w - 0.1, 0.25)
    tf = tb.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = label.upper()
    _run_fmt(run, 8, C_ACCENT2, bold=True)


# ═══════════════════════════════════════════════════════
#  SLIDE TITRE – Design splitté
# ═══════════════════════════════════════════════════════

def _make_title_slide(prs, specialite: str, module: str, chapitre: str, niveau: str,
                      title_image: bytes = None, photographer: str = ''):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, C_BG)

    # ── Panneau gauche violet ──────────────────────────
    _rect(slide, 0, 0, 4.4, 7.5, C_PANEL)
    # Bande inférieure plus sombre sur le panneau
    _rect(slide, 0, 5.6, 4.4, 1.9, C_ACCENT_DARK)
    # Ligne de séparation subtile
    _rect(slide, 0, 5.58, 4.4, 0.04, C_ACCENT2)

    # ── Déco panneau gauche ───────────────────────────
    circ = slide.shapes.add_shape(9, Inches(2.8), Inches(-1.0), Inches(3.0), Inches(3.0))
    circ.fill.solid()
    circ.fill.fore_color.rgb = C_ACCENT_DARK
    _no_line(circ)

    # ── Textes panneau gauche ─────────────────────────
    tb_spec = _tb(slide, 0.35, 1.4, 3.7, 0.5)
    tf = tb_spec.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = specialite.upper()
    _run_fmt(run, 13, C_WHITE, bold=True)

    _rect(slide, 0.35, 2.0, 1.2, 0.04, C_WHITE)

    _rounded_rect(slide, 0.35, 2.2, 1.5, 0.38, C_ACCENT_DARK)
    tb_niv = _tb(slide, 0.45, 2.25, 1.3, 0.3)
    p2 = tb_niv.text_frame.paragraphs[0]
    p2.alignment = PP_ALIGN.LEFT
    run2 = p2.add_run()
    run2.text = f"NIVEAU {niveau.upper()}"
    _run_fmt(run2, 11, C_ACCENT2, bold=True)

    tb_mod = _tb(slide, 0.35, 5.75, 3.7, 0.9)
    tf_mod = tb_mod.text_frame
    tf_mod.word_wrap = True
    p3 = tf_mod.paragraphs[0]
    run3 = p3.add_run()
    run3.text = module
    _run_fmt(run3, 12, RGBColor(0xC7, 0xD2, 0xFE), italic=True)

    # ── Panneau droit : image ou déco ─────────────────
    RIGHT_L = 4.4
    RIGHT_W = 13.33 - RIGHT_L   # 8.93"

    if title_image:
        # Image de fond sur tout le panneau droit
        slide.shapes.add_picture(
            BytesIO(title_image),
            Inches(RIGHT_L), Inches(0), Inches(RIGHT_W), Inches(7.5)
        )
        # Overlay sombre pour lisibilité du texte (70% opaque)
        _add_transparent_rect(slide, RIGHT_L, 0, RIGHT_W, 7.5, C_BG, 70)
        # Gradient plus dense en bas (bande titre)
        _add_transparent_rect(slide, RIGHT_L, 4.5, RIGHT_W, 3.0, C_BG, 85)
    else:
        # Déco par défaut : grand cercle sombre
        circ2 = slide.shapes.add_shape(9, Inches(9.5), Inches(4.5), Inches(4.5), Inches(4.5))
        circ2.fill.solid()
        circ2.fill.fore_color.rgb = C_ACCENT_DARK
        _no_line(circ2)

    # Titre principal
    tb_title = _tb(slide, 4.75, 1.5, 8.2, 4.2)
    tf_title = tb_title.text_frame
    tf_title.word_wrap = True
    p_title = tf_title.paragraphs[0]
    _add_runs(p_title, chapitre, 36, C_WHITE, base_bold=True)
    p_title.alignment = PP_ALIGN.LEFT
    p_title.space_after = Pt(10)

    # Ligne déco sous titre
    _rect(slide, 4.75, 6.1, 2.0, 0.05, C_ACCENT)

    # Attribution photographe Unsplash (obligatoire)
    if title_image and photographer:
        tb_photo = _tb(slide, RIGHT_L + 0.15, 7.2, RIGHT_W - 0.3, 0.28)
        p_ph = tb_photo.text_frame.paragraphs[0]
        p_ph.alignment = PP_ALIGN.RIGHT
        run_ph = p_ph.add_run()
        run_ph.text = f"Photo: {photographer} / Unsplash"
        _run_fmt(run_ph, 7, C_TEXT_MUTED)

    return slide


# ═══════════════════════════════════════════════════════
#  SLIDE DE SECTION – Fond bicolore
# ═══════════════════════════════════════════════════════

def _make_section_slide(prs, title: str, numero: int = 0,
                        section_image: bytes = None, photographer: str = ''):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    SPLIT   = 6.0               # largeur panneau gauche quand image présente
    RIGHT_W = 13.33 - SPLIT     # 7.33"

    if section_image:
        _set_bg(slide, C_ACCENT_DARK)

        # ── Panneau gauche violet ──────────────────────────
        _rect(slide, 0, 0, SPLIT, 7.5, C_ACCENT)
        _rect(slide, 0, 0, SPLIT, 1.1, C_ACCENT_DARK)
        _rect(slide, 0, 6.3, SPLIT, 1.2, C_ACCENT_DARK)
        _rect(slide, 0, 1.08, SPLIT, 0.04, C_ACCENT2)
        _rect(slide, 0, 6.28, SPLIT, 0.04, C_ACCENT2)

        # ── Panneau droit : image + overlay ───────────────
        slide.shapes.add_picture(
            BytesIO(section_image),
            Inches(SPLIT), Inches(0), Inches(RIGHT_W), Inches(7.5)
        )
        _add_transparent_rect(slide, SPLIT, 0, RIGHT_W, 7.5, C_BG, 45)

        # Grand chiffre romain watermark (droite)
        if 0 < numero <= len(CHIFFRES_ROMAINS):
            tb_num = _tb(slide, SPLIT + 0.2, 0.3, RIGHT_W - 0.3, 6.5)
            tf = tb_num.text_frame
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.RIGHT
            run = p.add_run()
            run.text = CHIFFRES_ROMAINS[numero - 1]
            _run_fmt(run, 180, RGBColor(0xA0, 0xA3, 0xFF), bold=True)

        # Attribution photographe
        if photographer:
            tb_photo = _tb(slide, SPLIT + 0.15, 7.2, RIGHT_W - 0.3, 0.28)
            p_ph = tb_photo.text_frame.paragraphs[0]
            p_ph.alignment = PP_ALIGN.RIGHT
            run_ph = p_ph.add_run()
            run_ph.text = f"Photo: {photographer} / Unsplash"
            _run_fmt(run_ph, 7, C_TEXT_MUTED)

        title_w   = SPLIT - 0.6
        font_size = 36

    else:
        # ── Design original plein écran ───────────────────
        _set_bg(slide, C_ACCENT)
        _rect(slide, 0, 0, 13.33, 1.1, C_ACCENT_DARK)
        _rect(slide, 0, 6.3, 13.33, 1.2, C_ACCENT_DARK)
        _rect(slide, 0, 1.08, 13.33, 0.04, C_ACCENT2)
        _rect(slide, 0, 6.28, 13.33, 0.04, C_ACCENT2)

        if 0 < numero <= len(CHIFFRES_ROMAINS):
            tb_num = _tb(slide, 7.5, 0.5, 5.5, 6.0)
            tf = tb_num.text_frame
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.RIGHT
            run = p.add_run()
            run.text = CHIFFRES_ROMAINS[numero - 1]
            _run_fmt(run, 200, RGBColor(0x7C, 0x7F, 0xF5), bold=True)

        title_w   = 10.0
        font_size = 40

    # ── Textes communs (panneau gauche) ───────────────────
    tb_lbl = _tb(slide, 0.6, 0.3, 5, 0.45)
    p_lbl = tb_lbl.text_frame.paragraphs[0]
    run_lbl = p_lbl.add_run()
    run_lbl.text = f"SECTION {CHIFFRES_ROMAINS[numero - 1]}" if 0 < numero <= len(CHIFFRES_ROMAINS) else "SECTION"
    _run_fmt(run_lbl, 11, RGBColor(0xC7, 0xD2, 0xFE))

    tb = _tb(slide, 0.6, 1.5, title_w, 4.5)
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    _add_runs(p, title, font_size, C_WHITE, base_bold=True)
    p.alignment = PP_ALIGN.LEFT

    return slide


# ═══════════════════════════════════════════════════════
#  SLIDE DE CONTENU – Barre gauche + badge section
# ═══════════════════════════════════════════════════════

def _content_base(prs, title: str, section_label: str = ''):
    """Crée la structure de base d'une slide de contenu (fond + déco)."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, C_BG_CARD)

    # Barre gauche accent
    _rect(slide, 0, 0, 0.09, 7.5, C_ACCENT)

    # Barre horizontale haute (fine)
    _rect(slide, 0.09, 0, 13.24, 0.05, C_ACCENT_MID)

    # Badge section
    if section_label:
        _section_badge(slide, section_label, 0.22, 0.12)

    return slide


def _make_content_slide(prs, title: str, content_lines: list[str],
                        is_bullets: bool = True, section_label: str = ''):
    slide = _content_base(prs, title, section_label)

    # Titre
    top_title = 0.5 if section_label else 0.18
    tb_title = _tb(slide, 0.22, top_title, 12.9, 1.0)
    tf = tb_title.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    _add_runs(p, title, 24, C_WHITE, base_bold=True)

    # Séparateur
    sep_top = top_title + 1.0
    _rect(slide, 0.22, sep_top, 12.9, 0.025, C_ACCENT)

    # Corps
    body_top = sep_top + 0.18
    body_h   = 7.5 - body_top - 0.15
    tb_body = _tb(slide, 0.22, body_top, 12.9, body_h)
    tf = tb_body.text_frame
    tf.word_wrap = True

    for i, line in enumerate(content_lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_before = Pt(5 if is_bullets else 3)
        p.space_after  = Pt(2)
        if is_bullets:
            run_b = p.add_run()
            run_b.text = '◆  '
            _run_fmt(run_b, 9, C_BULLET, bold=True)
            _add_runs(p, line, 13, C_TEXT_LIGHT)
        else:
            _add_runs(p, line, 13, C_TEXT_LIGHT)

    return slide


def _make_two_column_slide(prs, title: str, bullets: list[str], section_label: str = ''):
    slide = _content_base(prs, title, section_label)

    top_title = 0.5 if section_label else 0.18
    tb_title = _tb(slide, 0.22, top_title, 12.9, 1.0)
    tf = tb_title.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    _add_runs(p, title, 24, C_WHITE, base_bold=True)

    sep_top = top_title + 1.0
    _rect(slide, 0.22, sep_top, 12.9, 0.025, C_ACCENT)

    body_top = sep_top + 0.18
    body_h   = 7.5 - body_top - 0.15

    mid = (len(bullets) + 1) // 2
    col1, col2 = bullets[:mid], bullets[mid:]

    # Séparateur vertical central
    _rect(slide, 6.8, body_top, 0.02, body_h, C_ACCENT_MID)

    for col_lines, lx in [(col1, 0.22), (col2, 6.95)]:
        tb = _tb(slide, lx, body_top, 6.35, body_h)
        tf = tb.text_frame
        tf.word_wrap = True
        for i, line in enumerate(col_lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.space_before = Pt(5)
            p.space_after  = Pt(2)
            run_b = p.add_run()
            run_b.text = '◆  '
            _run_fmt(run_b, 9, C_BULLET, bold=True)
            _add_runs(p, line, 13, C_TEXT_LIGHT)

    return slide


# ═══════════════════════════════════════════════════════
#  SLIDE TABLEAU
# ═══════════════════════════════════════════════════════

def _make_table_slide(prs, title: str, headers: list[str], rows: list[list[str]],
                      section_label: str = ''):
    slide = _content_base(prs, title, section_label)

    top_title = 0.5 if section_label else 0.18
    tb_title = _tb(slide, 0.22, top_title, 12.9, 1.0)
    tf = tb_title.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    _add_runs(p, title, 24, C_WHITE, base_bold=True)

    sep_top = top_title + 1.0
    _rect(slide, 0.22, sep_top, 12.9, 0.025, C_ACCENT)

    n_cols = max(len(headers), max((len(r) for r in rows), default=0))
    n_rows = min(len(rows) + 1, 12)
    if n_cols == 0 or n_rows < 2:
        return slide

    tbl_top  = Inches(sep_top + 0.18)
    tbl_left = Inches(0.22)
    tbl_w    = Inches(12.9)
    row_h    = Inches(min(0.52, 5.6 / n_rows))
    tbl      = slide.shapes.add_table(n_rows, n_cols, tbl_left, tbl_top, tbl_w, row_h * n_rows).table

    col_w = tbl_w // n_cols
    for col in tbl.columns:
        col.width = col_w

    def _cell(cell, bg: RGBColor, text: str, bold=False, align=PP_ALIGN.CENTER):
        cell.fill.solid()
        cell.fill.fore_color.rgb = bg
        tf = cell.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = align
        p.space_before = Pt(2)
        _add_runs(p, text, 11, C_WHITE, base_bold=bold)

    for j, h in enumerate(headers[:n_cols]):
        _cell(tbl.cell(0, j), C_TABLE_HDR, h, bold=True)

    for i, row in enumerate(rows[:n_rows - 1]):
        bg = C_TABLE_ROW1 if i % 2 == 0 else C_TABLE_ROW2
        for j in range(n_cols):
            _cell(tbl.cell(i + 1, j), bg, row[j] if j < len(row) else '', align=PP_ALIGN.LEFT)

    return slide


# ═══════════════════════════════════════════════════════
#  SLIDE DÉFINITIONS
# ═══════════════════════════════════════════════════════

def _make_definitions_slide(prs, items: list[tuple[str, str]]):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, C_BG_CARD)
    _rect(slide, 0, 0, 0.09, 7.5, C_ACCENT)

    # Header band
    _rect(slide, 0.09, 0, 13.24, 0.75, C_ACCENT_DARK)

    tb_hdr = _tb(slide, 0.3, 0.1, 12.7, 0.55)
    p = tb_hdr.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = '  DÉFINITIONS DES CONCEPTS CLÉS'
    _run_fmt(run, 16, C_WHITE, bold=True)

    # Ligne sous le header
    _rect(slide, 0.09, 0.73, 13.24, 0.03, C_ACCENT)

    tb_body = _tb(slide, 0.3, 0.9, 12.85, 6.4)
    tf = tb_body.text_frame
    tf.word_wrap = True

    for i, (terme, definition) in enumerate(items[:10]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_before = Pt(5)
        # Puce + terme
        run_b = p.add_run()
        run_b.text = '◆ '
        _run_fmt(run_b, 10, C_BULLET, bold=True)
        run_t = p.add_run()
        run_t.text = f"{_clean(terme)}  "
        _run_fmt(run_t, 13, C_ACCENT2, bold=True)
        run_d = p.add_run()
        run_d.text = _clean(definition)
        _run_fmt(run_d, 12, C_TEXT_LIGHT)

    return slide


# ═══════════════════════════════════════════════════════
#  SLIDE POINTS IMPORTANTS – Numéros cerclés
# ═══════════════════════════════════════════════════════

def _make_key_points_slide(prs, points: list[str]):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, C_BG_CARD)
    _rect(slide, 0, 0, 0.09, 7.5, C_ACCENT)

    # Header band
    _rect(slide, 0.09, 0, 13.24, 0.75, C_ACCENT_DARK)

    tb_hdr = _tb(slide, 0.3, 0.1, 12.7, 0.55)
    p = tb_hdr.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = '  POINTS IMPORTANTS À RETENIR'
    _run_fmt(run, 16, C_WHITE, bold=True)

    _rect(slide, 0.09, 0.73, 13.24, 0.03, C_ACCENT)

    # Mise en page 2 colonnes si > 6 points
    pts = points[:12]
    if len(pts) > 6:
        mid = (len(pts) + 1) // 2
        cols = [(pts[:mid], 0.3), (pts[mid:], 6.85)]
        _rect(slide, 6.76, 0.85, 0.02, 6.5, C_ACCENT_MID)
    else:
        cols = [(pts, 0.3)]

    for col_pts, lx in cols:
        col_w = 6.2 if len(cols) > 1 else 12.85
        tb = _tb(slide, lx, 0.9, col_w, 6.4)
        tf = tb.text_frame
        tf.word_wrap = True
        for i, point in enumerate(col_pts):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.space_before = Pt(6)
            p.space_after  = Pt(2)
            idx = pts.index(point)
            run_num = p.add_run()
            run_num.text = f"{CIRCLED_NUMS[idx]}  "
            _run_fmt(run_num, 15, C_ACCENT, bold=True)
            _add_runs(p, point, 13, C_TEXT_LIGHT)

    return slide


# ═══════════════════════════════════════════════════════
#  POINT D'ENTRÉE
# ═══════════════════════════════════════════════════════

def markdown_to_pptx(contenu: str, specialite: str, module: str,
                     chapitre: str, niveau: str = '',
                     title_image: bytes = None, photographer: str = '',
                     section_images: list = None) -> bytes:
    prs = Presentation()
    prs.slide_width  = SLIDE_W
    prs.slide_height = SLIDE_H

    _make_title_slide(prs, specialite, module, chapitre, niveau,
                      title_image=title_image, photographer=photographer)

    SKIP      = {'tableau comparatif', 'synthèse visuelle', 'pour aller plus loin'}
    SEC_DEF   = {'définitions des concepts clés', 'définitions'}
    SEC_PTS   = {'points importants à retenir', 'points clés', 'à retenir'}

    section_counter = 0

    for section in re.split(r'\n(?=## )', contenu):
        section = section.strip()
        if not section.startswith('##'):
            continue

        lines        = section.split('\n')
        h2_title     = _clean(lines[0].lstrip('#').strip())
        section_body = '\n'.join(lines[1:])
        h2_lower     = h2_title.lower()

        if any(kw in h2_lower for kw in SKIP):
            continue

        if any(kw in h2_lower for kw in SEC_DEF):
            items = _parse_definitions(section_body)
            if items:
                _make_definitions_slide(prs, items)
            continue

        if any(kw in h2_lower for kw in SEC_PTS):
            points = _extract_bullets(section_body, max_b=12)
            if not points:
                points = _wrap_text(_first_paragraph(section_body), 120)
            if points:
                _make_key_points_slide(prs, points)
            continue

        section_counter += 1
        sec_img, sec_photo = (
            section_images[section_counter - 1]
            if section_images and section_counter - 1 < len(section_images)
            else (None, '')
        )
        _make_section_slide(prs, h2_title, numero=section_counter,
                            section_image=sec_img, photographer=sec_photo or '')

        subsections    = [s.strip() for s in re.split(r'\n(?=### )', section_body) if s.strip()]
        has_subsections = any(s.startswith('###') for s in subsections)

        if has_subsections:
            intro = subsections[0] if not subsections[0].startswith('###') else ''
            if intro:
                headers, rows = _parse_md_table(intro)
                if headers and rows:
                    _make_table_slide(prs, h2_title, headers, rows, section_label=h2_title)
                else:
                    para = _first_paragraph(intro)
                    if para:
                        _make_content_slide(prs, h2_title, _wrap_text(para, 95),
                                            is_bullets=False, section_label=h2_title)

            for sub in subsections:
                if not sub.startswith('###'):
                    continue
                sub_lines = sub.split('\n')
                h3_title  = _clean(sub_lines[0].lstrip('#').strip())
                sub_body  = '\n'.join(sub_lines[1:])

                headers, rows = _parse_md_table(sub_body)
                if headers and rows:
                    _make_table_slide(prs, h3_title, headers, rows, section_label=h2_title)
                    continue

                bullets = _extract_bullets(sub_body)
                if bullets:
                    if len(bullets) > MAX_BULLETS_SINGLE:
                        _make_two_column_slide(prs, h3_title, bullets[:MAX_BULLETS_COL * 2],
                                               section_label=h2_title)
                    else:
                        _make_content_slide(prs, h3_title, bullets,
                                            is_bullets=True, section_label=h2_title)
                else:
                    para = _first_paragraph(sub_body)
                    if para:
                        _make_content_slide(prs, h3_title, _wrap_text(para, 95),
                                            is_bullets=False, section_label=h2_title)
        else:
            headers, rows = _parse_md_table(section_body)
            if headers and rows:
                _make_table_slide(prs, h2_title, headers, rows)
            else:
                bullets = _extract_bullets(section_body)
                if bullets:
                    if len(bullets) > MAX_BULLETS_SINGLE:
                        _make_two_column_slide(prs, h2_title, bullets[:MAX_BULLETS_COL * 2])
                    else:
                        _make_content_slide(prs, h2_title, bullets, is_bullets=True)
                else:
                    para = _first_paragraph(section_body)
                    if para:
                        _make_content_slide(prs, h2_title, _wrap_text(para, 95), is_bullets=False)

    buf = BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf.read()
