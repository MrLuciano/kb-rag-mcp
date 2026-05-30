# AMD GPU Acceleration for Docling — Research Findings

**Date:** 2026-05-28  
**Author:** OpenCode (kb-rag-mcp session)  
**Hardware:** AMD Ryzen 7 PRO 8845HS w/ Radeon 780M Graphics  
**Environment:** WSL2 (Linux 6.6.87.2-microsoft-standard-WSL2)

---

## 1. Executive Summary

**Can docling be accelerated on AMD Radeon 780M iGPU?**  
→ **Partially, on Windows only, and with limited benefit.**

Docling's OCR sub-component (RapidOCR) can leverage DirectML on Windows with `onnxruntime-directml`, but the heavy-duty layout detection and image classification models are hardcoded to CPU/CUDA only. TableFormer uses PyTorch, which would require `torch-directml` (untested). On an integrated GPU with limited memory bandwidth, the expected speedup is modest (1.5–3× at best for OCR only), not the 6–10× seen with CUDA on discrete GPUs.

**Recommendation:** Continue running docling on CPU. The engineering effort to patch and validate DirectML support across all docling sub-models outweighs the marginal gains on this hardware.

---

## 2. Hardware & Environment Assessment

### 2.1 What the System Reports

```bash
# lspci inside WSL2
35b4:00:00.0 3D controller: Microsoft Corporation Device
4158:00:00.0 3D controller: Microsoft Corporation Basic Render Driver

# CPU
AMD Ryzen 7 PRO 8845HS w/ Radeon 780M Graphics
16 threads (8 cores × 2 SMT)

# PyTorch
Torch 2.12.0+cu130
CUDA available: False
ROCm/HIP available: None
```

### 2.2 Why ROCm Is Not an Option

- **ROCm does not support integrated GPUs.** The Radeon 780M is an RDNA3-based iGPU, and AMD's ROCm stack only supports select discrete GPUs (RX 7900 series, MI series).
- **WSL2 ROCm** is even more restricted: only specific discrete RDNA3+ cards are supported.
- No `/dev/dri`, no `rocminfo`, no ROCm packages available.

### 2.3 DirectML — The Only Viable Path on Windows

DirectML is Microsoft's hardware-agnostic ML inference API. ONNX Runtime supports it via `onnxruntime-directml`. However, DirectML support on AMD iGPUs is **experimental** and performance is highly model-dependent.

---

## 3. Docling Architecture & GPU Usage

Docling's PDF pipeline consists of multiple stages, each with different backends:

| Stage | Backend | Uses GPU? | GPU Type Supported |
|-------|---------|-----------|-------------------|
| **RapidOCR** (text detection & recognition) | ONNX Runtime | ✅ Yes (configurable) | CUDA, DirectML (Windows), CoreML (macOS) |
| **Layout Detection** (docling-layout-heron) | ONNX Runtime | ❌ Hardcoded to CPU/CUDA | CPU, CUDA only |
| **Image Classification** | ONNX Runtime | ❌ Hardcoded to CPU/CUDA | CPU, CUDA only |
| **TableFormer** (table structure) | PyTorch (`docling_ibm_models`) | ⚠️ Via PyTorch device | CUDA, MPS, XPU; `torch-directml` untested |

### 3.1 RapidOCR — DirectML Already Supported

**Source:** `docling/models/stages/ocr/rapid_ocr_model.py`

```python
# Line 150
use_dml = accelerator_options.device == AcceleratorDevice.AUTO

# Lines 228-239
params = {
    "Det.use_cuda": use_cuda,
    "Det.use_dml": use_dml,
    "Cls.use_cuda": use_cuda,
    "Cls.use_dml": use_dml,
    "Rec.use_cuda": use_cuda,
    "Rec.use_dml": use_dml,
}
```

RapidOCR's `ProviderConfig` class (`rapidocr/inference_engine/onnxruntime/provider_config.py`) checks for `DmlExecutionProvider` in `onnxruntime.get_available_providers()` when `use_dml=True`.

**Conclusion:** On Windows with `onnxruntime-directml` installed, RapidOCR will automatically use DirectML when `device=AUTO`.

