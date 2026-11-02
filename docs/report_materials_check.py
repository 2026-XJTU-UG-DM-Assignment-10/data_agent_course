"""Verify material claims and embedded evidence against actual saved runs."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import io
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from PIL import Image
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/materials_20261102"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    report = PdfReader(ROOT / "docs/report.pdf")
    assert len(report.pages) == 6
    pdf_text = "\n".join(page.extract_text() for page in report.pages)
    names = ["宋艳婷", "杨陈紫逸", "胡宇轩", "周锦晨"]
    assert all(name in pdf_text for name in names)
    run_id = "20261102T043037Z-b0fc7c1a"
    run = ROOT / "outputs/smoke_runs" / run_id
    metrics = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
    plan = json.loads((run / "cleaning_plan.json").read_text(encoding="utf-8"))
    assert metrics["confusion_matrix"] == [[2101, 189], [254, 456]]
    assert plan["mode"] == "llm" and plan["numeric_imputation"] == "median"
    assert plan["categorical_imputation"] == "constant"
    assert run_id in pdf_text and "0.788846" in pdf_text and "85.23%" in pdf_text
    assert not any(old in pdf_text for old in ["真实模型尚未配置", "姓名待确认", "未发出实际模型请求"])
    with zipfile.ZipFile(ROOT / "docs/presentation.pptx") as deck:
        slides = sorted(n for n in deck.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n))
        notes = sorted(n for n in deck.namelist() if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", n))
        assert len(slides) == 7 and len(notes) == 7
        body = "\n".join("".join(ET.fromstring(deck.read(n)).itertext()) for n in slides + notes)
        assert all(name in body for name in names)
        assert run_id in body and "11.4218" in body and "历史回放" in body
        assert not any(old in body for old in ["真实模型尚未配置", "尚无真实API", "姓名和口头分工待确认"])
        media = [deck.read(n) for n in deck.namelist() if n.startswith("ppt/media/")]
        assert len(media) == 2
        for data in media:
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
        assert {sha(data) for data in media} == {
            sha((ROOT / "docs/report_assets" / name).read_bytes())
            for name in ["confusion_matrix_llm.png", "page_llm_history.jpg"]}
        ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
        assert all(ET.fromstring(deck.read(f"ppt/slides/slide{i}.xml")).findall(".//a:tbl", ns) for i in [2, 3, 4])
    assert sha((ROOT / "docs/report_assets/confusion_matrix_llm.png").read_bytes()) == sha((run / "confusion_matrix.png").read_bytes())
    validation = json.loads((OUT / "ppt_build/validation-v3.json").read_text(encoding="utf-8"))
    assert validation["firstPartyImport"]["passed"]
    assert validation["finalSha256"] == sha((ROOT / "docs/presentation.pptx").read_bytes())
    result = {"status": "passed", "checked_at": datetime.now(timezone.utc).isoformat(),
              "scope": "local material structure, factual cross-checks and image embedding; separate visual inspection performed",
              "pdf_pages": 6, "slides": 7, "native_tables": 3,
              "embedded_evidence_images": 2, "image_bytes_match": True,
              "primary_run_id": run_id, "native_powerpoint": "not_run; app access approval timed out",
              "new_model_requests_during_materials": 0,
              "pdf_sha256": sha((ROOT / "docs/report.pdf").read_bytes()),
              "pptx_sha256": sha((ROOT / "docs/presentation.pptx").read_bytes())}
    (OUT / "materials_check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
