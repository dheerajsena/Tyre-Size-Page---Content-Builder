import re
import io
import json
from typing import List, Tuple
import streamlit as st

# Optional: for .docx export
from docx import Document
from docx.shared import Pt

APP_TITLE = "Bob Jane T-Marts Tyre Size Page Generator"

# ---------- Utils ----------
def sanitize(text: str) -> str:
    if not text:
        return ""
    return text.replace("—", "-").replace("–", "-")

def parse_tyre_size(raw: str) -> Tuple[str, str, str]:
    """
    Accepts formats like:
    - 225 45 19
    - 225/45R19
    - 225/45 19
    - 225-45-19  (just in case)
    Returns (width, aspect, rim) as strings or ("","","") if invalid.
    """
    if not raw:
        return "", "", ""
    s = raw.upper().strip()
    s = re.sub(r"[^\dR/ ]", " ", s)             # keep digits, R, slash, space
    s = re.sub(r"\s+", " ", s).strip()

    # Try canonical pattern first: 225/45R19
    m = re.match(r"^(\d{3})\s*/\s*(\d{2})\s*R?\s*(\d{2})$", s)
    if m:
        return m.group(1), m.group(2), m.group(3)

    # Fallback: 225 45 19 (spaces)
    m = re.match(r"^(\d{3})\s+(\d{2})\s+(\d{2})$", s)
    if m:
        return m.group(1), m.group(2), m.group(3)

    # Fallback: 225/45 19 (missing R)
    m = re.match(r"^(\d{3})\s*/\s*(\d{2})\s+(\d{2})$", s)
    if m:
        return m.group(1), m.group(2), m.group(3)

    # Fallback: 225-45-19
    m = re.match(r"^(\d{3})-(\d{2})-(\d{2})$", s)
    if m:
        return m.group(1), m.group(2), m.group(3)

    return "", "", ""

def canonical_size(width: str, aspect: str, rim: str) -> str:
    if not (width and aspect and rim):
        return ""
    return f"{width}/{aspect}R{rim}"

def classify_segment(width: int, aspect: int, rim: int) -> str:
    """
    Heuristics with sensible defaults:
    - Performance: low profile (aspect <= 45) and rim >= 18 OR width >= 235 and aspect <= 40
    - 4x4: very wide (width >= 265) or aspect >= 60 with rim >= 18
    - SUV: width >= 235 and aspect >= 50
    - Passenger: default
    """
    if (aspect <= 45 and rim >= 18) or (width >= 235 and aspect <= 40):
        return "performance"
    if width >= 265 or (aspect >= 60 and rim >= 18):
        return "4x4"
    if width >= 235 and aspect >= 50:
        return "suv"
    return "passenger"

def micro_proof_point(segment: str, aspect: int) -> str:
    if segment == "performance":
        return "Sharper turn-in on winding roads"
    if segment == "4x4":
        return "Tow-friendly stability for larger SUVs and 4x4s"
    if segment == "suv":
        return "Touring comfort for long highway runs with family and cargo"
    # passenger default
    return "Sure-footed braking for urban stop-start traffic" if aspect < 60 else "Balanced wet braking for sudden showers"

def other_popular_sizes(width: int, aspect: int, rim: int, segment: str) -> List[str]:
    """
    Generate 4–5 sensible alternates near the input size.
    We keep everything realistic-looking without claiming specific fitment.
    """
    suggestions = set()

    # Helper to constrain typical tyre ranges
    def clamp_w(w): return max(155, min(w, 345))
    def clamp_a(a): return max(30, min(a, 80))
    def clamp_r(r): return max(13, min(r, 22))

    # Nearby tweaks
    candidates = [
        (clamp_w(width+10), aspect, rim),
        (clamp_w(width-10), aspect, rim),
        (width, clamp_a(aspect+5), rim),
        (width, clamp_a(aspect-5), rim),
        (width, aspect, clamp_r(rim+1)),
        (width, aspect, clamp_r(rim-1)),
    ]

    # Segment-flavoured tweaks
    if segment in ("4x4", "suv"):
        candidates += [
            (clamp_w(width+20), clamp_a(aspect+5), rim),
            (clamp_w(width+10), aspect, clamp_r(rim+1)),
        ]
    elif segment == "performance":
        candidates += [
            (clamp_w(width+10), clamp_a(aspect-5), rim),
            (width, clamp_a(aspect-5), clamp_r(rim+1)),
        ]

    # Build canonical strings
    for w,a,r in candidates:
        if (w,a,r) != (width,aspect,rim):
            suggestions.add(f"{w}/{a}R{r}")

    # Return 5 max
    return list(suggestions)[:5]

def limit_chars(s: str, max_len: int) -> str:
    s = sanitize(s.strip())
    return s if len(s) <= max_len else s[:max_len-1].rstrip() + "…"

def word_count(s: str) -> int:
    return len(s.strip().split())

# ---------- Content Generators ----------
def target_keywords(size: str) -> List[str]:
    return [
        f"{size} tyres",
        f"buy {size} tyres online",
        f"best price {size} Australia",
        "Bob Jane T-Marts tyres"
    ]

