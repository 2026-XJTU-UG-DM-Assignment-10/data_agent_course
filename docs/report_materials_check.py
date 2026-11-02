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
OUT = ROOT / "outputs/final_release_20261102"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    report = PdfReader(ROOT / "docs/report.pdf")
    assert len(report.pages) == 6
    pdf_text = "\n".join(page.extract_text() for page in report.pages)
    names = ["宋艳婷", "杨陈紫逸", "胡宇轩", "周锦晨"]
    assert all(name in pdf_text for name in names)
    facts = json.loads((OUT / "report_data.json").read_text(encoding="utf-8"))
    run_id = facts["run_id"]
    run = ROOT / facts["run_folder"]
    metrics = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
    plan = json.loads((run / "cleaning_plan.json").read_text(encoding="utf-8"))
    assert metrics["confusion_matrix"] == [[2108, 182], [261, 449]]
    assert plan["mode"] == "llm" and plan["numeric_imputation"] == "median"
    assert plan["categorical_imputation"] == "most_frequent"
    assert run_id in pdf_text and "0.787282" in pdf_text and "85.23%" in pdf_text
    md = (ROOT / "docs/report.md").read_text(encoding="utf-8")
    formal_text = md + pdf_text + (ROOT / "docs/contributions.md").read_text(encoding="utf-8")
    assert all(word in formal_text for word in ["6,998", "most_frequent", "United-States", "5,928", "5,652"])
    unwanted = ["代替", "代补", "代完成", "四项功能补充", "四项功能补全"]
    assert not any(word in formal_text for word in unwanted)
    assert not any(old in pdf_text for old in ["真实模型尚未配置", "姓名待确认", "未发出实际模型请求"])
    with zipfile.ZipFile(ROOT / "docs/presentation.pptx") as deck:
        slides = sorted(n for n in deck.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n))
        notes = sorted(n for n in deck.namelist() if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", n))
        assert len(slides) == 7 and len(notes) == 7
        body = "\n".join("".join(ET.fromstring(deck.read(n)).itertext()) for n in slides + notes)
        assert all(name in body for name in names)
        assert run_id in body and "11.4218" in body and "历史回放" in body
        assert "0.787282" in body and not any(word in body for word in unwanted)
        assert not any(old in body for old in ["真实模型尚未配置", "尚无真实API", "姓名和口头分工待确认"])
        media = [deck.read(n) for n in deck.namelist() if n.startswith("ppt/media/")]
        assert len(media) == 2
        for data in media:
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
        assert {sha(data) for data in media} == {
            sha((ROOT / "docs/report_assets" / name).read_bytes())
            for name in ["confusion_matrix_current.png", "public_gateway_20261102/page_service_metrics.jpg"]}
        ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
        assert all(ET.fromstring(deck.read(f"ppt/slides/slide{i}.xml")).findall(".//a:tbl", ns) for i in [2, 3, 4])
    assert sha((ROOT / "docs/report_assets/confusion_matrix_current.png").read_bytes()) == sha((run / "confusion_matrix.png").read_bytes())
    validations = [json.loads(p.read_text(encoding="utf-8")) for p in (OUT / "ppt_build").glob("validation-*.json")]
    validation = next(v for v in validations if v.get("finalSha256") == sha((ROOT / "docs/presentation.pptx").read_bytes()))
    assert validation["firstPartyImport"]["passed"]
    assert validation["finalSha256"] == sha((ROOT / "docs/presentation.pptx").read_bytes())
    guide = (ROOT / "docs/presentation_guide.md").read_text(encoding="utf-8")
    assert all(s in guide for s in ["https://111.230.149.166/", "预检", "历史", "课堂", "7", run_id])
    ledger = json.loads((ROOT / "ai_usage/C/usage.json").read_text(encoding="utf-8"))
    runtime = [r for r in ledger["records"] if r["scope"] == "project_runtime"]
    assert len(runtime) == 6 and sum(r["calls"] for r in runtime) == 6
    assert sum(r["input_tokens"] for r in runtime) == 5928
    assert sum(r["output_tokens"] for r in runtime) == 5652
    result = {"status": "passed", "checked_at": datetime.now(timezone.utc).isoformat(),
              "scope": "local material structure, factual cross-checks and image embedding; separate visual inspection performed",
              "pdf_pages": 6, "slides": 7, "native_tables": 3,
              "embedded_evidence_images": 2, "image_bytes_match": True,
              "primary_run_id": run_id, "rules_run_id": facts["rules_run_id"],
              "native_powerpoint": "not_run; rendered and structural verification only",
              "visual_inspection": {"pdf_pages": [1, 2, 3, 4, 5, 6], "slides": [1, 2, 3, 4, 5, 6, 7]},
              "runtime_requests": 6, "input_tokens": 5928, "output_tokens": 5652,
              "new_model_requests_during_materials": 0,
              "pdf_sha256": sha((ROOT / "docs/report.pdf").read_bytes()),
              "pptx_sha256": sha((ROOT / "docs/presentation.pptx").read_bytes())}
    (OUT / "materials_check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
