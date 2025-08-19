import re
import io
import json
import zipfile
from typing import List, Tuple, Iterable
import streamlit as st
from docx import Document
from docx.shared import Pt
import pandas as pd

APP_TITLE = "Bob Jane T-Marts Tyre Size Page Generator"

# ---------- Utils ----------
def sanitize(text: str) -> str:
    if not text:
        return ""
    return text.replace("—", "-").replace("–", "-")

def parse_tyre_size(raw: str) -> Tuple[str, str, str]:
    if not raw:
        return "", "", ""
    s = str(raw).upper().strip()
    s = re.sub(r"[^\dR/ -]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    m = re.match(r"^(\d{3})\s*/\s*(\d{2})\s*R?\s*(\d{2})$", s)
    if m: return m.group(1), m.group(2), m.group(3)
    m = re.match(r"^(\d{3})\s+(\d{2})\s+(\d{2})$", s)
    if m: return m.group(1), m.group(2), m.group(3)
    m = re.match(r"^(\d{3})\s*/\s*(\d{2})\s+(\d{2})$", s)
    if m: return m.group(1), m.group(2), m.group(3)
    m = re.match(r"^(\d{3})-(\d{2})-(\d{2})$", s)
    if m: return m.group(1), m.group(2), m.group(3)
    return "", "", ""

def canonical_size(width: str, aspect: str, rim: str) -> str:
    if not (width and aspect and rim):
        return ""
    return f"{width}/{aspect}R{rim}"

def classify_segment(width: int, aspect: int, rim: int) -> str:
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
    return "Sure-footed braking for urban stop-start traffic" if aspect < 60 else "Balanced wet braking for sudden showers"

def other_popular_sizes(width: int, aspect: int, rim: int, segment: str) -> List[str]:
    suggestions = set()
    def clamp_w(w): return max(155, min(w, 345))
    def clamp_a(a): return max(30, min(a, 80))
    def clamp_r(r): return max(13, min(r, 22))
    candidates = [
        (clamp_w(width+10), aspect, rim),
        (clamp_w(width-10), aspect, rim),
        (width, clamp_a(aspect+5), rim),
        (width, clamp_a(aspect-5), rim),
        (width, aspect, clamp_r(rim+1)),
        (width, aspect, clamp_r(rim-1)),
    ]
    if segment in ("4x4", "suv"):
        candidates += [(clamp_w(width+20), clamp_a(aspect+5), rim), (clamp_w(width+10), aspect, clamp_r(rim+1))]
    elif segment == "performance":
        candidates += [(clamp_w(width+10), clamp_a(aspect-5), rim), (width, clamp_a(aspect-5), clamp_r(rim+1))]
    for w,a,r in candidates:
        if (w,a,r) != (width,aspect,rim):
            suggestions.add(f"{w}/{a}R{r}")
    return list(suggestions)[:5]

def limit_chars(s: str, max_len: int) -> str:
    s = sanitize(s.strip())
    return s if len(s) <= max_len else s[:max_len-1].rstrip() + "..."

def word_count(s: str) -> int:
    return len(s.strip().split())

# ---------- Content ----------
def target_keywords(size: str) -> List[str]:
    return [f"{size} tyres", f"buy {size} tyres online", f"best price {size} Australia", "Bob Jane T-Marts tyres"]

def compose_intro(size: str, segment: str) -> str:
    if segment == "performance":
        txt = (f"Engineered for performance vehicles, {size} tyres deliver sharp handling, cornering grip and responsive braking. "
               f"The lower profile helps keep steering precise while modern compounds support stability at speed. "
               f"Choose {size} for confident control on Australian roads in wet and dry conditions.")
    elif segment == "4x4":
        txt = (f"Designed for SUVs and 4x4s, {size} tyres provide strength, stability and traction on highways and light off-road terrain. "
               f"Robust constructions and versatile tread patterns deliver comfort and control across long distances. "
               f"Choose {size} for dependable performance in varied Australian conditions.")
    elif segment == "suv":
        txt = (f"Built for SUVs and crossovers, {size} tyres offer stable handling, sure grip and a comfortable ride. "
               f"Durable, touring-focused tread patterns make daily errands and road trips smoother and quieter. "
               f"Choose {size} for reliable performance across Australian roads and weather.")
    else:
        txt = (f"Popular with hatchbacks and sedans, {size} tyres balance safety, comfort and fuel efficiency for everyday driving. "
               f"Tuned tread patterns help reduce noise while maintaining confident braking in wet and dry conditions. "
               f"Choose {size} for long-lasting performance on Australian roads.")
    return sanitize(txt)

def compose_buy(size: str) -> str:
    txt = (f"Buying {size} tyres is quick and simple with Bob Jane T-Marts. Use our online tyre finder to select the right fit in minutes. "
           f"Pricing is transparent and all-inclusive, covering professional fitting, balancing and the responsible disposal of your old tyres. "
           f"With our Best Tyre Price Guarantee, Tyre Satisfaction Guarantee and nationwide stores, you will enjoy great value, easy booking and expert service from checkout to fitment.")
    return sanitize(txt)

def bullets_for(segment: str, proof: str) -> List[str]:
    if segment == "performance":
        base = ["Precise steering and cornering grip","Strong, predictable braking","Sporty road feel with comfort in mind"]
    elif segment == "4x4":
        base = ["Confident highway and light off-road grip","Comfortable, stable ride","Durable construction for long life"]
    elif segment == "suv":
        base = ["Stable handling for larger SUVs","Quiet, comfortable touring","Reliable wet and dry performance"]
    else:
        base = ["Comfortable, quiet everyday ride","Confident wet and dry traction","Fuel efficient, long wearing designs"]
    out = [sanitize(proof)] + base
    return out[:4]

def make_meta_title(size: str) -> str:
    return limit_chars(f"{size} Tyres | Best Price Online | Bob Jane T-Marts", 60)

def make_meta_description(size: str) -> str:
    return limit_chars(f"Shop {size} tyres online at Bob Jane T-Marts. Best Price Guarantee, fitting and balancing included, nationwide stores. Book online today.", 160)

def render_markdown(size: str, intro: str, buy: str, bullets: List[str], other_sizes: List[str]) -> str:
    kw = ", ".join(target_keywords(size))
    content = f"""Target Keywords: {kw}

Meta Title: {make_meta_title(size)}

Meta Description: {make_meta_description(size)}

H1: {size} Tyres

Intro (50-70 words)
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

# ---------- Schema ----------
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
            {"@type": "Question","name": f"What vehicles use {size} tyres?","acceptedAnswer": {"@type": "Answer","text": f"Many hatchbacks, sedans and SUVs use {size} tyres. Use our online tyre finder to confirm fitment for your vehicle and book fitting at a nearby store."}},
            {"@type": "Question","name": f"Can I buy {size} tyres online and fit in store?","acceptedAnswer": {"@type": "Answer","text": f"Yes. Order {size} tyres online, choose a store and a time that suits you, and our team will fit and balance your new tyres with disposal included."}},
            {"@type": "Question","name": "Do prices include fitting and balancing?","acceptedAnswer": {"@type": "Answer","text": "Yes. Our all inclusive pricing covers professional fitting, balancing and old tyre disposal. No hidden extras."}},
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
        "address": {"@type": "PostalAddress","streetAddress": "[STREET ADDRESS]","addressLocality": "[CITY]","addressRegion": "[STATE]","postalCode": "[POSTCODE]","addressCountry": "AU"},
        "openingHoursSpecification": [
            {"@type": "OpeningHoursSpecification","dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday"],"opens": "08:00","closes": "17:00"},
            {"@type": "OpeningHoursSpecification","dayOfWeek": ["Saturday"],"opens": "08:00","closes": "12:00"}
        ],
        "areaServed": {"@type": "AdministrativeArea","name": "[PRIMARY SUBURBS OR CITY]"},
    }

# ---------- Export helpers ----------
def docx_bytes(content: str) -> bytes:
    content = sanitize(content)
    doc = Document()
    for block in content.split("\n\n"):
        p = doc.add_paragraph(block)
        p.paragraph_format.space_after = Pt(6)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()

def md_bytes(content: str) -> bytes:
    return sanitize(content).encode("utf-8")

def generate_for_size(size: str, include_product: bool, include_faq: bool, include_local: bool) -> dict:
    w, a, r = parse_tyre_size(size)
    if not all([w, a, r]):
        return {"error": f"Invalid size: {size}"}
    canonical = canonical_size(w, a, r)
    width, aspect, rim = int(w), int(a), int(r)
    segment = classify_segment(width, aspect, rim)
    proof = micro_proof_point(segment, aspect)
    intro = compose_intro(canonical, segment)
    buy = compose_buy(canonical)
    bullets = bullets_for(segment, proof)
    others = other_popular_sizes(width, aspect, rim, segment)
    content = render_markdown(canonical, intro, buy, bullets, others)
    files = {
        f"{canonical.replace('/','-')}.md": md_bytes(content),
        f"{canonical.replace('/','-')}.docx": docx_bytes(content),
    }
    if include_product:
        files[f"{canonical.replace('/','-')}.product.jsonld"] = json.dumps(product_schema_jsonld(canonical), indent=2).encode("utf-8")
    if include_faq:
        files[f"{canonical.replace('/','-')}.faq.jsonld"] = json.dumps(faq_schema_jsonld(canonical), indent=2).encode("utf-8")
    if include_local:
        files["localbusiness.jsonld"] = json.dumps(localbusiness_schema_jsonld(), indent=2).encode("utf-8")
    return {"size": canonical, "content": content, "files": files}

def extract_sizes_from_df(df: pd.DataFrame) -> List[str]:
    sizes = []
    size_re = re.compile(r"\b\d{3}\s*[\/ ]\s*\d{2}\s*R?\s*\d{2}\b", re.IGNORECASE)
    if "Tyre Size" in df.columns:
        sizes = [str(v) for v in df["Tyre Size"].dropna().tolist() if size_re.search(str(v))]
    else:
        # scan all columns
        for col in df.columns:
            sizes += [m.group(0) for v in df[col].dropna().astype(str) for m in [size_re.search(v)] if m]
    # normalise
    canon = set()
    for s in sizes:
        w,a,r = parse_tyre_size(s)
        if all([w,a,r]):
            canon.add(canonical_size(w,a,r))
    return sorted(canon)

def zip_bytes(files_map: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files_map.items():
            zf.writestr(name, data)
    buf.seek(0)
    return buf.read()

# ---------- Streamlit UI ----------
st.set_page_config(page_title=APP_TITLE, page_icon="🛞", layout="wide")
st.title(APP_TITLE)
st.caption("Generate SEO and conversion-optimised tyre size pages. Single or bulk. Australian English. No em dashes.")

tab_single, tab_bulk = st.tabs(["Single size", "Bulk upload"])

with tab_single:
    size_input = st.text_input("Tyre Size", placeholder="e.g., 225 45 19 or 225/45R19")
    colA, colB, colC = st.columns(3)
    with colA:
        include_product = st.checkbox("Include Product JSON-LD", value=True, key="p1")
    with colB:
        include_faq = st.checkbox("Include FAQ JSON-LD", value=True, key="f1")
    with colC:
        include_local = st.checkbox("Include LocalBusiness JSON-LD", value=False, key="l1")
    if st.button("Generate", key="g1"):
        res = generate_for_size(size_input, include_product, include_faq, include_local)
        if "error" in res:
            st.error(res["error"])
        else:
            st.success(f"Generated for {res['size']}")
            st.code(res["content"], language="markdown")
            st.download_button("Download .docx", res["files"][f"{res['size'].replace('/','-')}.docx"], file_name=f"{res['size'].replace('/','-')}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            st.download_button("Download .md", res["files"][f"{res['size'].replace('/','-')}.md"], file_name=f"{res['size'].replace('/','-')}.md", mime="text/markdown")
            if include_product:
                st.download_button("Download product.jsonld", res["files"][f"{res['size'].replace('/','-')}.product.jsonld"], file_name=f"{res['size'].replace('/','-')}.product.jsonld", mime="application/ld+json")
            if include_faq:
                st.download_button("Download faq.jsonld", res["files"][f"{res['size'].replace('/','-')}.faq.jsonld"], file_name=f"{res['size'].replace('/','-')}.faq.jsonld", mime="application/ld+json")
            if include_local:
                st.download_button("Download localbusiness.jsonld", res["files"]["localbusiness.jsonld"], file_name="localbusiness.jsonld", mime="application/ld+json")

with tab_bulk:
    st.subheader("Upload a sheet and generate pages for all unique sizes")
    st.write("Accepts `.xlsx` or `.csv`. A column named **Tyre Size** is preferred. If not present, the app will scan all columns for values that look like tyre sizes.")
    file = st.file_uploader("Upload Excel or CSV", type=["xlsx", "csv"])
    col1, col2, col3 = st.columns(3)
    with col1:
        b_include_product = st.checkbox("Include Product JSON-LD", value=True, key="p2")
    with col2:
        b_include_faq = st.checkbox("Include FAQ JSON-LD", value=True, key="f2")
    with col3:
        b_include_local = st.checkbox("Include LocalBusiness JSON-LD", value=False, key="l2")
    if file is not None:
        try:
            if file.name.lower().endswith(".xlsx"):
                df = pd.read_excel(file)
            else:
                df = pd.read_csv(file)
        except Exception as e:
            st.error(f"Could not read file: {e}")
            df = None
        if df is not None:
            sizes = extract_sizes_from_df(df)
            st.info(f"Found {len(sizes)} unique sizes.")
            if sizes:
                st.dataframe(pd.DataFrame({"Tyre Size": sizes}))
                if st.button("Generate ZIP", key="bulkgen"):
                    all_files = {}
                    for sz in sizes:
                        res = generate_for_size(sz, b_include_product, b_include_faq, b_include_local)
                        if "files" in res:
                            for name, data in res["files"].items():
                                all_files[name] = data
                    zdata = zip_bytes(all_files)
                    st.download_button("Download all pages as ZIP", data=zdata, file_name="tyre_pages_bulk.zip", mime="application/zip")
            else:
                st.warning("No valid tyre sizes detected in the sheet. Ensure a column contains values like 225/45R19 or 225 45 19.")

st.caption("Tip: Use a column named 'Tyre Size' for best results. Validate JSON-LD in Google's Rich Results Test before publishing.")
