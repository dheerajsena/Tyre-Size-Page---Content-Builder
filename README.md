# Bob Jane T-Marts Tyre Size Page Generator (Streamlit)

Single and bulk generation of SEO and conversion-optimised tyre size landing pages. Uses Australian English and avoids em dashes.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Single size
- Enter a tyre size like `225 45 19`, `225/45R19` or `225/45 19`.
- Download `.docx`, `.md`, and optional JSON-LD.

## Bulk upload
- Upload `.xlsx` or `.csv` with a `Tyre Size` column. If missing, the app scans all columns for values like `205/55R16` or `225 45 19`.
- Generates content for each unique size and returns a single ZIP with all files.
- Options to include Product, FAQ, and LocalBusiness JSON-LD.

## Output structure per size
- SEO blocks: Target Keywords, Meta Title, Meta Description, H1
- Body: Intro (50–70 words), Buy Online (80–100 words), Why Choose (4 bullets), Other Popular Sizes (4–5), CTA
- Exports: `.md`, `.docx`, optional `.product.jsonld`, `.faq.jsonld`, optional `localbusiness.jsonld`

## Notes
- Heuristics classify the segment (passenger, SUV, 4x4, performance) to shape tone and bullets.
- One micro proof point is injected into the bullets for uniqueness.
- All outputs are sanitised to avoid em dashes.
