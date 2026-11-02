"""One-page Streamlit interface using only C's public pipeline."""

from pathlib import Path
import csv
import hashlib
import io
import re

import pandas as pd
import streamlit as st

from src.cli import DEFAULT_TEST, DEFAULT_TRAIN, PipelineUnavailable, run_requested_pipeline
from src.schema import (CSV_COLUMNS, CLASS_LABELS, FEATURE_COLUMNS, METADATA_COLUMNS,
                        NUMERIC_COLUMNS, NUMERIC_BOUNDS, CleaningAudit, CleaningPlan,
                        CleaningState, DataValidationError, QualityReport, RunResult)

ROOT = Path(__file__).resolve().parent
MAX_CSV_BYTES = 20 * 1024 * 1024


def parse_input_csv(data: bytes) -> pd.DataFrame:
    """Decode and reorder the fixed schema; never infer labels or provenance."""
    if not data or len(data) > MAX_CSV_BYTES:
        raise DataValidationError("CSV为空或超过20 MB限制。")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = data.decode("gb18030")
        except UnicodeDecodeError:
            raise DataValidationError("CSV编码需为UTF-8或GB18030。") from None
    try:
        delimiter = csv.Sniffer().sniff(text[:8192], delimiters=",;\t").delimiter
        rows = csv.reader(io.StringIO(text), delimiter=delimiter, strict=True)
        header = next(rows)
        if len(header) != len(set(header)):
            raise DataValidationError("CSV存在重复列名。")
        if set(header) != set(CSV_COLUMNS):
            missing = sorted(set(CSV_COLUMNS) - set(header))
            extra = sorted(set(header) - set(CSV_COLUMNS))
            raise DataValidationError(f"需17个Adult约定字段；缺少{missing}；额外{extra}。保留_source_id和_group_id。")
        if any(len(row) != len(header) for row in rows if row):
            raise DataValidationError("CSV某行字段数量与表头不一致。")
        frame = pd.read_csv(io.StringIO(text), sep=delimiter, dtype=str, keep_default_na=False)
    except (csv.Error, StopIteration, pd.errors.ParserError, pd.errors.EmptyDataError):
        raise DataValidationError("无法解析CSV表头或记录，请检查分隔符和引号。") from None
    if frame.empty:
        raise DataValidationError("CSV只有表头，没有数据。")
    return frame.loc[:, list(CSV_COLUMNS)]


def preflight_inputs(train: pd.DataFrame, test: pd.DataFrame) -> dict:
    """Local validation only, before any model request or uploaded-file write."""
    from src.normalization import normalize_frame
    for name, frame in (("训练", train), ("测试", test)):
        if frame.empty or tuple(frame.columns) != CSV_COLUMNS:
            raise DataValidationError(f"{name}数据为空或字段不符合约定。")
        if not frame["income"].isin(CLASS_LABELS).all():
            raise DataValidationError(f"{name}标签只能为<=50K或>50K。")
        for column in METADATA_COLUMNS:
            if not frame[column].map(lambda v: isinstance(v, str) and bool(v.strip())
                                     and v.strip().casefold() not in ("?", "null", "none", "nan")).all():
                raise DataValidationError(f"{name}的{column}含缺失来源信息，需先正确准备数据。")
        normalized, _ = normalize_frame(frame)
        if name == "训练":
            if set(frame.income) != set(CLASS_LABELS):
                raise DataValidationError("训练集需要同时包含两个标签类别。")
            for column in NUMERIC_COLUMNS:
                low, high = NUMERIC_BOUNDS[column]
                values = normalized[column].dropna()
                valid = values.gt(low) if column == "fnlwgt" else values.ge(low)
                if high is not None:
                    valid &= values.le(high)
                if not valid.any():
                    raise DataValidationError(f"训练列{column}没有合法观测，无法从训练集学习填补值。")
    for column in METADATA_COLUMNS:
        if set(train[column]) & set(test[column]):
            raise DataValidationError(f"训练和测试的{column}有交叉，请重新按来源组划分。")
    return {"训练行数": len(train), "测试行数": len(test), "特征数": 14,
            "来源隔离": "通过", "模型请求": "未调用",
            "训练不足5000行": len(train) < 5000}


def save_uploaded_inputs(train: pd.DataFrame, test: pd.DataFrame, *, root=ROOT):
    preflight_inputs(train, test)
    train_data = train.to_csv(index=False).encode("utf-8")
    test_data = test.to_csv(index=False).encode("utf-8")
    fingerprint = hashlib.sha256(train_data + b"\x00" + test_data).hexdigest()
    base = (Path(root) / "outputs/uploads").resolve()
    folder = (base / fingerprint).resolve()
    if not folder.is_relative_to(base):
        raise DataValidationError("上传存储路径无效。")
    folder.mkdir(parents=True, exist_ok=True)
    paths = folder / "train.csv", folder / "test.csv"
    for path, data in zip(paths, (train_data, test_data)):
        if path.exists():
            if path.read_bytes() != data:
                raise DataValidationError("已保存的上传数据校验失败。")
        else:
            path.write_bytes(data)
    return paths


