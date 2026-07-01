"""JM 插件 - 图片渲染"""
import base64
import io
import json
import os
from typing import List, Optional, Tuple

from nonebot.adapters.onebot.v11 import MessageSegment
from PIL import Image, ImageChops, ImageDraw, ImageFont

from .config import SEARCH_PAGE_SIZE

_json_path = os.path.join(os.path.dirname(__file__), '_HELP_SYMBOL_BASE64.json')
with open(_json_path, 'r', encoding='utf-8-sig') as _f:
    _SYMBOL_BASE64_DATA = json.load(_f)
_HELP_SYMBOL_BASE64 = _SYMBOL_BASE64_DATA.get('_HELP_SYMBOL_BASE64', '')
_DOWNLOAD_SYMBOL_BASE64 = _SYMBOL_BASE64_DATA.get('_DOWNLOAD_SYMBOL_BASE64', '')
_FINISH_SYMBOL_BASE64 = _SYMBOL_BASE64_DATA.get('_FINISH_SYMBOL_BASE64', '')
_HELP_SYMBOL_CACHE = {}
_DOWNLOAD_SYMBOL_CACHE = {}
_FINISH_SYMBOL_CACHE = {}
_HELP_SYMBOL_INLINE_BASE64 = ""


def _try_load_font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        "msyh.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for path in candidates:
        try:
            if os.path.exists(path):
                return ImageFont.truetype(path, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap_text(draw, text: str, font, max_width: int) -> List[str]:
    lines: List[str] = []
    for para in text.splitlines():
        if not para.strip():
            lines.append("")
            continue
        current = ""
        for ch in para:
            candidate = current + ch
            if draw.textlength(candidate, font=font) <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = ch
        if current:
            lines.append(current)
    return lines or [""]


def _mix(c1: Tuple[int, int, int], c2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _draw_firefly_help_bg(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    top = (235, 255, 249)
    mid = (205, 248, 238)
    bottom = (177, 232, 238)
    for y in range(height):
        t = y / max(1, height - 1)
        color = _mix(top, mid, t / 0.55) if t < 0.55 else _mix(mid, bottom, (t - 0.55) / 0.45)
        draw.line((0, y, width, y), fill=color)

    for x in range(-height, width, 64):
        draw.line((x, 0, x + height, height), fill=(156, 222, 214), width=1)
    for x in range(84, width, 126):
        draw.line((x, 0, x, height), fill=(221, 251, 245), width=1)
    for y in range(90, height, 108):
        draw.line((0, y, width, y), fill=(221, 251, 245), width=1)

    for box, fill in (
        ((-180, -130, 360, 310), (186, 255, 229)),
        ((width - 360, -120, width + 160, 330), (133, 228, 205)),
        ((width - 320, height - 360, width + 180, height + 110), (183, 243, 255)),
    ):
        draw.ellipse(box, fill=fill)

    for cx, cy, r in (
        (width - 122, 88, 8), (width - 190, 142, 5), (82, 116, 6),
        (150, height - 156, 5), (width - 230, height - 128, 6),
        (width - 94, height - 214, 4), (240, 74, 3),
    ):
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(250, 255, 252))


def _draw_gradient_roundrect(
    img: Image.Image,
    box: Tuple[int, int, int, int],
    radius: int,
    left: Tuple[int, int, int],
    right: Tuple[int, int, int],
    outline: Optional[Tuple[int, int, int]] = None,
    width: int = 1,
) -> None:
    x1, y1, x2, y2 = box
    patch_w, patch_h = x2 - x1, y2 - y1
    patch = Image.new("RGB", (patch_w, patch_h), left)
    pd = ImageDraw.Draw(patch)
    for x in range(patch_w):
        pd.line((x, 0, x, patch_h), fill=_mix(left, right, x / max(1, patch_w - 1)))
    mask = Image.new("L", (patch_w, patch_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, patch_w, patch_h), radius=radius, fill=255)
    img.paste(patch, (x1, y1), mask)
    if outline:
        ImageDraw.Draw(img).rounded_rectangle(box, radius=radius, outline=outline, width=width)


def _get_help_symbol(size: int = 132) -> Optional[Image.Image]:
    cached = _HELP_SYMBOL_CACHE.get(size)
    if cached is not None:
        return cached.copy()

    sources = [("file", os.path.join(os.path.dirname(__file__), "17.png"))]
    if _HELP_SYMBOL_INLINE_BASE64:
        sources.append(("base64", _HELP_SYMBOL_INLINE_BASE64))
    if _HELP_SYMBOL_BASE64:
        sources.append(("base64", _HELP_SYMBOL_BASE64))

    for source_type, source in sources:
        try:
            if source_type == "base64":
                raw = base64.b64decode(source)
                icon = Image.open(io.BytesIO(raw)).convert("RGBA")
            else:
                if not os.path.exists(source):
                    continue
                icon = Image.open(source).convert("RGBA")
            side = min(icon.width, icon.height)
            left = (icon.width - side) // 2
            top = (icon.height - side) // 2
            icon = icon.crop((left, top, left + side, top + side)).resize((size, size), Image.LANCZOS)
            rounded_mask = Image.new("L", (size, size), 0)
            ImageDraw.Draw(rounded_mask).rounded_rectangle((0, 0, size, size), radius=34, fill=255)
            alpha = icon.getchannel("A")
            icon.putalpha(ImageChops.multiply(alpha, rounded_mask))
            _HELP_SYMBOL_CACHE[size] = icon.copy()
            return icon
        except Exception:
            continue
    return None


def _get_status_symbol(
    size: int,
    cache: dict,
    inline_base64: str,
    fallback_filename: str,
) -> Optional[Image.Image]:
    cached = cache.get(size)
    if cached is not None:
        return cached.copy()

    sources = []
    if inline_base64:
        sources.append(("base64", inline_base64))
    sources.append(("file", os.path.join(os.path.dirname(__file__), fallback_filename)))

    for source_type, source in sources:
        try:
            if source_type == "base64":
                icon = Image.open(io.BytesIO(base64.b64decode(source))).convert("RGBA")
            else:
                if not os.path.exists(source):
                    continue
                icon = Image.open(source).convert("RGBA")

            icon.thumbnail((size, size), Image.LANCZOS)
            canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            x = (size - icon.width) // 2
            y = (size - icon.height) // 2
            canvas.paste(icon, (x, y), icon)
            cache[size] = canvas.copy()
            return canvas
        except Exception:
            continue
    return None


def _get_download_symbol(size: int = 118) -> Optional[Image.Image]:
    return _get_status_symbol(
        size, _DOWNLOAD_SYMBOL_CACHE, _DOWNLOAD_SYMBOL_BASE64, "dowload.png"
    )


def _get_finish_symbol(size: int = 118) -> Optional[Image.Image]:
    return _get_status_symbol(
        size, _FINISH_SYMBOL_CACHE, _FINISH_SYMBOL_BASE64, "finish.png"
    )


def _draw_firefly_help_card(
    draw: ImageDraw.ImageDraw,
    box: Tuple[int, int, int, int],
    title: str,
    items: List,
    accent: Tuple[int, int, int],
) -> None:
    x1, y1, x2, y2 = box
    card_w = x2 - x1
    title_font = _try_load_font(30, bold=True)
    body_font = _try_load_font(22)
    command_font = _try_load_font(20, bold=True)
    small_font = _try_load_font(17)

    draw.rounded_rectangle(box, radius=24, fill=(247, 255, 252), outline=(134, 221, 207), width=2)
    draw.rounded_rectangle((x1 + 16, y1 + 16, x2 - 16, y1 + 54), radius=16,
                           fill=(224, 255, 248), outline=(182, 238, 226), width=1)
    draw.ellipse((x1 + 28, y1 + 26, x1 + 42, y1 + 40), fill=accent)
    draw.text((x1 + 54, y1 + 21), title, font=title_font, fill=(13, 92, 91))
    draw.text((x2 - 104, y1 + 24), "FIREFLY", font=small_font, fill=(74, 154, 151))

    table_x1, table_y1 = x1 + 24, y1 + 76
    table_x2, table_y2 = x2 - 24, y2 - 24
    draw.rounded_rectangle((table_x1, table_y1, table_x2, table_y2), radius=18,
                           fill=(255, 255, 255), outline=(188, 235, 225), width=1)

    inner_w = table_x2 - table_x1 - 36
    y = table_y1 + 18
    for idx, item in enumerate(items):
        if isinstance(item, dict):
            command = str(item.get("cmd", "")).strip()
            desc = str(item.get("desc", "")).strip()
        elif isinstance(item, (tuple, list)) and len(item) >= 2:
            command = str(item[0]).strip()
            desc = str(item[1]).strip()
        else:
            command = ""
            desc = str(item).strip()

        command_w = 0
        if command:
            command_w = min(inner_w, int(draw.textlength(command, font=command_font)) + 30)
        desc_x = table_x1 + 28 + (command_w + 12 if command else 0)
        desc_w = max(120, table_x2 - desc_x - 18)
        desc_lines = _wrap_text(draw, desc, body_font, desc_w) if desc else []
        block_h = max(42, max(1, len(desc_lines)) * 28 + 14)

        if idx % 2:
            draw.rounded_rectangle((table_x1 + 8, y - 6, table_x2 - 8, y - 6 + block_h),
                                   radius=12, fill=(240, 255, 251))
        if command:
            pill = (table_x1 + 18, y + 4, table_x1 + 18 + command_w, y + 36)
            draw.rounded_rectangle(pill, radius=14, fill=(218, 255, 247), outline=accent, width=2)
            draw.text((pill[0] + 15, y + 8), command, font=command_font, fill=(9, 107, 104))
        else:
            draw.rounded_rectangle((table_x1 + 18, y + 8, table_x1 + 24, y + 30),
                                   radius=3, fill=accent)
            desc_x = table_x1 + 38
            desc_w = table_x2 - desc_x - 18
            desc_lines = _wrap_text(draw, desc, body_font, desc_w)
        for line_idx, line in enumerate(desc_lines[:3]):
            draw.text((desc_x, y + 6 + line_idx * 28), line, font=body_font, fill=(32, 73, 76))
        y += block_h + 10


def _render_card_image_bytes(
    title: str, subtitle: str, lines: List[str], accent: tuple
) -> bytes:
    width = 1080
    margin = 46
    card_padding = 42
    inner_width = width - margin * 2 - card_padding * 2

    title_font = _try_load_font(54, bold=True)
    subtitle_font = _try_load_font(26)
    body_font = _try_load_font(34)

    measure = Image.new("RGB", (width, 200), (255, 255, 255))
    measure_draw = ImageDraw.Draw(measure)

    wrapped_lines: List[str] = []
    for line in lines:
        wrapped_lines.extend(_wrap_text(measure_draw, line, body_font, inner_width))

    line_height = int(getattr(body_font, "size", 34) * 1.55)
    title_height = 76
    subtitle_height = 38
    body_height = max(line_height, len(wrapped_lines) * line_height)
    card_height = card_padding * 2 + title_height + subtitle_height + 26 + body_height
    height = card_height + margin * 2

    img = Image.new("RGBA", (width, height), (15, 26, 43, 255))
    draw = ImageDraw.Draw(img)

    top = accent
    bottom = (
        min(255, accent[0] + 85),
        min(255, accent[1] + 45),
        min(255, accent[2] + 25),
    )
    for y in range(height):
        ratio = y / max(1, height - 1)
        color = (
            int(top[0] * (1 - ratio) + bottom[0] * ratio),
            int(top[1] * (1 - ratio) + bottom[1] * ratio),
            int(top[2] * (1 - ratio) + bottom[2] * ratio),
            255,
        )
        draw.line([(0, y), (width, y)], fill=color)

    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((width - 360, -120, width + 80, 260), fill=(*accent, 58))
    glow_draw.ellipse((-180, height - 280, 220, height + 120), fill=(255, 255, 255, 28))
    img = Image.alpha_composite(img, glow)
    draw = ImageDraw.Draw(img)

    x1, y1 = margin, margin
    x2, y2 = width - margin, height - margin
    draw.rounded_rectangle(
        (x1, y1, x2, y2),
        radius=30,
        fill=(247, 249, 252, 240),
        outline=(255, 255, 255, 110),
        width=2,
    )

    badge_x = x1 + card_padding
    badge_y = y1 + 24
    draw.rounded_rectangle(
        (badge_x, badge_y, badge_x + 156, badge_y + 14),
        radius=7,
        fill=(*accent, 255),
    )

    tx = x1 + card_padding
    ty = y1 + card_padding + 18
    draw.text((tx, ty), title, font=title_font, fill=(22, 31, 48, 255))
    draw.text((tx, ty + title_height), subtitle, font=subtitle_font, fill=(89, 107, 132, 255))

    body_y = ty + title_height + subtitle_height + 26
    for line in wrapped_lines:
        draw.text((tx, body_y), line, font=body_font, fill=(41, 51, 66, 255))
        body_y += line_height

    out = io.BytesIO()
    img.convert("RGB").save(out, format="JPEG", quality=92, optimize=True)
    return out.getvalue()


def _image_message_from_bytes(data: bytes) -> MessageSegment:
    encoded = base64.b64encode(data).decode("utf-8")
    return MessageSegment.image(f"base64://{encoded}")


def _make_firefly_canvas(width: int, height: int) -> Image.Image:
    img = Image.new("RGB", (width, height), (234, 255, 249))
    draw = ImageDraw.Draw(img)
    _draw_firefly_help_bg(draw, width, height)
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((-170, -130, 380, 340), fill=(190, 255, 220, 86))
    glow_draw.ellipse((width - 390, -120, width + 160, 340), fill=(93, 206, 215, 70))
    glow_draw.ellipse((width - 330, height - 310, width + 130, height + 150), fill=(139, 230, 206, 54))
    return Image.alpha_composite(img.convert("RGBA"), glow)


def _draw_chip(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    font,
    fill: Tuple[int, int, int] = (226, 255, 248),
    outline: Tuple[int, int, int] = (126, 217, 202),
    text_fill: Tuple[int, int, int] = (10, 107, 104),
) -> Tuple[int, int, int, int]:
    chip_w = int(draw.textlength(text, font=font)) + 32
    box = (x, y, x + chip_w, y + 32)
    draw.rounded_rectangle(box, radius=14, fill=fill, outline=outline, width=1)
    draw.text((x + 16, y + 5), text, font=font, fill=text_fill)
    return box


def _draw_firefly_page_header(
    img: Image.Image,
    title: str,
    subtitle: str,
    badge: str,
    symbol: Optional[Image.Image] = None,
) -> Tuple[int, int, int, int]:
    draw = ImageDraw.Draw(img)
    width = img.width
    margin = 42
    header_h = 180
    header = (margin, margin, width - margin, margin + header_h)
    _draw_gradient_roundrect(img, header, 28, (16, 181, 164), (123, 229, 209),
                             outline=(236, 255, 249), width=3)
    draw = ImageDraw.Draw(img)
    x1, y1, x2, y2 = header
    title_font = _try_load_font(48, bold=True)
    subtitle_font = _try_load_font(23)
    badge_font = _try_load_font(18, bold=True)
    draw.rounded_rectangle((x1 + 14, y1 + 14, x2 - 14, y2 - 14),
                           radius=22, outline=(14, 127, 124), width=2)
    draw.text((x1 + 34, y1 + 34), title, font=title_font, fill=(248, 255, 252))
    draw.text((x1 + 36, y1 + 96), subtitle, font=subtitle_font, fill=(221, 255, 248))
    draw.line((x1 + 36, y2 - 42, x2 - 230, y2 - 42), fill=(8, 121, 118), width=3)
    _draw_chip(draw, x1 + 36, y2 - 34, badge, badge_font)
    if symbol:
        panel = (x2 - 176, y1 + 24, x2 - 42, y1 + 158)
        draw.rounded_rectangle(panel, radius=26, fill=(226, 255, 248, 120),
                               outline=(229, 255, 249), width=2)
        img.paste(symbol, (x2 - 163, y1 + 37), symbol)
    else:
        draw.text((x2 - 168, y1 + 38), "FIREFLY", font=badge_font, fill=(226, 255, 248))
    return header


def _draw_wrapped_text_block(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    max_width: int,
    font,
    fill: Tuple[int, int, int],
    line_gap: int = 8,
    max_lines: int = 3,
) -> int:
    line_h = int(getattr(font, "size", 22) * 1.25) + line_gap
    for line in _wrap_text(draw, text, font, max_width)[:max_lines]:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_h
    return y


def _draw_info_section(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    title: str,
    rows: List[Tuple[str, str]],
) -> int:
    title_font = _try_load_font(25, bold=True)
    label_font = _try_load_font(20, bold=True)
    body_font = _try_load_font(21)
    row_gap = 10
    measure_y = y + 64
    value_width = width - 180
    for label, value in rows:
        line_count = len(_wrap_text(draw, value, body_font, value_width))
        measure_y += max(32, line_count * 29) + row_gap
    box_h = measure_y - y + 18
    draw.rounded_rectangle((x, y, x + width, y + box_h), radius=22,
                           fill=(255, 255, 255, 218), outline=(126, 217, 202), width=2)
    draw.rounded_rectangle((x + 20, y + 18, x + 32, y + 48), radius=5, fill=(39, 185, 159))
    draw.text((x + 48, y + 16), title, font=title_font, fill=(13, 92, 91))
    cy = y + 64
    for label, value in rows:
        draw.text((x + 28, cy), label, font=label_font, fill=(10, 107, 104))
        wrapped = _wrap_text(draw, value, body_font, value_width)
        vy = cy
        for line in wrapped:
            draw.text((x + 150, vy), line, font=body_font, fill=(32, 73, 76))
            vy += 29
        cy = max(cy + 32, vy) + row_gap
    return y + box_h + 24


def _measure_info_section_height(
    draw: ImageDraw.ImageDraw,
    width: int,
    rows: List[Tuple[str, str]],
) -> int:
    body_font = _try_load_font(21)
    row_gap = 10
    measure_y = 64
    value_width = width - 180
    for _, value in rows:
        line_count = len(_wrap_text(draw, value, body_font, value_width))
        measure_y += max(32, line_count * 29) + row_gap
    return measure_y + 18 + 24


def render_download_status(
    album_id: str,
    output_desc: str,
    status: str = "start",
    tip: str = "",
    user_id: str = "",
) -> bytes:
    requester = f"用户 {user_id}" if user_id else f"JM{album_id}"
    status_map = {
        "start": {
            "title": "开始下载学习资料",
            "badge": "DOWNLOADING",
            "summary": f"已收到 {requester} 的学习请求，完成后会自动生成 {output_desc}。",
            "hint": "学习资料寻找和上传需要一点时间，请耐心等待噢~。",
            "accent": (39, 185, 159),
            "progress": 0.36,
        },
        "done": {
            "title": "学习资料下载完成",
            "badge": "COMPLETED",
            "summary": f"学习资料{album_id} 已处理完成，慢慢学习吧~。",
            "hint": "可以在当前会话或群文件中查看。",
            "accent": (34, 197, 94),
            "progress": 1.0,
        },
        "timeout": {
            "title": "上传任务已提交",
            "badge": "UPLOADING",
            "summary": f"学习资料{album_id} 已提交上传，学习资料较大时可能仍在后台发送。",
            "hint": "请稍后到群文件或当前会话中查看。",
            "accent": (54, 198, 214),
            "progress": 0.72,
        },
    }
    meta = status_map.get(status, status_map["start"])
    accent = meta["accent"]

    width, height = 980, 500
    img = Image.new("RGB", (width, height), (234, 255, 249))
    draw = ImageDraw.Draw(img)
    _draw_firefly_help_bg(draw, width, height)

    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((-90, -95, 330, 290), fill=(190, 255, 220, 96))
    glow_draw.ellipse((width - 330, -80, width + 120, 310), fill=(93, 206, 215, 72))
    glow_draw.ellipse((width - 260, height - 230, width + 120, height + 130), fill=(139, 230, 206, 58))
    img = Image.alpha_composite(img.convert("RGBA"), glow)
    draw = ImageDraw.Draw(img)

    title_font = _try_load_font(48, bold=True)
    body_font = _try_load_font(27)
    small_font = _try_load_font(21)
    badge_font = _try_load_font(18, bold=True)
    mono_font = _try_load_font(24, bold=True)

    card = (54, 50, width - 54, height - 50)
    x1, y1, x2, y2 = card
    draw.rounded_rectangle(
        card,
        radius=30,
        fill=(255, 255, 255, 210),
        outline=(236, 255, 249, 220),
        width=2,
    )
    draw.rounded_rectangle(
        (x1 + 14, y1 + 14, x2 - 14, y2 - 14),
        radius=24,
        outline=(121, 218, 204, 130),
        width=2,
    )
    badge_text_width = int(draw.textlength(meta["badge"], font=badge_font))
    badge_w = max(172, badge_text_width + 58)
    draw.rounded_rectangle(
        (x1 + 34, y1 + 30, x1 + 34 + badge_w, y1 + 64),
        radius=14,
        fill=(226, 255, 248, 230),
        outline=(126, 217, 202, 180),
        width=1,
    )
    draw.text((x1 + 58, y1 + 36), meta["badge"], font=badge_font, fill=(9, 107, 104))
    draw.text((x2 - 184, y1 + 36), "FIREFLY", font=badge_font, fill=(74, 154, 151))

    icon_box = (x1 + 42, y1 + 84, x1 + 164, y1 + 206)
    draw.rounded_rectangle(icon_box, radius=26, fill=(225, 255, 248, 225), outline=(126, 217, 202), width=2)
    symbol = _get_finish_symbol(108) if status == "done" else _get_download_symbol(108)
    if symbol:
        img.paste(symbol, (x1 + 49, y1 + 91), symbol)
    else:
        cx, cy = x1 + 103, y1 + 145
        draw.ellipse((cx - 24, cy - 24, cx + 24, cy + 24), fill=accent)
        draw.ellipse((cx - 9, cy - 9, cx + 9, cy + 9), fill=(248, 255, 252))

    text_x = x1 + 196
    draw.text((text_x, y1 + 92), meta["title"], font=title_font, fill=(18, 76, 79))
    draw.text((text_x, y1 + 154), f"ID:{album_id}", font=mono_font, fill=(13, 88, 89))

    content_x = x1 + 46
    content_y = y1 + 232
    max_text_width = x2 - content_x - 52
    lines = _wrap_text(draw, meta["summary"], body_font, max_text_width)
    for idx, line in enumerate(lines[:2]):
        draw.text((content_x, content_y + idx * 36), line, font=body_font, fill=(32, 73, 76))
    hint_y = content_y + max(1, min(2, len(lines))) * 36 + 12
    hint_lines = _wrap_text(draw, meta["hint"] + (tip if tip else ""), small_font, max_text_width)
    for idx, line in enumerate(hint_lines[:2]):
        draw.text((content_x, hint_y + idx * 30), line, font=small_font, fill=(80, 119, 123))

    bar_x1, bar_y1 = content_x, y2 - 56
    bar_x2, bar_y2 = x2 - 52, y2 - 34
    draw.rounded_rectangle((bar_x1, bar_y1, bar_x2, bar_y2), radius=10, fill=(219, 246, 241))
    fill_w = int((bar_x2 - bar_x1) * meta["progress"])
    _draw_gradient_roundrect(
        img,
        (bar_x1, bar_y1, bar_x1 + fill_w, bar_y2),
        10,
        accent,
        (139, 230, 206),
    )

    draw.rounded_rectangle((x2 - 156, bar_y1 - 48, x2 - 52, bar_y1 - 20),
                           radius=12, fill=(226, 255, 248), outline=(126, 217, 202), width=1)
    draw.text((x2 - 134, bar_y1 - 45), output_desc, font=badge_font, fill=(10, 107, 104))

    out = io.BytesIO()
    img.convert("RGB").save(out, format="PNG")
    return out.getvalue()


def render_search_result(
    keyword: str, albums: List[dict], sort_label: str, page: int
) -> bytes:
    width = 1120
    margin = 42
    gap = 18
    result_h = 138
    footer_h = 72
    list_h = max(result_h, len(albums) * result_h + max(0, len(albums) - 1) * gap)
    height = margin + 180 + 26 + 58 + 24 + list_h + gap + footer_h + margin

    img = _make_firefly_canvas(width, height)
    draw = ImageDraw.Draw(img)
    _draw_firefly_page_header(
        img,
        "JM 搜索结果",
        "流萤印象主题 · 搜索条目速览",
        "SEARCH",
    )
    draw = ImageDraw.Draw(img)

    badge_font = _try_load_font(18, bold=True)
    title_font = _try_load_font(27, bold=True)
    body_font = _try_load_font(21)
    small_font = _try_load_font(18)

    meta_y = margin + 180 + 26
    meta_x = margin + 24
    for text in (f"关键词：{keyword}", f"排序：{sort_label}", f"第 {page} 页", f"本页 {len(albums)} 条"):
        box = _draw_chip(draw, meta_x, meta_y, text, badge_font)
        meta_x = box[2] + 14

    y = meta_y + 58 + 24
    content_x = margin
    content_w = width - margin * 2
    if not albums:
        draw.rounded_rectangle((content_x, y, content_x + content_w, y + result_h), radius=24,
                               fill=(255, 255, 255, 218), outline=(126, 217, 202), width=2)
        draw.text((content_x + 34, y + 32), "没有匹配结果", font=title_font, fill=(13, 92, 91))
        draw.text((content_x + 34, y + 76), "可以尝试缩短关键词或改用编号搜索", font=body_font, fill=(80, 119, 123))
        y += result_h
    else:
        for idx, album in enumerate(albums, 1):
            global_index = (page - 1) * SEARCH_PAGE_SIZE + idx
            index_text = f"{global_index:02d}"
            index_w = max(66, int(draw.textlength(index_text, font=title_font)) + 30)
            box = (content_x, y, content_x + content_w, y + result_h)
            fill = (255, 255, 255, 222) if idx % 2 else (244, 255, 252, 226)
            draw.rounded_rectangle(box, radius=24, fill=fill, outline=(126, 217, 202), width=2)
            draw.rounded_rectangle((content_x + 24, y + 26, content_x + 24 + index_w, y + 88),
                                   radius=18, fill=(226, 255, 248), outline=(39, 185, 159), width=2)
            text_x = content_x + 24 + (index_w - int(draw.textlength(index_text, font=title_font))) // 2
            draw.text((text_x, y + 38), index_text, font=title_font, fill=(10, 107, 104))
            chip_x = content_x + 24 + index_w + 26
            id_box = _draw_chip(draw, chip_x, y + 24, f"#{album['id']}", small_font)
            author = str(album.get("author") or "未知")
            _draw_chip(draw, id_box[2] + 12, y + 24, f"作者：{author}", small_font)
            title = str(album.get("title") or "未命名")
            _draw_wrapped_text_block(
                draw, title, chip_x, y + 68, content_w - (chip_x - content_x) - 34,
                title_font, (32, 73, 76), line_gap=4, max_lines=2
            )
            y += result_h + gap

    footer_y = height - margin - footer_h
    draw.rounded_rectangle((margin + 18, footer_y, width - margin - 18, footer_y + footer_h),
                           radius=22, fill=(226, 255, 248), outline=(126, 217, 202), width=2)
    draw.rounded_rectangle((margin + 42, footer_y + 20, margin + 54, footer_y + 54),
                           radius=5, fill=(39, 185, 159))
    draw.text((margin + 72, footer_y + 18), "翻页：/下一页    返回：/上一页",
              font=body_font, fill=(24, 91, 92))
    draw.text((width - margin - 188, footer_y + 42), "FIREFLY · BAIZE",
              font=badge_font, fill=(74, 154, 151))

    out = io.BytesIO()
    img.convert("RGB").save(out, format="PNG")
    return out.getvalue()


def render_info(info: dict) -> bytes:
    tags = info["tags"][:18] if info["tags"] else []
    actors = " / ".join(info["actors"][:10]) if info["actors"] else "无"
    works = " / ".join(info["works"][:10]) if info["works"] else "无"
    authors = " / ".join(info["authors"]) if info["authors"] else info["author"]
    description = info["description"] or "无简介"
    chapters = info["chapters"][:12] if info["chapters"] else []

    measure = Image.new("RGB", (1120, 200), (255, 255, 255))
    measure_draw = ImageDraw.Draw(measure)
    body_font = _try_load_font(21)
    tag_font = _try_load_font(18, bold=True)
    desc_lines = _wrap_text(measure_draw, description, body_font, 938)
    tag_rows = 1
    if tags:
        row_w = 0
        tag_rows = 1
        for tag in tags:
            chip_w = int(measure_draw.textlength(tag, font=tag_font)) + 32
            if row_w and row_w + chip_w + 10 > 938:
                tag_rows += 1
                row_w = 0
            row_w += chip_w + 10
    basic_rows = [
        ("车号", f"JM{info['id']}"),
        ("链接", info["link"] or "无"),
        ("发布", str(info["pub_date"] or "未知")),
        ("更新", str(info["update_date"] or "未知")),
        ("页数", str(info["page_count"] or "未知")),
        ("观看", str(info["views"] or "未知")),
        ("点赞", str(info["likes"] or "未知")),
        ("评论", str(info["comment_count"] or "未知")),
    ]
    relation_rows = [("人物", actors), ("作品", works)]
    chapter_rows: List[Tuple[str, str]] = []
    if chapters:
        for idx, chapter in enumerate(chapters, 1):
            chapter_id = chapter.get("id", "")
            chapter_title = chapter.get("title", "未命名章节")
            value = f"{chapter_title} ({chapter_id})" if chapter_id else chapter_title
            chapter_rows.append((f"{idx:02d}", value))
        if len(info["chapters"]) > 12:
            chapter_rows.append(("...", f"还有 {len(info['chapters']) - 12} 章未展示"))
    else:
        chapter_rows.append(("-", "无章节列表"))
    desc_rows = [("简介", "\n".join(desc_lines))]

    width = 1120
    margin = 42
    content_w = width - margin * 2
    tag_box_h = 98 + tag_rows * 42
    height = (
        margin + 180 + 26 + 170 + 24
        + _measure_info_section_height(measure_draw, content_w, basic_rows)
        + tag_box_h + 24
        + _measure_info_section_height(measure_draw, content_w, relation_rows)
        + _measure_info_section_height(measure_draw, content_w, chapter_rows)
        + _measure_info_section_height(measure_draw, content_w, desc_rows)
        + margin
    )

    img = _make_firefly_canvas(width, height)
    draw = ImageDraw.Draw(img)
    _draw_firefly_page_header(
        img,
        "JM 本子详情",
        "流萤印象主题 · 条目信息面板",
        "DETAIL",
        _get_download_symbol(108),
    )
    draw = ImageDraw.Draw(img)

    title_font = _try_load_font(38, bold=True)
    body_font = _try_load_font(21)
    small_font = _try_load_font(18)
    badge_font = _try_load_font(18, bold=True)
    y = margin + 180 + 26

    title_box = (margin, y, width - margin, y + 170)
    draw.rounded_rectangle(title_box, radius=26, fill=(255, 255, 255, 222),
                           outline=(126, 217, 202), width=2)
    draw.rounded_rectangle((margin + 28, y + 28, margin + 42, y + 72),
                           radius=6, fill=(39, 185, 159))
    title_lines = _wrap_text(draw, str(info["title"]), title_font, content_w - 110)
    for idx, line in enumerate(title_lines[:2]):
        draw.text((margin + 62, y + 20 + idx * 44), line, font=title_font, fill=(18, 76, 79))
    chip_y = y + 102
    chip_x = margin + 62
    for text in (f"JM{info['id']}", f"作者：{authors}", f"章节：{info['chapter_count']}"):
        box = _draw_chip(draw, chip_x, chip_y, text, badge_font)
        chip_x = box[2] + 12
    y += 170 + 24

    y = _draw_info_section(draw, margin, y, content_w, "基础信息", basic_rows)

    draw.rounded_rectangle((margin, y, width - margin, y + tag_box_h), radius=22,
                           fill=(255, 255, 255, 218), outline=(126, 217, 202), width=2)
    draw.rounded_rectangle((margin + 20, y + 18, margin + 32, y + 48), radius=5, fill=(39, 185, 159))
    draw.text((margin + 48, y + 16), "标签信息", font=_try_load_font(25, bold=True), fill=(13, 92, 91))
    tag_x, tag_y = margin + 28, y + 66
    if tags:
        for tag in tags:
            chip_w = int(draw.textlength(tag, font=tag_font)) + 32
            if tag_x + chip_w > width - margin - 28:
                tag_x = margin + 28
                tag_y += 42
            box = _draw_chip(draw, tag_x, tag_y, tag, tag_font)
            tag_x = box[2] + 10
    else:
        draw.text((tag_x, tag_y + 5), "无", font=body_font, fill=(80, 119, 123))
    y += tag_box_h + 24

    y = _draw_info_section(draw, margin, y, content_w, "关联信息", relation_rows)
    y = _draw_info_section(draw, margin, y, content_w, f"章节（{info['chapter_count']}）", chapter_rows)

    _draw_info_section(draw, margin, y, content_w, "简介", desc_rows)

    out = io.BytesIO()
    img.convert("RGB").save(out, format="PNG")
    return out.getvalue()


def render_help() -> bytes:
    width = 1120
    margin = 34
    gap = 28
    header_h = 230
    card_w = (width - margin * 2 - gap) // 2
    card_h = 430
    wide_h = 340
    footer_h = 82
    height = margin + header_h + gap + card_h + gap + wide_h + gap + footer_h + margin

    img = Image.new("RGB", (width, height), (235, 255, 249))
    draw = ImageDraw.Draw(img)
    _draw_firefly_help_bg(draw, width, height)

    title_font = _try_load_font(50, bold=True)
    subtitle_font = _try_load_font(24)
    badge_font = _try_load_font(18, bold=True)
    body_font = _try_load_font(22)
    footer_font = _try_load_font(20)

    header = (margin, margin, width - margin, margin + header_h)
    _draw_gradient_roundrect(img, header, 30, (16, 181, 164), (123, 229, 209),
                             outline=(236, 255, 249), width=3)
    draw = ImageDraw.Draw(img)
    hx1, hy1, hx2, hy2 = header
    draw.rounded_rectangle((hx1 + 14, hy1 + 14, hx2 - 14, hy2 - 14),
                           radius=24, outline=(14, 127, 124), width=2)
    draw.text((hx1 + 38, hy1 + 36), "JM PLUGIN HELP", font=title_font, fill=(248, 255, 252))
    draw.text((hx1 + 40, hy1 + 98), "流萤印象主题 · 搜索 / 详情 / 下载指令速览",
              font=subtitle_font, fill=(221, 255, 248))
    draw.line((hx1 + 40, hy2 - 54, hx2 - 250, hy2 - 54), fill=(8, 121, 118), width=3)

    chip_x = hx1 + 40
    for label in ("SEARCH", "DETAIL", "DOWNLOAD"):
        chip_w = max(100, int(draw.textlength(label, font=badge_font)) + 36)
        draw.rounded_rectangle((chip_x, hy2 - 42, chip_x + chip_w, hy2 - 14),
                               radius=12, fill=(226, 255, 248), outline=(9, 127, 124), width=1)
        draw.text((chip_x + 18, hy2 - 38), label, font=badge_font, fill=(10, 107, 104))
        chip_x += chip_w + 20

    symbol_panel = (hx2 - 184, hy1 + 34, hx2 - 36, hy1 + 182)
    draw.rounded_rectangle(symbol_panel, radius=30, fill=(226, 255, 248), outline=(229, 255, 249), width=2)
    symbol = _get_help_symbol(116)
    if symbol:
        img.paste(symbol, (hx2 - 168, hy1 + 50), symbol)
    else:
        draw.text((hx2 - 162, hy1 + 82), "FIREFLY", font=subtitle_font, fill=(10, 107, 104))
    draw.rounded_rectangle((hx2 - 172, hy1 + 164, hx2 - 48, hy1 + 192),
                           radius=12, fill=(12, 142, 132), outline=(229, 255, 249), width=1)
    draw.text((hx2 - 154, hy1 + 168), "SAM MODE", font=badge_font, fill=(232, 255, 249))
    for cx, cy, r in ((hx2 - 186, hy1 + 72, 5), (hx2 - 42, hy1 + 62, 7), (hx2 - 72, hy1 + 188, 4)):
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(248, 255, 252))
    draw.arc((hx2 - 210, hy1 + 28, hx2 - 18, hy1 + 218), start=210, end=330, fill=(229, 255, 249), width=2)

    cards_y = margin + header_h + gap
    _draw_firefly_help_card(
        draw,
        (margin, cards_y, margin + card_w, cards_y + card_h),
        "搜索与翻页",
        [
            {"cmd": "/jm搜索", "desc": "按关键词搜索并返回结果卡"},
            {"cmd": "/jm搜索 最新 关键词", "desc": "指定排序后搜索，适合快速找新条目"},
            {"cmd": "/下一页", "desc": "查看最近一次搜索的下一页"},
            {"cmd": "/上一页", "desc": "返回最近一次搜索的上一页"},
            {"cmd": "排序词", "desc": "默认 / 相关 / 最新 / 总排行 / 观看 / 点赞"},
        ],
        (20, 186, 164),
    )
    _draw_firefly_help_card(
        draw,
        (margin + card_w + gap, cards_y, width - margin, cards_y + card_h),
        "详情与下载",
        [
            {"cmd": "/jm详情 ID", "desc": "查看条目标题、作者、标签、章节等信息"},
            {"cmd": "/jm下载 ID", "desc": "下载指定条目并上传为文件"},
            {"cmd": "示例", "desc": "/jm详情 350234  或  /jm下载 350234"},
            {"cmd": "输出", "desc": "按配置生成 PDF / ZIP，PDF 可启用加密"},
            {"cmd": "提示", "desc": "ID 可直接使用搜索结果里的编号"},
        ],
        (58, 201, 214),
    )

    wide_y = cards_y + card_h + gap
    _draw_firefly_help_card(
        draw,
        (margin, wide_y, width - margin, wide_y + wide_h),
        "使用提示",
        [
            {"cmd": "/jm帮助", "desc": "打开这张单独帮助图"},
            {"cmd": "会话记录", "desc": "搜索翻页按群聊 / 私聊分别保存，互不影响"},
            {"cmd": "关键词", "desc": "太长或太宽泛时可以缩短关键词，或追加排序词"},
            {"cmd": "下载任务", "desc": "文件生成耗时取决于条目页数和网络状态"},
        ],
        (92, 190, 232),
    )

    footer_y = wide_y + wide_h + gap
    draw.rounded_rectangle((margin + 18, footer_y, width - margin - 18, footer_y + footer_h),
                           radius=24, fill=(226, 255, 248), outline=(126, 217, 202), width=2)
    draw.rounded_rectangle((margin + 42, footer_y + 22, margin + 54, footer_y + 60),
                           radius=5, fill=(20, 186, 164))
    draw.text((margin + 72, footer_y + 18),
              "提示：搜索记录按会话保存，群聊和私聊互不影响。翻页无需重复输入关键词。",
              font=footer_font, fill=(24, 91, 92))
    draw.text((width - margin - 188, footer_y + 46), "FIREFLY · BAIZE",
              font=badge_font, fill=(74, 154, 151))

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()
