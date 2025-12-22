import os
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.enum.dml import MSO_THEME_COLOR
from pptx.dml.color import RGBColor

# SVG -> PNG conversion (Windows-friendly)
# Attempted at runtime to avoid hard dependency on system Cairo

BASE = Path(__file__).resolve().parents[1]
DOCS = BASE / "docs"
OUT = DOCS / "Harmonics_Presentation.pptx"
PNG_DIR = DOCS / "png"

SVG_FILES = {
    "usecase": DOCS / "usecase_diagram.svg",
    "seq_practice": DOCS / "sequence_diagram_practice.svg",
    "seq_msg": DOCS / "sequence_diagram_messaging.svg",
    "class": DOCS / "class_diagram.svg",
}

TEXT_THEME_COLOR = RGBColor(34, 34, 34)


def ensure_pngs():
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    png_map = {}
    for key, svg_path in SVG_FILES.items():
        if not svg_path.exists():
            print(f"[WARN] Missing SVG: {svg_path}")
            continue
        png_path = PNG_DIR / f"{key}.png"
        try:
            from svglib.svglib import svg2rlg
            from reportlab.graphics import renderPM
            drawing = svg2rlg(str(svg_path))
            renderPM.drawToFile(drawing, str(png_path), fmt="PNG")
            png_map[key] = png_path
            print(f"[OK] Converted {svg_path.name} -> {png_path.name}")
        except Exception as e:
            print(f"[WARN] PNG conversion failed for {svg_path.name}: {e}")
            print("      Slide will include a placeholder instead.")
    return png_map


def add_title_slide(prs: Presentation, title: str, subtitle: str):
    slide = prs.slides.add_slide(prs.slide_layouts[0])  # Title
    title_shape = slide.shapes.title
    subtitle_shape = slide.placeholders[1]
    title_shape.text = title
    subtitle_shape.text = subtitle
    title_shape.text_frame.paragraphs[0].font.size = Pt(36)
    subtitle_shape.text_frame.paragraphs[0].font.size = Pt(18)


def add_bullets_slide(prs: Presentation, title: str, bullets: list[str]):
    slide = prs.slides.add_slide(prs.slide_layouts[1])  # Title and Content
    slide.shapes.title.text = title
    tf = slide.placeholders[1].text_frame
    tf.clear()
    for i, line in enumerate(bullets):
        p = tf.add_paragraph() if i > 0 else tf.paragraphs[0]
        p.text = line
        p.level = 0
        p.font.size = Pt(18)
        p.font.color.rgb = TEXT_THEME_COLOR


def add_image_slide(prs: Presentation, title: str, image_path: Path):
    slide = prs.slides.add_slide(prs.slide_layouts[5])  # Title Only
    slide.shapes.title.text = title
    # Center the image
    left = Inches(0.5)
    top = Inches(1.5)
    height = Inches(5.5)
    if image_path and image_path.exists():
        slide.shapes.add_picture(str(image_path), left, top, height=height)
    else:
        add_bullets_slide(prs, title + " (이미지 누락)", [str(image_path)])


def build_presentation():
    pngs = ensure_pngs()
    prs = Presentation()

    # 1. 표지
    add_title_slide(
        prs,
        "Harmonics v2: 공학적 원리 적용 사례",
        "거래 · SNS · 메시지 · AI 연습 추천 · 진행도 · 일지"
    )

    # 2. 아키텍처 요약
    add_bullets_slide(
        prs,
        "아키텍처",
        [
            "클라이언트: Jinja2 템플릿 + JavaScript(AJAX)",
            "서버: Flask 레이어드(MVC 개념) + Blueprint 분리 지향",
            "데이터: SQLAlchemy + Alembic(마이그레이션)",
            "외부: Google Gemini(추천), YouTube Data API(영상)",
            "인증/보안: Flask-Login, .env 환경변수"
        ],
    )

    # 3. 유스케이스 스냅샷
    add_image_slide(prs, "유스케이스: 거래/SNS/메시지/연습/인증", pngs.get("usecase"))

    # 4. 적용 이론/패턴
    add_bullets_slide(
        prs,
        "적용 이론/패턴",
        [
            "요구사항 공학: 기능/비기능 명세, 우선순위·추적",
            "아키텍처: Layered + MVC, 도메인 모듈화",
            "State: 연습 진행 상태(미시작/연습중/완료/일시중지)",
            "Strategy: YouTube 한/영 폴백, 특정 곡 프롬프트 분기",
            "Facade: Gemini/YouTube API 캡슐화",
            "Template: base.html로 UI 일관성"
        ],
    )

    # 5. 효과(바뀐 점/차이)
    add_bullets_slide(
        prs,
        "효과: v1 → v2",
        [
            "유지보수성↑: 모듈 경계로 변경 영향↓, 중복 제거",
            "확장성↑: AI 연습 추천 추가 시 기존 영향 최소",
            "신뢰성↑: 요구 기반 검증 + 회귀 체크리스트로 버그 조기 해결",
            "사용자 가치↑: 개인화 추천 + 진행도/일지로 동기부여"
        ],
    )

    # 6. 핵심 흐름(정적)
    add_image_slide(prs, "시퀀스: AI 연습 추천 생성·저장·업데이트", pngs.get("seq_practice"))

    # 7. 결론/향후 계획
    add_bullets_slide(
        prs,
        "결론 및 향후",
        [
            "공학 원리 적용으로 품질·확장·가치 동시 향상",
            "라우트 분리 심화, 자동화 테스트/보안 강화",
            "성능/캐싱, API 문서화, Docker/배포 파이프라인"
        ],
    )

    prs.save(str(OUT))
    print(f"[DONE] Saved presentation: {OUT}")


if __name__ == "__main__":
    build_presentation()
