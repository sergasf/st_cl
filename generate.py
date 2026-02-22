#!/usr/bin/env python3
"""
South Bear Studio — генератор index.html
Запуск: python3 generate.py
Сканирует папку photos/ и генерирует index.html с найденными файлами.
Требует Pillow для определения размеров изображений: pip install Pillow
"""

import os
import sys

PHOTOS_DIR = "photos"
OUTPUT_FILE = "index.html"

# Поддерживаемые форматы
IMAGE_EXTS = {".jpg", ".jpeg", ".webp", ".png", ".gif"}
VIDEO_EXTS = {".mp4", ".mov", ".webm"}

# Порядок отображения разделов и их русские названия
SECTION_ORDER = [
    "interior",
    "sofas",
    "chairs",
    "beds",
    "wardrobes",
    "kitchen",
    "materials",
]

SECTION_NAMES = {
    "interior":   "Интерьер",
    "sofas":      "Диваны",
    "chairs":     "Кресла",
    "beds":       "Кровати",
    "wardrobes":  "Шкафы",
    "kitchen":    "Кухни",
    "materials":  "Материалы",
}

SECTION_DESCS = {
    "interior": "Галерея проектов",
}


def get_image_dimensions(path):
    """Возвращает (width, height) или None если Pillow не установлен."""
    try:
        from PIL import Image
        with Image.open(path) as img:
            return img.size  # (width, height)
    except Exception:
        return None


def aspect_class(w, h):
    """Определяет CSS-класс карточки по соотношению сторон."""
    if w is None or h is None:
        return ""  # по умолчанию 3:4
    ratio = w / h
    if ratio > 1.6:
        return "gallery-item--wide"   # ландшафт (2:1 и шире)
    if ratio > 0.85:
        return "gallery-item--square" # квадрат
    return ""                          # портрет 3:4


def video_ratio_class(w, h):
    """CSS-класс контейнера видео по соотношению сторон."""
    if w is None or h is None:
        return "video-16-9"
    ratio = w / h
    if ratio > 1.4:
        return "video-16-9"
    if ratio > 0.85:
        return "video-1-1"
    return "video-3-4"


def video_max_width(w, h):
    """Ограничение ширины для нестандартных видео."""
    if w is None or h is None:
        return None
    ratio = w / h
    if ratio < 0.85:   # портрет
        return "360px"
    if ratio < 1.1:    # квадрат
        return "440px"
    return None


def scan_photos(photos_dir):
    """
    Возвращает dict: { folder_name: { 'images': [...], 'videos': [...] } }
    Каждый элемент: { 'path': 'photos/folder/file.jpg', 'w': int, 'h': int }
    """
    result = {}

    if not os.path.isdir(photos_dir):
        print(f"Ошибка: папка '{photos_dir}' не найдена. Запустите скрипт рядом с папкой photos/")
        sys.exit(1)

    # Сначала собираем все папки
    for entry in sorted(os.scandir(photos_dir), key=lambda e: e.name):
        if not entry.is_dir():
            continue
        folder = entry.name
        images = []
        videos = []

        for file in sorted(os.scandir(entry.path), key=lambda e: e.name):
            if not file.is_file():
                continue
            ext = os.path.splitext(file.name)[1].lower()
            rel_path = f"{photos_dir}/{folder}/{file.name}"

            if ext in IMAGE_EXTS:
                dims = get_image_dimensions(file.path)
                w, h = dims if dims else (None, None)
                images.append({"path": rel_path, "w": w, "h": h})
            elif ext in VIDEO_EXTS:
                videos.append({"path": rel_path, "w": None, "h": None})

        if images or videos:
            result[folder] = {"images": images, "videos": videos}

    return result


def render_image(item):
    """Генерирует HTML для одной картинки в галерее."""
    cls = aspect_class(item["w"], item["h"])
    extra = f" {cls}" if cls else ""
    path = item["path"]
    return (
        f'    <div class="gallery-item{extra}" onclick="openLightbox(\'{path}\')">\n'
        f'      <img src="{path}" alt="">\n'
        f'    </div>\n'
    )