def compose_intro(size: str, segment: str) -> str:
    if segment == "performance":
        txt = (
            f"Engineered for performance vehicles, {size} tyres deliver sharp handling, cornering grip and responsive braking. "
            f"The lower profile helps keep steering precise while modern compounds support stability at speed. "
            f"Choose {size} for confident control on Australian roads in wet and dry conditions."
        )
    elif segment == "4x4":
        txt = (
            f"Designed for SUVs and 4x4s, {size} tyres provide strength, stability and traction on highways and light off-road terrain. "
            f"Robust constructions and versatile tread patterns deliver comfort and control across long distances. "
            f"Choose {size} for dependable performance in varied Australian conditions."
        )
    elif segment == "suv":
        txt = (
            f"Built for SUVs and crossovers, {size} tyres offer stable handling, sure grip and a comfortable ride. "
            f"Durable, touring-focused tread patterns make daily errands and road trips smoother and quieter. "
            f"Choose {size} for reliable performance across Australian roads and weather."
        )
    else:
        txt = (
            f"Popular with hatchbacks and sedans, {size} tyres balance safety, comfort and fuel efficiency for everyday driving. "
            f"Tuned tread patterns help reduce noise while maintaining confident braking in wet and dry conditions. "
            f"Choose {size} for long-lasting performance on Australian roads."
        )
    return sanitize(txt)

def compose_buy(size: str) -> str:
    txt = (
        f"Buying {size} tyres is quick and simple with Bob Jane T-Marts. Use our online tyre finder to select the right fit in minutes. "
        f"Pricing is transparent and all-inclusive, covering professional fitting, balancing and the responsible disposal of your old tyres. "
        f"With our Best Tyre Price Guarantee, Tyre Satisfaction Guarantee and nationwide stores, you will enjoy great value, easy booking and expert service from checkout to fitment."
    )
    return sanitize(txt)

def bullets_for(segment: str, proof: str) -> List[str]:
    if segment == "performance":
        base = [
            "Precise steering and cornering grip",
            "Strong, predictable braking",
            "Sporty road feel with comfort in mind",
        ]
    elif segment == "4x4":
        base = [
            "Confident highway and light off-road grip",
            "Comfortable, stable ride",
            "Durable construction for long life",
        ]
    elif segment == "suv":
        base = [
            "Stable handling for larger SUVs",
            "Quiet, comfortable touring",
            "Reliable wet and dry performance",
        ]
    else:
        base = [
            "Comfortable, quiet everyday ride",
            "Confident wet and dry traction",
            "Fuel efficient, long wearing designs",
        ]
    out = [sanitize(proof)] + base
    return out[:4]

def make_meta_title(size: str) -> str:
    return limit_chars(f"{size} Tyres | Best Price Online | Bob Jane T-Marts", 60)

def make_meta_description(size: str) -> str:
    return limit_chars(
        f"Shop {size} tyres online at Bob Jane T-Marts. Best Price Guarantee, fitting and balancing included, nationwide stores. Book online today.",
        160,
    )

def render_markdown(size: str, intro: str, buy: str, bullets: List[str], other_sizes: List[str]) -> str:
    kw = ", ".join(target_keywords(size))
    content = f"""Target Keywords: {kw}

Meta Title: {make_meta_title(size)}

Meta Description: {make_meta_description(size)}

H1: {size} Tyres

Intro (50–70 words)
{intro}

H2: Buy {size} Tyres Online
{buy}

H2: Why Choose {size} Tyres?
- {bullets[0]}
- {bullets[1]}
- {bullets[2]}
- {bullets[3]}

H2: Other Popular Sizes
• {" • ".join(other_sizes)}

CTA:
Shop {size} tyres today at Bob Jane T-Marts."""
    return sanitize(content)

# ---------- Schema (optional placeholders) ----------
def product_schema_jsonld(size: str) -> dict:
    width, aspect, rim = size.split("/")[0], size.split("/")[1][:2], size.split("R")[1]
    return {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": f"{size} Tyres",
        "category": "Tyres",
        "brand": {"@type": "Brand", "name": "Various"},
        "description": f"Shop {size} tyres online at Bob Jane T-Marts. Best Price Guarantee with fitting and balancing included. Nationwide stores and easy booking.",
        "additionalProperty": [
            {"@type": "PropertyValue", "name": "Width", "value": width},
            {"@type": "PropertyValue", "name": "Aspect Ratio", "value": aspect},
            {"@type": "PropertyValue", "name": "Rim Diameter", "value": rim},
        ],
        # Add price/offerCount later if you have live data
        "offers": {
            "@type": "AggregateOffer",
            "priceCurrency": "AUD",
            "lowPrice": "[LOWEST PRICE]",
            "highPrice": "[HIGHEST PRICE]",
            "offerCount": "[NUMBER OF LISTINGS]",
            "availability": "https://schema.org/InStock",
            "url": "[CANONICAL URL FOR THIS SIZE PAGE]",
        },
    }

