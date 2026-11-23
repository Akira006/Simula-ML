import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "rubric" / "examples"


@pytest.fixture
def api_rubric():
    return json.loads((EXAMPLES / "optimasi-api-endpoint-produk.rubric.json").read_text(encoding="utf-8"))


@pytest.fixture
def api_case():
    return json.loads((EXAMPLES / "optimasi-api-endpoint-produk.case.json").read_text(encoding="utf-8"))


@pytest.fixture
def marketing_rubric():
    return json.loads((EXAMPLES / "kalender-konten-media-sosial.rubric.json").read_text(encoding="utf-8"))


@pytest.fixture
def marketing_case():
    return json.loads((EXAMPLES / "kalender-konten-media-sosial.case.json").read_text(encoding="utf-8"))


@pytest.fixture
def good_submission():
    return {
        "slots": [
            {"id": "kode", "title": "Kode sumber", "kind": "code_zip",
             "content": "=== FILE: README.md ===\n# Optimasi endpoint produk\nAkar masalah: filter category tanpa indeks.\n"
                        "Sebelum: p50 3,8 detik. Sesudah: p50 220 ms (autocannon, 100 koneksi, 30 detik).\n"
                        "=== FILE: migrations/001_idx_category.sql ===\nCREATE INDEX idx_products_category ON products(category);\n"
                        "=== FILE: src/products/repository.ts ===\nexport const findByCategory = (c: string) =>\n"
                        "  db.query('SELECT id, name, price FROM products WHERE category = $1', [c]);"},
            {"id": "penjelasan", "title": "Penjelasan solusi", "kind": "text",
             "content": "Saya mengukur endpoint dengan autocannon lalu menjalankan EXPLAIN ANALYZE. Query memakai sequential scan "
                        "pada 50.000 baris karena kolom category tidak berindeks. Saya menambah indeks lewat migrasi dan "
                        "membatasi kolom yang diambil sesuai output lama. Tes snapshot memastikan respons tetap sama."},
        ],
        "note": "Terima kasih.",
    }


@pytest.fixture
def attacks():
    return json.loads((ROOT / "tests" / "fixtures" / "injection" / "attacks.json").read_text(encoding="utf-8"))["cases"]