def render_video(item):
    """Генерирует HTML для одной видеокарточки."""
    path = item["path"]
    ratio_cls = video_ratio_class(item["w"], item["h"])
    max_w = video_max_width(item["w"], item["h"])
    label = os.path.splitext(os.path.basename(path))[0].replace("-", " ").replace("_", " ").capitalize()

    card = (
        f'    <div class="video-card">\n'
        f'      <div class="video-embed {ratio_cls}">\n'
        f'        <video controls preload="metadata" playsinline>\n'
        f'          <source src="{path}" type="video/mp4">\n'
        f'        </video>\n'
        f'      </div>\n'
        f'      <div class="video-label">{label}</div>\n'
        f'    </div>\n'
    )

    if max_w:
        return f'  <div style="max-width: {max_w}; margin-top: 20px;">\n{card}  </div>\n'
    return card


def render_section(folder, data, num):
    """Генерирует HTML одного раздела."""
    name = SECTION_NAMES.get(folder, folder.capitalize())
    desc = SECTION_DESCS.get(folder, "")
    desc_html = f'    <span class="section-desc">{desc}</span>\n' if desc else ""
    anchor = folder

    html = f'\n<div class="section-wrap" id="{anchor}">\n'
    html += f'  <div class="section-header">\n'
    html += f'    <span class="section-num">{num:02d}</span>\n'
    html += f'    <h2 class="section-title">{name}</h2>\n'
    html += desc_html
    html += f'  </div>\n'

    images = data["images"]
    videos = data["videos"]

    # Галерея изображений
    if images:
        html += '  <div class="gallery">\n'
        for item in images:
            html += render_image(item)
        html += '  </div>\n'

    # Видео
    if videos:
        # Если несколько видео 16:9 — сетка, иначе по одному
        wide_videos = [v for v in videos if video_ratio_class(v["w"], v["h"]) == "video-16-9"]
        other_videos = [v for v in videos if video_ratio_class(v["w"], v["h"]) != "video-16-9"]

        if len(wide_videos) > 1:
            mt = ' style="margin-top: 20px;"' if images else ""
            html += f'  <div class="video-grid"{mt}>\n'
            for v in wide_videos:
                html += render_video(v)
            html += '  </div>\n'
        else:
            for v in wide_videos:
                html += render_video(v)

        for v in other_videos:
            html += render_video(v)

    html += '</div>\n'
    return html


# ── CSS ─────────────────────────────────────────────────────────────────────

