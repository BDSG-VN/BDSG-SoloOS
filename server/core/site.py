"""Original, declarative Vietnamese website templates. No executable theme code."""

from pydantic import BaseModel, ConfigDict, Field

THEMES = {
    "personal": (
        "Cá nhân & chuyên gia",
        "Chia sẻ kinh nghiệm. Kết nối cơ hội.",
        "#185c41",
        "#fafbf8",
        ["Giới thiệu", "Dự án nổi bật", "Bài viết & góc nhìn"],
    ),
    "consulting": (
        "Tư vấn & dịch vụ",
        "Đồng hành từ ý tưởng đến kết quả.",
        "#204d91",
        "#f4f7fc",
        ["Giải pháp của chúng tôi", "Quy trình hợp tác", "Đặt lịch tư vấn"],
    ),
    "retail": (
        "Cửa hàng & thương hiệu",
        "Sản phẩm được chọn bằng sự tận tâm.",
        "#a44723",
        "#fff9f1",
        ["Bộ sưu tập", "Câu chuyện thương hiệu", "Hướng dẫn mua hàng"],
    ),
    "restaurant": (
        "Ẩm thực & cà phê",
        "Một điểm hẹn. Nhiều câu chuyện.",
        "#754523",
        "#fff8ed",
        ["Thực đơn", "Không gian", "Đặt bàn & liên hệ"],
    ),
    "education": (
        "Giáo dục & đào tạo",
        "Học điều mới. Làm điều khác biệt.",
        "#5140a0",
        "#f8f6ff",
        ["Chương trình học", "Phương pháp đào tạo", "Đăng ký tư vấn"],
    ),
    "property": (
        "Bất động sản & kiến trúc",
        "Không gian dành cho tương lai.",
        "#344f60",
        "#f4f7f7",
        ["Dự án", "Dịch vụ", "Kết nối chuyên viên"],
    ),
    "travel": (
        "Du lịch & lưu trú",
        "Đi để cảm nhận. Ở để tận hưởng.",
        "#006d77",
        "#f2fbfa",
        ["Trải nghiệm", "Điểm đến", "Lên lịch chuyến đi"],
    ),
    "wellness": (
        "Sức khỏe & chăm sóc",
        "Chăm sóc từ những điều gần gũi.",
        "#446b45",
        "#f7faf2",
        ["Dịch vụ chăm sóc", "Đội ngũ", "Đặt lịch"],
    ),
}


class SiteSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(default="BDSG SoloOS", min_length=1, max_length=120)
    tagline: str = Field(default="Không gian chia sẻ và kết nối.", max_length=300)
    theme: str = "personal"
    registration: bool = False


def settings(cms):
    with cms.db() as db:
        row = db.execute("SELECT value FROM settings WHERE key='site'").fetchone()
    return SiteSettings.model_validate_json(row["value"]) if row else SiteSettings()


def save_settings(cms, body):
    if body.theme not in THEMES:
        raise ValueError("Unknown theme")
    with cms.db() as db:
        db.execute("INSERT OR REPLACE INTO settings VALUES('site',?)", (body.model_dump_json(),))
    return body


def template(theme, title):
    if theme not in THEMES:
        raise ValueError("Unknown theme")
    label, headline, _, _, sections = THEMES[theme]
    return {
        "kind": "page",
        "title": title,
        "excerpt": headline,
        "blocks": [
            {"type": "hero", "text": headline, "detail": f"{title} · {label}"},
            *[
                block
                for section in sections
                for block in (
                    {"type": "heading", "text": section},
                    {
                        "type": "paragraph",
                        "text": "Thay nội dung này bằng thông tin đã kiểm chứng của bạn trước khi xuất bản.",
                    },
                )
            ],
            {"type": "button", "text": "Đọc bài viết mới", "href": "/news"},
        ],
    }
