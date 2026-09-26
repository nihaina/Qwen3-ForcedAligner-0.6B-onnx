# Qwen3-ForcedAligner-0.6B ONNX 导出脚本

将官方 [`Qwen/Qwen3-ForcedAligner-0.6B`](https://modelscope.cn/models/Qwen/Qwen3-ForcedAligner-0.6B) 权重导出为 ONNX，并与官方 PyTorch 推理结果比较。脚本适用于 `qwen-asr==0.0.6` 使用的原版权重；名称带 `-hf` 的 Transformers 原生权重采用另一套实现，不能直接用于本脚本。

## 准备环境

参考验证环境：Python 3.12.7、PyTorch 2.5.1+cpu、`qwen-asr` 0.0.6、Transformers 4.57.6、ONNX 1.22.0、ONNX Runtime 1.20.1。导出和验证均可在 CPU 上运行。

在仓库根目录创建并激活虚拟环境。PowerShell 使用 `.\.venv\Scripts\Activate.ps1`，Linux/macOS 使用 `source .venv/bin/activate`。

```text
python -m venv .venv
```

激活环境后执行：

```text
python -m pip install -r requirements.txt
python -m pip install modelscope
modelscope download --model Qwen/Qwen3-ForcedAligner-0.6B --local_dir build/official
```

`modelscope` 仅用于下载；也可以从官方仓库下载完整模型到 `build/official`。`build/` 和虚拟环境已加入 `.gitignore`。

## 导出

```text
python tools/export_qwen3_forced_aligner_onnx.py --model build/official --output build/forced_aligner.onnx
```

脚本先检查三组不同长度的输入与官方 PyTorch 模型是否一致，再导出动态音频/文本长度的图，写入外部 FP32 权重，并用 ONNX Runtime 对三组输入复验。默认 opset 为 18，batch 固定为 1。输出包括：

| 文件 | 用途 |
| --- | --- |
| `build/forced_aligner.onnx` | 模型图，约 7.76 MB |
| `build/forced_aligner.onnx.data` | 外部 FP32 权重，约 3.67 GB，须与模型图同目录并保持文件名 |
| `build/forced_aligner.validation.json` | 文件大小、SHA-256 和三组动态长度验证结果 |
| `build/parity_*.npz` | 验证输入与官方 PyTorch logits |
| `build/forced_aligner.graph.onnx` | 不含权重的中间图，不能单独推理 |

模型图有四个输入和一个输出：

| 名称 | 类型 | 形状 |
| --- | --- | --- |
| `input_ids` | int64 | `[1, sequence]` |
| `input_features` | float32 | `[1, 128, frames]` |
| `attention_mask` | int64 | `[1, sequence]` |
| `feature_attention_mask` | int64 | `[1, frames]` |
| `logits` | float32 | `[1, sequence, 5000]` |

分词和 log-mel 特征提取仍在模型图之外。音频特征掩码支持右侧补零，有效帧必须从第一帧连续排列。`<timestamp>` 的 token ID 为 151705，每个时间戳类别代表 80 ms。音频占位符须按官方处理器展开为以下数量：

```text
((valid_frames % 100 + 7) // 8) + (valid_frames // 100) * 13
```

## 用真实音频验证

提供音频、对应原文及语言，例如：

```text
python tools/verify_qwen3_forced_aligner_onnx.py --model build/official --onnx build/forced_aligner.onnx --audio path/to/audio.wav --text "你好世界" --language Chinese
```

脚本使用官方音频预处理、分词和占位符展开，比较官方模型、导出包装层及 ONNX Runtime 的 logits 与时间戳类别，并写出 `build/forced_aligner.audio-validation.json` 和对应的 `.npz` 输入。报告含音频路径和转录文本，公开分享前请检查。

参考验证使用了官方 4.204 秒中文样例：官方模型与导出包装层 logits 完全一致，ONNX 最大绝对误差约 `1.05e-5`，26 个时间戳类别均一致，解析出 13 个逐字时间段。该结果仅覆盖所用样例；脚本采用 FP32/eager 后端，未对 FlashAttention 2、量化模型或所有语言与长音频做等价性验证。

脚本来自 [SubtitleEditforAndroid](https://github.com/nihaina/SubtitleEditforAndroid) 的 Qwen3 强制对齐导出实现。

## 下载已导出的模型

在 [最新 Release](https://github.com/nihaina/Qwen3-ForcedAligner-0.6B-onnx/releases/latest) 下载全部 `forced_aligner-onnx-fp32.7z.001` 等分卷及 `SHA256SUMS.txt`，放在同一目录。安装 7-Zip 后，从第一卷解压：

```text
7z x forced_aligner-onnx-fp32.7z.001
```

也可在 Windows 中用 7-Zip 打开 `.001` 文件并解压。压缩包内含 `forced_aligner.onnx` 和 `forced_aligner.onnx.data`；推理时请将两者放在同一目录，保持文件名不变。`SHA256SUMS.txt` 列出了各分卷及解压后文件的校验值。分卷大小低于 GitHub Release 的单附件限制。