CSS = """
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg: #0e0e0e;
      --surface: #161616;
      --border: #2a2a2a;
      --text: #e8e2d9;
      --text-muted: #7a7570;
      --accent: #c8a96e;
      --accent-dim: rgba(200,169,110,0.12);
    }

    html { scroll-behavior: smooth; }

    body {
      background: var(--bg);
      color: var(--text);
      font-family: 'Montserrat', sans-serif;
      font-weight: 300;
      line-height: 1.7;
      overflow-x: hidden;
    }

    nav {
      position: fixed;
      top: 0; left: 0; right: 0;
      z-index: 100;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 18px 48px;
      background: rgba(14,14,14,0.92);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border);
    }

    .nav-logo img {
      height: 36px;
      filter: invert(1) brightness(0.9);
    }

    .nav-links {
      display: flex;
      gap: 28px;
      list-style: none;
    }

    .nav-links a {
      color: var(--text-muted);
      text-decoration: none;
      font-size: 11px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      transition: color 0.3s;
    }

    .nav-links a:hover { color: var(--accent); }

    .hero {
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 120px 48px 80px;
      position: relative;
    }

    .hero::before {
      content: '';
      position: absolute;
      inset: 0;
      background: radial-gradient(ellipse 80% 60% at 50% 40%, rgba(200,169,110,0.07) 0%, transparent 70%);
      pointer-events: none;
    }

    .hero-logo {
      width: min(420px, 80vw);
      filter: invert(1) brightness(0.95);
      margin-bottom: 40px;
      animation: fadeUp 1s ease both;
    }

    .hero-tagline {
      font-family: 'Cormorant Garamond', serif;
      font-size: clamp(18px, 2.5vw, 26px);
      font-style: italic;
      color: var(--text-muted);
      letter-spacing: 0.04em;
      animation: fadeUp 1s 0.2s ease both;
    }

    .hero-divider {
      width: 60px; height: 1px;
      background: var(--accent);
      margin: 32px auto;
      animation: fadeUp 1s 0.3s ease both;
    }

    .hero-sub {
      font-size: 12px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--text-muted);
      animation: fadeUp 1s 0.4s ease both;
    }

    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(28px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    .section-wrap {
      padding: 100px 48px;
      max-width: 1280px;
      margin: 0 auto;
    }

    .section-header {
      display: flex;
      align-items: baseline;
      gap: 24px;
      margin-bottom: 60px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 24px;
    }

    .section-num {
      font-family: 'Cormorant Garamond', serif;
      font-size: 13px;
      color: var(--accent);
      letter-spacing: 0.1em;
    }

    .section-title {
      font-family: 'Cormorant Garamond', serif;
      font-size: clamp(32px, 4vw, 52px);
      font-weight: 300;
      letter-spacing: 0.02em;
      flex: 1;
    }

    .section-desc {
      font-size: 12px;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      color: var(--text-muted);
      align-self: center;
    }

    .gallery {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 3px;
    }

    .gallery-item {
      aspect-ratio: 3/4;
      overflow: hidden;
      background: var(--surface);
      cursor: pointer;
    }

    .gallery-item--wide {
      aspect-ratio: 2/1;
      grid-column: span 2;
    }

    .gallery-item--square {
      aspect-ratio: 1/1;
    }

    .gallery-item img {
      width: 100%; height: 100%;
      object-fit: cover;
      transition: transform 0.6s ease;
      display: block;
    }

    .gallery-item:hover img { transform: scale(1.06); }

    .video-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(440px, 1fr));
      gap: 20px;
    }

    .video-card {
      background: var(--surface);
      border: 1px solid var(--border);
    }

    .video-16-9 { aspect-ratio: 16/9; }
    .video-1-1  { aspect-ratio: 1/1; }
    .video-3-4  { aspect-ratio: 3/4; }

    .video-embed {
      width: 100%;
      background: #080808;
      overflow: hidden;
    }

    .video-embed video {
      width: 100%; height: 100%;
      display: block;
      object-fit: cover;
    }

    .video-label {
      padding: 14px 20px;
      font-size: 11px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--text-muted);
      border-top: 1px solid var(--border);
    }

    .lightbox {
      display: none;
      position: fixed;
      inset: 0;
      z-index: 200;
      background: rgba(0,0,0,0.92);
      align-items: center;
      justify-content: center;
    }

    .lightbox.open { display: flex; }

    .lightbox img {
      max-width: 90vw;
      max-height: 90vh;
      object-fit: contain;
    }

    .lightbox-close {
      position: absolute;
      top: 24px; right: 32px;
      font-size: 36px;
      color: var(--text-muted);
      cursor: pointer;
      transition: color 0.2s;
      line-height: 1;
    }

    .lightbox-close:hover { color: var(--accent); }

    .sep {
      width: 100%; height: 1px;
      background: linear-gradient(90deg, transparent, var(--border), transparent);
    }

    .contact-section {
      text-align: center;
      padding: 100px 48px;
    }

    .contact-inner { max-width: 480px; margin: 0 auto; }

    .contact-title {
      font-family: 'Cormorant Garamond', serif;
      font-size: clamp(28px, 3.5vw, 44px);
      font-weight: 300;
      margin-bottom: 16px;
    }

    .contact-sub {
      font-size: 12px;
      color: var(--text-muted);
      letter-spacing: 0.1em;
      margin-bottom: 40px;
      line-height: 2;
    }

    .contact-link {
      display: inline-block;
      padding: 14px 40px;
      border: 1px solid var(--accent);
      color: var(--accent);
      text-decoration: none;
      font-size: 11px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      transition: all 0.3s;
    }

    .contact-link:hover { background: var(--accent); color: var(--bg); }

    footer {
      border-top: 1px solid var(--border);
      padding: 32px 48px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11px;
      color: var(--text-muted);
      letter-spacing: 0.08em;
    }

    footer img {
      height: 24px;
      filter: invert(1) brightness(0.5);
    }

    @media (max-width: 600px) {
      nav { padding: 16px 20px; }
      .nav-links { display: none; }
      .section-wrap { padding: 60px 20px; }
      .video-grid { grid-template-columns: 1fr; }
      .gallery-item--wide { grid-column: span 1; aspect-ratio: 2/1; }
      footer { flex-direction: column; gap: 16px; text-align: center; }
    }
"""