### 3.2 Layout Detection — Hardcoded CPU/CUDA

**Source:** `docling/models/inference_engines/object_detection/onnxruntime_engine.py`

```python
def _resolve_providers(self) -> List[str]:
    configured_providers = self.options.providers or ["CPUExecutionProvider"]
    if configured_providers != ["CPUExecutionProvider"]:
        return configured_providers

    device = decide_device(
        self._accelerator_options.device,
        supported_devices=[AcceleratorDevice.CPU, AcceleratorDevice.CUDA],
    )

    if device.startswith("cuda"):
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]
    return ["CPUExecutionProvider"]
```

**Key issue:** `supported_devices=[AcceleratorDevice.CPU, AcceleratorDevice.CUDA]` explicitly excludes any other provider. Even if you set `device=AUTO` and have DirectML available, `decide_device()` will return `"cpu"` because CUDA is not present, and the function falls back to `CPUExecutionProvider`.

The same pattern exists in:
- `image_classification/onnxruntime_engine.py` (same `_resolve_providers` logic)

### 3.3 Device Selection Logic — No AMD Awareness

**Source:** `docling/utils/accelerator_utils.py`

```python
def decide_device(accelerator_device: str, supported_devices=None) -> str:
    import torch
    device = "cpu"
    has_cuda = torch.backends.cuda.is_built() and torch.cuda.is_available()
    has_mps = torch.backends.mps.is_built() and torch.backends.mps.is_available()
    has_xpu = hasattr(torch, "xpu") and torch.xpu.is_available()

    if accelerator_device == AcceleratorDevice.AUTO.value:
        if has_cuda:
            device = "cuda:0"
        elif has_mps:
            device = "mps"
        elif has_xpu:
            device = "xpu"
        # else: stays "cpu"
```

**No AMD/ROCm/DirectML/XPU path exists.** The function only knows about CUDA, MPS, and Intel XPU.

### 3.4 TableFormer — PyTorch-Based, DirectML Untested

**Source:** `docling/models/stages/table_structure/table_structure_model.py`

```python
from docling_ibm_models.tableformer.data_management.tf_predictor import TFPredictor
self.tf_predictor = TFPredictor(self.tm_config, device, accelerator_options.num_threads)
```

TableFormer uses `docling_ibm_models` which is a PyTorch model. On Windows, PyTorch can use DirectML via `torch-directml`, but:
1. `torch-directml` is not a dependency of docling.
2. Compatibility with `docling_ibm_models` is **untested**.
3. The model loads weights and runs inference via custom PyTorch code; there is no guarantee it works with DirectML tensors.

---

## 4. Benchmark Baseline (CPU on WSL2)

For reference, the 5-PDF benchmark run on this machine (all CPU):

| Extractor | Total Time | ms/page | Chars | vs PyMuPDF |
|-----------|-----------|---------|-------|------------|
| PyMuPDF | 0.09s | 1.5ms | 54,163 | 1.0× |
| PyMuPDF4LLM | 10.60s | 179.7ms | 60,953 | 121× |
| **docling** | **158.51s** | **2,686ms** | **86,169** | **1,809×** |

Docling extracts **59% more text** than PyMuPDF (tables, structure, headings) but is ~1,800× slower. The bottleneck is layout detection and OCR inference on CPU.

---

## 5. Hypothetical Windows + DirectML Scenario

### 5.1 What Would Work Out of the Box

If you installed docling on native Windows with `onnxruntime-directml`:

| Component | Would Use DirectML? | Expected Speedup on 780M |
|-----------|---------------------|-------------------------|
| RapidOCR text detection | ✅ Yes | 1.5–3× |
| RapidOCR text recognition | ✅ Yes | 1.5–3× |
| Layout detection (heron) | ❌ No (hardcoded) | 1.0× (CPU) |
| Image classification | ❌ No (hardcoded) | 1.0× (CPU) |
| TableFormer | ❌ No (PyTorch, needs torch-directml) | 1.0× (CPU) |

**Overall impact:** Since layout detection is typically the most expensive stage, the total pipeline speedup would likely be **< 20%**, not worth the OS migration.

