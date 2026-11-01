"""One-page Streamlit interface using only C's public pipeline."""

from pathlib import Path

import pandas as pd
import streamlit as st

from src.cli import DEFAULT_TEST, DEFAULT_TRAIN, PipelineUnavailable, run_requested_pipeline
from src.schema import CleaningAudit, CleaningPlan, QualityReport, RunResult

ROOT = Path(__file__).resolve().parent


def artifact_path(result: RunResult, name: str) -> Path | None:
    """Only expose files explicitly exported inside this run's directory."""
    relative = result.artifacts.get(name)
    if not relative or Path(relative).is_absolute():
        return None
    root = Path(result.output_dir).resolve()
    path = (root / relative).resolve()
    return path if path.is_relative_to(root) and path.is_file() else None


def read_artifact(result, name, schema):
    path = artifact_path(result, name)
    if path is None:
        return None
    try:
        return schema.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        st.warning(f"导出文件无法读取或不符合公共契约：{name}")
        return None


def render_result(result: RunResult):
    st.caption(f"运行 ID：{result.run_id} · 结果模式：{result.mode}")
    if result.status == "failed":
        st.error(f"处理失败：{result.error_code}。请查看本次运行日志。")
    else:
        st.success("处理成功")
    before = read_artifact(result, "quality_before", QualityReport)
    after = read_artifact(result, "quality_after", QualityReport)
    if before and after:
        def counts(report):
            return [report.row_count, sum(report.missing_by_column.values()),
                    report.duplicate_rows, report.outlier_cells, report.format_issue_cells]
        st.subheader("训练集质量变化")
        st.table(pd.DataFrame({"指标": ["行数", "缺失单元格", "多余重复行", "异常单元格", "格式问题单元格"],
                               "处理前": counts(before), "处理后": counts(after)}))
        st.caption("四类问题可能重叠，不能相加作为问题总行数。")
    plan = read_artifact(result, "cleaning_plan", CleaningPlan)
    if plan:
        st.subheader("处理策略与理由")
        st.write(f"数值填补：{plan.numeric_imputation}；{plan.reason_numeric}")
        st.write(f"类别填补：{plan.categorical_imputation}；{plan.reason_categorical}")
        st.write("步骤：" + " → ".join(plan.steps))
    for name in ("audit_train", "audit_test"):
        audit = read_artifact(result, name, CleaningAudit)
        if audit:
            with st.expander(f"实际删除及修改数量（{audit.dataset}）"):
                st.json(audit.model_dump(mode="json"))
    if result.status == "succeeded" and result.metrics:
        st.subheader("测试集分类结果")
        left, right = st.columns(2)
        left.metric("Accuracy", f"{result.metrics.accuracy:.2%}")
        right.metric("Macro-F1", f"{result.metrics.macro_f1:.2%}")
        st.caption(f"测试行数：{result.metrics.test_rows}；类别计数：{result.metrics.class_counts_test}")
        st.table(pd.DataFrame(result.metrics.confusion_matrix,
                              index=[f"真实 {x}" for x in result.metrics.labels],
                              columns=[f"预测 {x}" for x in result.metrics.labels]))
        matrix = artifact_path(result, "confusion_matrix")
        if matrix and matrix.suffix.lower() == ".png":
            st.image(str(matrix), caption="行是真实类别，列是预测类别")
    st.subheader("下载本次运行文件")
    for name, relative in result.artifacts.items():
        path = artifact_path(result, name)
        if path is None:
            st.warning(f"导出文件缺失或路径无效：{name}")
            continue
        st.download_button(f"下载 {name}", path.read_bytes(), file_name=Path(relative).name,
                           key=f"download-{result.run_id}-{name}", on_click="ignore")


def main():
    st.set_page_config(page_title="数据清洗与分类智能体", layout="wide")
    st.title("数据清洗与分类智能体")
    demo = st.checkbox("使用演示数据", value=True)
    train = st.text_input("训练 CSV", str(ROOT / DEFAULT_TRAIN), disabled=demo)
    test = st.text_input("测试 CSV", str(ROOT / DEFAULT_TEST), disabled=demo)
    if demo:
        train, test = str(ROOT / DEFAULT_TRAIN), str(ROOT / DEFAULT_TEST)
    mode = st.selectbox("运行模式", ["rules", "llm"],
                        format_func=lambda x: "rules · 固定规则" if x == "rules" else "llm · 真实模型")
    st.info(f"当前选择模式：{mode}。仅点击“开始处理”创建新运行。")
    if st.checkbox("查看合成页面示例（非真实运行）", value=False):
        st.warning("合成页面示例：指标和返回对象来自 examples，不能作为实验或模型调用证据。")
        example = RunResult.model_validate_json((ROOT / "examples/run_result_example.json").read_text(encoding="utf-8"))
        example.output_dir = str(ROOT / "examples")
        render_result(example)
    if st.button("开始处理", type="primary"):
        st.session_state.pop("run_result", None)
        st.session_state.pop("run_error", None)
        with st.status("正在执行检测、计划、清洗、分类和导出…", expanded=True) as progress:
            try:
                result = run_requested_pipeline(train, test, mode=mode, output_dir=str(ROOT / "outputs"))
                st.session_state["run_result"] = result.model_dump(mode="json")
                progress.update(label="处理成功" if result.status == "succeeded" else "处理失败",
                                state="complete" if result.status == "succeeded" else "error")
            except (FileNotFoundError, PipelineUnavailable) as exc:
                st.session_state["run_error"] = str(exc)
                progress.update(label="处理失败", state="error")
            except Exception as exc:
                st.session_state["run_error"] = f"无法启动处理（{type(exc).__name__}），请检查输入文件及已交付的流程依赖。"
                progress.update(label="处理失败", state="error")
    if "run_error" in st.session_state:
        st.error(st.session_state["run_error"])
    if "run_result" in st.session_state:
        render_result(RunResult.model_validate(st.session_state["run_result"]))


if __name__ == "__main__":
    main()
