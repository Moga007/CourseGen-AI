"""
Module de conversion du cours Markdown en prompt structuré pour Beautiful.ai.
Génère un prompt au format "slide N: titre\ncontenu\n---" pour contrôler
la répartition des slides.
"""

import re

MAX_SLIDE_CHARS = 450  # Garder les slides concis pour Beautiful.ai


def _clean_markdown(text: str) -> str:
    """Supprime la mise en forme Markdown (gras, italique, code inline)."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    return text.strip()


def _truncate(text: str, max_chars: int = MAX_SLIDE_CHARS) -> str:
    """Tronque le texte proprement sur le dernier espace."""
    text = _clean_markdown(text)
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(' ', 1)[0] + '…'


def _extract_bullets(text: str, max_bullets: int = 5) -> list[str]:
    """Extrait les points de liste depuis un texte Markdown."""
    bullets = []
    for line in text.split('\n'):
        line = line.strip()
        # Listes non-ordonnées
        if re.match(r'^[-*•]\s', line):
            bullet = _clean_markdown(line[2:].strip())
            if bullet:
                bullets.append(bullet)
        # Listes ordonnées
        elif re.match(r'^\d+\.\s', line):
            bullet = _clean_markdown(re.sub(r'^\d+\.\s', '', line).strip())
            if bullet:
                bullets.append(bullet)
        if len(bullets) >= max_bullets:
            break
    return bullets


def _first_paragraph(text: str) -> str:
    """Retourne le premier paragraphe non-vide d'un texte."""
    for block in text.split('\n\n'):
        block = block.strip()
        # Ignorer les lignes de tableau et les titres
        if block and not block.startswith('|') and not block.startswith('#'):
            return _truncate(block)
    return ''


def markdown_to_slides_prompt(
    contenu: str,
    specialite: str,
    module: str,
    chapitre: str
) -> str:
    """
    Convertit le contenu Markdown d'un cours en prompt structuré pour Beautiful.ai.

    Format de sortie :
        slide 1: Titre
        Contenu
        ---
        slide 2: Titre
        Contenu
        ---
        ...

    Args:
        contenu: Le cours complet en Markdown.
        specialite: La spécialité académique.
        module: Le nom du module.
        chapitre: Le titre du chapitre.

    Returns:
        Le prompt structuré prêt à envoyer à l'API Beautiful.ai.
    """
    slides = []
    slide_num = 1

    # --- Slide 1 : Titre ---
    slides.append(
        f"slide {slide_num}: {chapitre}\n"
        f"Module : {module}\n"
        f"Spécialité : {specialite}"
    )
    slide_num += 1

    # Sections à ignorer (trop techniques ou mal adaptées au format slide)
    SECTIONS_A_IGNORER = {'tableau comparatif', 'synthèse visuelle', 'pour aller plus loin'}

    # Découper par sections H2 (## ...)
    # On enlève le premier fragment vide éventuel avant le premier ##
    raw_sections = re.split(r'\n(?=## )', contenu)

    for section in raw_sections:
        section = section.strip()
        if not section.startswith('##'):
            continue

        lines = section.split('\n')
        h2_title = _clean_markdown(lines[0].lstrip('#').strip())
        section_body = '\n'.join(lines[1:])

        # Ignorer certaines sections
        if any(kw in h2_title.lower() for kw in SECTIONS_A_IGNORER):
            continue

        # Découper par sous-sections H3 (### ...)
        subsections = re.split(r'\n(?=### )', section_body)
        subsections = [s.strip() for s in subsections if s.strip()]

        has_subsections = any(s.startswith('###') for s in subsections)

        if has_subsections:
            # Slide d'introduction de la partie (paragraphe intro H2)
            intro_text = subsections[0] if not subsections[0].startswith('###') else ''
            if intro_text:
                paragraph = _first_paragraph(intro_text)
                if paragraph:
                    slides.append(f"slide {slide_num}: {h2_title}\n{paragraph}")
                    slide_num += 1

            # Une slide par sous-section H3
            for sub in subsections:
                if not sub.startswith('###'):
                    continue
                sub_lines = sub.split('\n')
                h3_title = _clean_markdown(sub_lines[0].lstrip('#').strip())
                sub_body = '\n'.join(sub_lines[1:])

                bullets = _extract_bullets(sub_body, max_bullets=5)
                if bullets:
                    content = '\n'.join(f'• {b}' for b in bullets)
                else:
                    content = _first_paragraph(sub_body)

                if content:
                    slides.append(
                        f"slide {slide_num}: {h2_title} — {h3_title}\n{content}"
                    )
                    slide_num += 1

        else:
            # Pas de sous-sections : une seule slide pour la section
            bullets = _extract_bullets(section_body, max_bullets=6)
            if bullets:
                content = '\n'.join(f'• {b}' for b in bullets)
            else:
                content = _first_paragraph(section_body)

            if content:
                slides.append(f"slide {slide_num}: {h2_title}\n{content}")
                slide_num += 1

    return '\n---\n'.join(slides)
