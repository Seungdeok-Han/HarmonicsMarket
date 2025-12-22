import os
from PIL import Image, ImageDraw, ImageFont


def load_font(size: int) -> ImageFont.ImageFont:
    """Load a common sans font; fall back to default."""
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_box(draw: ImageDraw.ImageDraw, palette: dict, x0: int, y0: int, x1: int, y1: int, fill: str, outline: str, text: str, font: ImageFont.ImageFont):
    draw.rounded_rectangle((x0, y0, x1, y1), radius=12, fill=fill, outline=outline, width=3)
    tw, th = text_size(draw, text, font=font)
    tx = x0 + (x1 - x0 - tw) / 2
    ty = y0 + (y1 - y0 - th) / 2
    draw.text((tx, ty), text, fill=palette["text"], font=font)


def arrow(draw: ImageDraw.ImageDraw, from_xy, to_xy, color="#444", width=4, head=14):
    draw.line((from_xy[0], from_xy[1], to_xy[0], to_xy[1]), fill=color, width=width)
    dx = to_xy[0] - from_xy[0]
    dy = to_xy[1] - from_xy[1]
    length = (dx ** 2 + dy ** 2) ** 0.5 or 1
    ux, uy = dx / length, dy / length
    perp = (-uy, ux)
    p1 = (to_xy[0] - ux * head + perp[0] * head * 0.6, to_xy[1] - uy * head + perp[1] * head * 0.6)
    p2 = (to_xy[0] - ux * head - perp[0] * head * 0.6, to_xy[1] - uy * head - perp[1] * head * 0.6)
    draw.polygon([to_xy, p1, p2], fill=color)


def midpoint(rect):
    x0, y0, x1, y1 = rect
    return ((x0 + x1) / 2, (y0 + y1) / 2)


def main():
    os.makedirs("app/static/diagrams", exist_ok=True)

    width, height = 1400, 950
    img = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(img)

    font_title = load_font(36)
    font_label = load_font(24)
    font_small = load_font(18)

    palette = {
        "client": "#f7c948",
        "presentation": "#6fa8dc",
        "view": "#c9daf8",
        "controller": "#9fc5e8",
        "model": "#9ad6cb",
        "service": "#ffd966",
        "data": "#d9ead3",
        "storage": "#b6d7a8",
        "border": "#3d3d3d",
        "text": "#1f1f1f",
    }

    center_x = width // 2
    draw.text((center_x - 230, 20), "Layered Architecture + MVC", fill=palette["text"], font=font_title)

    client = (520, 80, 880, 150)
    presentation = (150, 170, 1250, 360)
    view = (200, 210, 530, 320)
    controller = (580, 210, 910, 320)
    model = (960, 210, 1220, 320)
    service = (200, 410, 1200, 520)
    data_access = (250, 570, 1150, 680)
    storage = (320, 740, 1080, 860)

    arrow(draw, midpoint(client), (midpoint(presentation)[0], presentation[1] - 10))

    draw_box(draw, palette, *presentation, fill=palette["presentation"], outline=palette["border"], text="Presentation Layer (MVC)", font=font_label)
    draw_box(draw, palette, *view, fill=palette["view"], outline=palette["border"], text="View (Jinja templates)", font=font_small)
    draw_box(draw, palette, *controller, fill=palette["controller"], outline=palette["border"], text="Controller (Flask routes / Socket.IO)", font=font_small)
    draw_box(draw, palette, *model, fill=palette["model"], outline=palette["border"], text="Model (SQLAlchemy)", font=font_small)

    draw_box(draw, palette, *client, fill=palette["client"], outline=palette["border"], text="Client", font=font_label)
    draw_box(draw, palette, *service, fill=palette["service"], outline=palette["border"], text="Service / Domain", font=font_label)
    draw_box(draw, palette, *data_access, fill=palette["data"], outline=palette["border"], text="Data Access / Repository", font=font_label)
    draw_box(draw, palette, *storage, fill=palette["storage"], outline=palette["border"], text="Database / External APIs", font=font_label)

    arrow(draw, midpoint(presentation), (midpoint(service)[0], service[1] - 10))
    arrow(draw, midpoint(service), (midpoint(data_access)[0], data_access[1] - 10))
    arrow(draw, midpoint(data_access), (midpoint(storage)[0], storage[1] - 10))

    arrow(draw, (midpoint(service)[0], service[3] + 10), (midpoint(presentation)[0], presentation[3] + 40), color="#8c8c8c", width=3, head=10)
    arrow(draw, (midpoint(data_access)[0], data_access[3] + 10), (midpoint(service)[0], service[3] + 40), color="#8c8c8c", width=3, head=10)
    arrow(draw, (midpoint(storage)[0], storage[3] + 10), (midpoint(data_access)[0], data_access[3] + 40), color="#8c8c8c", width=3, head=10)

    layer_notes = [
        (presentation, "Presentation Layer with MVC"),
        (service, "Service / Domain (business rules, validation)"),
        (data_access, "Data Access (repositories, ORM queries)"),
        (storage, "Database / External APIs"),
    ]
    for rect, text in layer_notes:
        draw.text((rect[0] + 10, rect[1] - 26), text, fill="#555", font=font_small)

    draw.text((client[0], client[3] + 10), "Client (browser / mobile)", fill="#555", font=font_small)
    draw.text((presentation[0] + 15, presentation[3] + 8), "Controller orchestrates flow, updates Model; View renders using Model; Socket.IO hooks live updates.", fill="#555", font=font_small)
    draw.text((data_access[0] + 15, data_access[3] + 8), "ORM / repository mediates persistence; isolates SQL/driver details.", fill="#555", font=font_small)
    draw.text((storage[0] + 15, storage[3] + 8), "RDBMS, caches, file/object storage, third-party APIs.", fill="#555", font=font_small)

    output_path = "app/static/diagrams/layered_mvc.png"
    img.save(output_path)
    print(f"saved {output_path}")


if __name__ == "__main__":
    main()