def faq_schema_jsonld(size: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": f"What vehicles use {size} tyres?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f"Many hatchbacks, sedans and SUVs use {size} tyres. Use our online tyre finder to confirm fitment for your vehicle and book fitting at a nearby store."
                },
            },
            {
                "@type": "Question",
                "name": f"Can I buy {size} tyres online and fit in store?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f"Yes. Order {size} tyres online, choose a store and a time that suits you, and our team will fit and balance your new tyres with disposal included."
                },
            },
            {
                "@type": "Question",
                "name": "Do prices include fitting and balancing?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "Yes. Our all inclusive pricing covers professional fitting, balancing and old tyre disposal. No hidden extras."
                },
            },
        ],
    }

def localbusiness_schema_jsonld() -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "AutomotiveBusiness",
        "name": "Bob Jane T-Marts [STORE NAME]",
        "url": "[STORE PAGE URL]",
        "telephone": "[STORE PHONE]",
        "priceRange": "$$",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "[STREET ADDRESS]",
            "addressLocality": "[CITY]",
            "addressRegion": "[STATE]",
            "postalCode": "[POSTCODE]",
            "addressCountry": "AU",
        },
        "openingHoursSpecification": [
            {
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                "opens": "08:00",
                "closes": "17:00",
            },
            {
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": ["Saturday"],
                "opens": "08:00",
                "closes": "12:00",
            },
        ],
        "areaServed": {"@type": "AdministrativeArea", "name": "[PRIMARY SUBURBS OR CITY]"},
    }

# ---------- Export helpers ----------
def as_docx(content: str) -> bytes:
    doc = Document()
    for block in content.split("\n\n"):
        p = doc.add_paragraph(block)
        p.paragraph_format.space_after = Pt(6)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()

def as_bytes(s: str) -> bytes:
    return s.encode("utf-8")

# ---------- Streamlit UI ----------
st.set_page_config(page_title=APP_TITLE, page_icon="🛞", layout="centered")
st.title(APP_TITLE)
st.caption("Enter a tyre size. The app normalises the format and generates SEO and conversion-optimised page content with optional JSON-LD.")

size_input = st.text_input("Tyre Size", placeholder="e.g., 225 45 19 or 225/45R19")

colA, colB = st.columns(2)
with colA:
    include_product = st.checkbox("Include Product JSON-LD", value=True)
with colB:
    include_faq = st.checkbox("Include FAQ JSON-LD", value=True)
include_local = st.checkbox("Include LocalBusiness JSON-LD (for store pages)", value=False)

if st.button("Generate"):
    w, a, r = parse_tyre_size(size_input)
    if not all([w, a, r]):
        st.error("Please enter a valid tyre size like 205/55R16, 225 45 18, or 225/45 18.")
        st.stop()

    size = canonical_size(w, a, r)
    width, aspect, rim = int(w), int(a), int(r)

    segment = classify_segment(width, aspect, rim)
    proof = micro_proof_point(segment, aspect)
    intro = compose_intro(size, segment)
    buy = compose_buy(size)
    bullets = bullets_for(segment, proof)
    others = other_popular_sizes(width, aspect, rim, segment)

    content = render_markdown(size, intro, buy, bullets, others)

    # Word count check (guideline only)
    total_words = word_count(intro) + word_count(buy)
    wc_note = f"Approx body words: {total_words} (target 200–250 across sections)."

    st.success(f"Generated for {size} [{segment}]. {wc_note}")
    st.code(content, language="markdown")

    # JSON-LD outputs
    json_tabs = []
    if include_product or include_faq or include_local:
        json_tabs = st.tabs(
            [label for label, flag in [("Product JSON-LD", include_product), ("FAQ JSON-LD", include_faq), ("LocalBusiness JSON-LD", include_local)] if flag]
        )

    idx = 0
    if include_product:
        prod = product_schema_jsonld(size)
        with json_tabs[idx]:
            st.code(json.dumps(prod, indent=2), language="json")
            st.download_button("Download product.jsonld", data=as_bytes(json.dumps(prod, indent=2)), file_name=f"{size.replace('/','-')}.product.jsonld", mime="application/ld+json")
        idx += 1

    if include_faq:
        faq = faq_schema_jsonld(size)
        with json_tabs[idx]:
            st.code(json.dumps(faq, indent=2), language="json")
            st.download_button("Download faq.jsonld", data=as_bytes(json.dumps(faq, indent=2)), file_name=f"{size.replace('/','-')}.faq.jsonld", mime="application/ld+json")
        idx += 1

    if include_local:
        lb = localbusiness_schema_jsonld()
        with json_tabs[idx]:
            st.code(json.dumps(lb, indent=2), language="json")
            st.download_button("Download localbusiness.jsonld", data=as_bytes(json.dumps(lb, indent=2)), file_name=f"localbusiness.jsonld", mime="application/ld+json")

    # Downloads
    st.download_button("Download as .docx", data=as_docx(content), file_name=f"{size.replace('/','-')}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    st.download_button("Download as .md", data=as_bytes(content), file_name=f"{size.replace('/','-')}.md", mime="text/markdown")

# Footer
st.caption("This tool uses Australian English. No em dashes are used. Meta and copy lengths are auto-trimmed to fit best practice.")
