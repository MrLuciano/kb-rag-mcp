"""Shared docling utilities: singleton DocumentConverter with GPU acceleration.

Use `get_docling_converter()` instead of creating a new `DocumentConverter()`
for every PDF — this avoids repeated model downloads from HuggingFace and
enables GPU batch inference.

Environment variables (set before first call or in .env):

    DOCLING_ARTIFACTS_PATH=/persistent/path/models  # avoid re-download
    DOCLING_DEVICE=cuda                              # force GPU (auto/cpu/cuda/mps)
    DOCLING_NUM_THREADS=8                             # CPU thread count
    HF_HUB_ENABLE_HF_TRANSFER=1                      # faster downloads
"""

import logging
import os
from functools import lru_cache

log = logging.getLogger("kb-ingest.docling_utils")


@lru_cache(maxsize=1)
def get_docling_converter():
    """Return a singleton DocumentConverter configured for maximum throughput.

    GPU acceleration is enabled when CUDA is available (or when
    ``DOCLING_DEVICE=cuda`` is set). Batch sizes are increased for
    layout/OCR stages. Set ``DOCLING_ARTIFACTS_PATH`` to avoid
    re-downloading models from HuggingFace.
    """
    try:
        from docling.datamodel.accelerator_options import (
            AcceleratorDevice,
            AcceleratorOptions,
        )
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import (
            PdfPipelineOptions,
            RapidOcrOptions,
            TableFormerMode,
        )
        from docling.document_converter import DocumentConverter, PdfFormatOption

        extra_log = []

        device_str = os.environ.get("DOCLING_DEVICE", "auto")
        num_threads = int(os.environ.get("DOCLING_NUM_THREADS", "0")) or (
            os.cpu_count() or 4
        )

        accelerator_options = AcceleratorOptions(
            num_threads=num_threads,
            device=device_str,
        )
        extra_log.append(f"device={device_str}")

        # ── Pipeline: batch layout + OCR for throughput ───────────────
        pdf_pipeline_options = PdfPipelineOptions(
            do_ocr=True,
            do_table_structure=True,
            accelerator_options=accelerator_options,
        )
        pdf_pipeline_options.ocr_batch_size = 64        # default 4
        pdf_pipeline_options.layout_batch_size = 64      # default 4
        pdf_pipeline_options.table_structure_options.mode = (
            TableFormerMode.FAST
        )
        pdf_pipeline_options.ocr_options = RapidOcrOptions()

        extra_log.append(f"ocr_batch={pdf_pipeline_options.ocr_batch_size}")
        extra_log.append(f"layout_batch={pdf_pipeline_options.layout_batch_size}")

        # ── Build converter once ───────────────────────────────────────
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pdf_pipeline_options,
                ),
            },
        )

        log.info("docling converter initialized: %s", ", ".join(extra_log))
        return converter

    except ImportError:
        return None


def check_models_cached() -> bool:
    """Check whether all docling models are already cached locally."""
    path = os.environ.get("DOCLING_ARTIFACTS_PATH")
    if path and os.path.isdir(path):
        return True
    hf_cache = os.environ.get(
        "HF_HOME",
        os.path.join(os.path.expanduser("~"), ".cache", "huggingface"),
    )
    hub_dir = os.path.join(hf_cache, "hub")
    if os.path.isdir(hub_dir):
        return True
    return False