def load_history(path, *, root=ROOT) -> RunResult:
    """Rebase a complete saved run inside outputs; this function cannot execute it."""
    path = Path(path).resolve()
    base = (Path(root) / "outputs").resolve()
    if not path.is_relative_to(base) or path.name != "run_result.json":
        raise DataValidationError("仅允许回放本项目outputs内的成功运行。")
    result = RunResult.model_validate_json(path.read_text(encoding="utf-8"))
    if result.status != "succeeded" or result.run_id != path.parent.name or not re.fullmatch(r"\d{8}T\d{6}Z-[a-f0-9]{8}", result.run_id):
        raise DataValidationError("运行未成功或运行ID与目录不符。")
    # A package may be extracted to another machine: only relative artifacts
    # inside the actual saved directory are used, never the exported old path.
    result = result.model_copy(update={"output_dir": str(path.parent)})
    required = {"events", "quality_before", "quality_after", "cleaning_plan", "cleaning_state",
                "audit_train", "audit_test", "metrics", "confusion_matrix", "summary",
                "run_result", "train_processed", "test_processed"}
    if not required <= set(result.artifacts) or any(artifact_path(result, key) is None for key in result.artifacts):
        raise DataValidationError("历史运行文件不完整或路径越界。")
    if artifact_path(result, "run_result") != path:
        raise DataValidationError("历史结果文件与导出清单不一致。")
    before = QualityReport.model_validate_json(artifact_path(result, "quality_before").read_text(encoding="utf-8"))
    plan = CleaningPlan.model_validate_json(artifact_path(result, "cleaning_plan").read_text(encoding="utf-8"))
    if before.dataset != "train" or before.stage != "before" or plan.mode != result.mode:
        raise DataValidationError("历史质量报告或计划模式不一致。")
    from scripts.smoke_check import verify_events
    verify_events(artifact_path(result, "events"), result)
    return result


def history_runs(*, root=ROOT):
    base = Path(root) / "outputs"
    files = list(base.glob("*/run_result.json"))
    for name in ("smoke_runs", "real_llm_check"):
        files.extend((base / name).glob("*/run_result.json"))
    runs = []
    for path in sorted(files, reverse=True):
        try:
            result = load_history(path, root=root)
            count = QualityReport.model_validate_json(artifact_path(result, "quality_before").read_text(encoding="utf-8")).row_count
            runs.append((count >= 5000, result.run_id, path, result))
        except (OSError, ValueError, DataValidationError):
            continue
    return [(path, result) for _, _, path, result in sorted(runs, key=lambda item: item[:2], reverse=True)[:100]]


def history_label(result):
    before = QualityReport.model_validate_json(artifact_path(result, "quality_before").read_text(encoding="utf-8"))
    scale = "规模≥5000" if before.row_count >= 5000 else "小样本，非正式规模"
    return f"{result.run_id} · {result.mode} · 训练{before.row_count}/测试{result.metrics.test_rows} · {scale}"