JS = """
  function openLightbox(src) {
    document.getElementById('lightbox-img').src = src;
    document.getElementById('lightbox').classList.add('open');
  }

  function closeLightbox() {
    document.getElementById('lightbox').classList.remove('open');
    document.getElementById('lightbox-img').src = '';
  }

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeLightbox();
  });
"""


def build_html(sections_data):
    """Собирает итоговый HTML."""

    # Определяем порядок: сначала из SECTION_ORDER, потом остальные алфавитно
    ordered_folders = []
    for f in SECTION_ORDER:
        if f in sections_data:
            ordered_folders.append(f)
    for f in sorted(sections_data.keys()):
        if f not in ordered_folders:
            ordered_folders.append(f)

    # Навигация
    nav_items = ""
    for folder in ordered_folders:
        name = SECTION_NAMES.get(folder, folder.capitalize())
        nav_items += f'    <li><a href="#{folder}">{name}</a></li>\n'
    nav_items += '    <li><a href="#contact">Контакты</a></li>\n'

    # Разделы
    sections_html = ""
    for i, folder in enumerate(ordered_folders, 1):
        sections_html += render_section(folder, sections_data[folder], i)
        sections_html += '\n<div class="sep"></div>\n'

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>South Bear Studio</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=Montserrat:wght@300;400;500&display=swap" rel="stylesheet">
  <style>{CSS}
  </style>
</head>
<body>

<div class="lightbox" id="lightbox" onclick="closeLightbox()">
  <span class="lightbox-close">x</span>
  <img id="lightbox-img" src="" alt="">
</div>

<nav>
  <a class="nav-logo" href="#top">
    <img src="photos/logo.png" alt="South Bear Studio">
  </a>
  <ul class="nav-links">
{nav_items}  </ul>
</nav>

<div class="hero" id="top">
  <img class="hero-logo" src="photos/logo.png" alt="South Bear Studio">
  <p class="hero-tagline">Мебель и интерьеры под заказ</p>
  <div class="hero-divider"></div>
  <p class="hero-sub">Производство · Поставки · Проектирование</p>
</div>

<div class="sep"></div>

{sections_html}

<div class="contact-section" id="contact">
  <div class="contact-inner">
    <h2 class="contact-title">Обсудим проект</h2>
    <p class="contact-sub">
      Мебель и материалы под заказ<br>
      Производство по чертежам<br>
      Поставки и таможенное оформление
    </p>
    <a class="contact-link" href="mailto:info@southbearstudio.com">Написать нам</a>
  </div>
</div>

<footer>
  <img src="photos/logo.png" alt="South Bear Studio">
  <span>2025 South Bear Studio</span>
</footer>

<script>
{JS}
</script>

</body>
</html>
"""
    return html


def main():
    print(f"Сканирую папку {PHOTOS_DIR}/...")

    try:
        from PIL import Image
        print("Pillow найден — определяю размеры изображений.")
    except ImportError:
        print("Pillow не установлен. Размеры изображений не определяются.")
        print("Установите: pip install Pillow")

    sections = scan_photos(PHOTOS_DIR)

    if not sections:
        print("Не найдено ни одного файла в подпапках photos/")
        sys.exit(1)

    print(f"Найдены разделы: {', '.join(sections.keys())}")
    for folder, data in sections.items():
        print(f"  {folder}: {len(data['images'])} фото, {len(data['videos'])} видео")

    html = build_html(sections)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\nГотово! Создан файл: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()