### 5.2 How to Enable RapidOCR DirectML on Windows

```powershell
# 1. Install onnxruntime-directml (replaces CPU-only package)
pip uninstall onnxruntime onnxruntime-gpu
pip install onnxruntime-directml

# 2. Verify provider availability
python -c "import onnxruntime; print(onnxruntime.get_available_providers())"
# Expected: ['DmlExecutionProvider', 'CPUExecutionProvider']

# 3. Run docling with AUTO device
# docling will automatically set use_dml=True when device=AUTO
```

### 5.3 What It Would Take to Enable Layout DirectML

To make layout detection use DirectML, you would need to **patch docling's source code** or **monkey-patch at runtime**:

```python
# Monkey-patch approach (experimental, fragile)
from docling.datamodel.object_detection_engine_options import OnnxRuntimeObjectDetectionEngineOptions

# Override the default providers before docling initializes the pipeline
OnnxRuntimeObjectDetectionEngineOptions.providers = ["DmlExecutionProvider", "CPUExecutionProvider"]
```

However, this is **not officially supported** and may:
- Fail with unsupported ONNX ops on DirectML.
- Produce incorrect inference results.
- Be slower than CPU due to iGPU memory bandwidth limitations.

---

## 6. Key Findings

| # | Finding | Implication |
|---|---------|-------------|
| 1 | ROCm is not supported on Radeon 780M iGPU | No Linux GPU acceleration path exists |
| 2 | RapidOCR already supports DirectML on Windows | OCR could be ~2× faster on Windows |
| 3 | Layout detection models are hardcoded to CPU/CUDA | The most expensive stage stays on CPU |
| 4 | `decide_device()` knows nothing about AMD/DirectML | Even with DirectML installed, docling defaults to CPU for non-OCR stages |
| 5 | TableFormer uses PyTorch, not ONNX | Requires `torch-directml` (untested with docling) |
| 6 | Radeon 780M is an iGPU with limited bandwidth | Even if all models used DirectML, speedup would be modest, not 6–10× |

---

## 7. Recommendations

### 7.1 Short Term (Current Setup)

- **Stay on WSL2 + CPU.** The file system and networking integration is simpler.
- **Optimize CPU settings:**
  ```bash
  export DOCLING_NUM_THREADS=16        # Use all threads
  export OMP_NUM_THREADS=16
  export OPENBLAS_NUM_THREADS=16
  ```
- **Use the singleton converter** (`ingest/docling_utils.py`) to avoid model reload overhead.
- **Consider `TableFormerMode.FAST`** instead of `ACCURATE` for table extraction if speed is critical.

### 7.2 Medium Term (If You Acquire Discrete AMD GPU)

- If you upgrade to a discrete AMD GPU (e.g., RX 7900 XT/XTX):
  - **ROCm on Linux** becomes viable.
  - Docling would need to add ROCm support to `decide_device()` and layout model providers.
  - This is an **upstream docling feature request**, not a local patch.

### 7.3 Long Term (If You Must Use Windows)

- If you migrate ingestion to native Windows for other reasons (IDE, file I/O):
  1. Install `onnxruntime-directml` to get OCR acceleration.
  2. Accept that layout and table models remain CPU-bound.
  3. Monitor docling releases for official DirectML support in layout models.

---

## 8. References

- Docling source (installed in `.venv/lib/python3.13/site-packages/docling/`):
  - `models/stages/ocr/rapid_ocr_model.py`
  - `models/inference_engines/object_detection/onnxruntime_engine.py`
  - `models/inference_engines/image_classification/onnxruntime_engine.py`
  - `models/stages/table_structure/table_structure_model.py`
  - `utils/accelerator_utils.py`
- RapidOCR source:
  - `rapidocr/inference_engine/onnxruntime/provider_config.py`
- AMD ROCm supported GPUs: https://rocm.docs.amd.com/en/latest/release/gpu_os_support.html
- ONNX Runtime DirectML: https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html

---

## 9. Document History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-28 | OpenCode | Initial research based on docling 2.96.0 source analysis and WSL2 environment audit |