def column_quality(before, after):
    return pd.DataFrame([{"字段": column,
                          "处理前缺失数": before.missing_by_column.get(column, 0),
                          "处理后缺失数": after.missing_by_column.get(column, 0),
                          "处理前缺失率(%)": 100 * before.missing_by_column.get(column, 0) / max(before.row_count, 1),
                          "处理后缺失率(%)": 100 * after.missing_by_column.get(column, 0) / max(after.row_count, 1)}
                         for column in FEATURE_COLUMNS]).set_index("字段")


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
        with st.expander("列级质量与训练分布", expanded=False):
            columns = column_quality(before, after)
            st.dataframe(columns, width="stretch")
            st.bar_chart(columns[["处理前缺失率(%)", "处理后缺失率(%)"]])
            high_missing = columns.index[columns["处理前缺失率(%)"] >= 20].tolist()
            if high_missing:
                st.warning("缺失率≥20%的训练字段：" + "、".join(high_missing))
            st.caption("20%仅为展示提示阈值，不改变填补策略。统计基于本次训练集。")
            st.dataframe(pd.DataFrame(before.numeric_summary).T, width="stretch")
            st.caption("数值摘要排除非法/缺失观测；q25/q75为四分位数，iqr为四分位距。偏度不足3个观测时为空；旧运行可能没有新增统计。")
    plan = read_artifact(result, "cleaning_plan", CleaningPlan)
    if plan:
        st.subheader("处理策略与理由")
        st.write(f"数值填补：{plan.numeric_imputation}；{plan.reason_numeric}")
        st.write(f"类别填补：{plan.categorical_imputation}；{plan.reason_categorical}")
        st.write("步骤：" + " → ".join(plan.steps))
        state = read_artifact(result, "cleaning_state", CleaningState)
        if state:
            with st.expander("实际训练填补值（测试只应用）"):
                st.dataframe(pd.DataFrame([{"字段": col, "训练学得填补值": str(value)}
                    for col, value in {**state.numeric_fill_values, **state.categorical_fill_values}.items()]), width="stretch")
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
    source = st.radio("数据来源", ["本机CSV", "上传CSV"], horizontal=True)
    demo = st.checkbox("使用演示数据", value=True)
    train = st.text_input("训练 CSV", str(ROOT / DEFAULT_TRAIN), disabled=demo)
    test = st.text_input("测试 CSV", str(ROOT / DEFAULT_TEST), disabled=demo)
    if demo:
        train, test = str(ROOT / DEFAULT_TRAIN), str(ROOT / DEFAULT_TEST)
    uploads = None
    if source == "上传CSV":
        st.caption("上传已正确划分的训练/测试CSV（各≤20 MB）；固定14特征、income、_source_id、_group_id。保留来源元数据，不自动猜测标签或来源。支持UTF-8/GB18030及逗号、分号、制表符。")
        uploads = (st.file_uploader("上传训练CSV", type=["csv"], key="train_upload"),
                   st.file_uploader("上传测试CSV", type=["csv"], key="test_upload"))

    def prepare_inputs():
        if source == "上传CSV":
            if not all(item is not None for item in uploads):
                raise DataValidationError("请同时上传训练和测试CSV。")
            frames = tuple(parse_input_csv(item.getvalue()) for item in uploads)
        else:
            frames = tuple(parse_input_csv(Path(path).read_bytes()) for path in (train, test))
        return frames, preflight_inputs(*frames)
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
                frames, check_result = prepare_inputs()
                st.session_state["input_check"] = check_result
                # Canonical UTF8 CSV also supports alternate uploaded encodings
                # and delimiters while keeping the one production pipeline.
                run_train, run_test = save_uploaded_inputs(*frames)
                result = run_requested_pipeline(run_train, run_test, mode=mode, output_dir=str(ROOT / "outputs"))
                st.session_state["run_result"] = result.model_dump(mode="json")
                st.session_state["result_origin"] = "new"
                progress.update(label="处理成功" if result.status == "succeeded" else "处理失败",
                                state="complete" if result.status == "succeeded" else "error")
            except (FileNotFoundError, PipelineUnavailable, DataValidationError) as exc:
                st.session_state["run_error"] = str(exc)
                progress.update(label="处理失败", state="error")
            except Exception as exc:
                st.session_state["run_error"] = f"无法启动处理（{type(exc).__name__}），请检查输入文件及已交付的流程依赖。"
                progress.update(label="处理失败", state="error")
    if st.button("预检输入（不调用模型）"):
        try:
            _, checked = prepare_inputs()
            st.session_state["input_check"] = checked
        except (OSError, ValueError, DataValidationError) as exc:
            st.session_state.pop("input_check", None)
            st.error(str(exc) if isinstance(exc, DataValidationError) else "无法读取输入CSV。")
    if "input_check" in st.session_state:
        st.caption("上次输入预检（执行时会重新检查）")
        st.json(st.session_state["input_check"])
        if st.session_state["input_check"]["训练不足5000行"]:
            st.warning("此输入不足5000训练行，可用于功能自测，不符合正式课程规模。")
    with st.expander("回放历史成功运行（不创建新运行）"):
        runs = history_runs()
        if runs:
            selected = st.selectbox("历史运行", range(len(runs)),
                format_func=lambda i: history_label(runs[i][1]))
            if st.button("加载历史结果"):
                try:
                    historical = load_history(runs[selected][0])
                    st.session_state["run_result"] = historical.model_dump(mode="json")
                    st.session_state["result_origin"] = "history"
                    st.session_state.pop("run_error", None)
                except (OSError, ValueError, DataValidationError):
                    st.session_state.pop("run_result", None)
                    st.error("历史记录已变化或不完整，请重新选择。")
        else:
            st.caption("outputs中暂无可校验的完整成功运行。")
    if "run_error" in st.session_state:
        st.error(st.session_state["run_error"])
    if "run_result" in st.session_state:
        if st.session_state.get("result_origin") == "history":
            st.warning("历史结果回放：以下运行ID含原始UTC时间，并非本次新请求；选择器不会改变历史结果模式。")
        render_result(RunResult.model_validate(st.session_state["run_result"]))


if __name__ == "__main__":
    main()
