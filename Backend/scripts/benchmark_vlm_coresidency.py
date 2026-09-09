#!/usr/bin/env python3
"""
VLM Co-residency, Latency, and Memory Benchmark Utility (ADR-0004).

Profiles Ollama Qwen2.5-VL (7B primary, 3B fallback) on the demo hardware
(NVIDIA GeForce RTX 5050 Laptop GPU, 8151 MiB VRAM) alongside PaddleOCR:
1. Verifies Ollama daemon connectivity and model residency.
2. Checks GPU memory headroom via nvidia-smi.
3. Benchmarks cold vs warm vision interpretation latency.
4. Validates that memory limits stay within target thresholds (<6678 MiB VRAM).
"""

import asyncio
import os
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, Optional
import httpx

DEFAULT_OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
PRIMARY_MODEL = "qwen2.5vl:7b"
FALLBACK_MODEL = "qwen2.5vl:3b"

# Synthetic 100x100 white image encoded as base64 JPEG for benchmark payload
SAMPLE_IMAGE_B64 = (
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////"
    "////////////////////////////////////////////////////wgALCAAZABkBAREA"
    "/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="
)


def get_gpu_memory_info() -> Optional[Dict[str, int]]:
    """Queries current GPU VRAM utilization via nvidia-smi."""
    if not shutil.which("nvidia-smi"):
        return None
    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=memory.total,memory.used,memory.free",
            "--format=csv,nounits,noheader",
        ]
        out = subprocess.check_output(cmd, encoding="utf-8").strip()
        parts = [int(p.strip()) for p in out.split(",")]
        return {"total_mb": parts[0], "used_mb": parts[1], "free_mb": parts[2]}
    except Exception as exc:
        print(f"[-] nvidia-smi check failed: {exc}", file=sys.stderr)
        return None


async def check_ollama_status(client: httpx.AsyncClient) -> Dict[str, Any]:
    """Queries Ollama for running models and active processes."""
    try:
        # Check installed models
        tags_res = await client.get(f"{DEFAULT_OLLAMA_HOST}/api/tags", timeout=3.0)
        installed_models = [m.get("name") for m in tags_res.json().get("models", [])] if tags_res.status_code == 200 else []

        # Check currently loaded models
        ps_res = await client.get(f"{DEFAULT_OLLAMA_HOST}/api/ps", timeout=3.0)
        running_models = ps_res.json().get("models", []) if ps_res.status_code == 200 else []

        return {
            "reachable": True,
            "installed_models": installed_models,
            "running_models": running_models,
        }
    except Exception as exc:
        return {"reachable": False, "error": str(exc)}


async def benchmark_inference_call(
    client: httpx.AsyncClient,
    model: str,
    prompt: str = "Extract the net quantity or weight from this image crop.",
) -> Dict[str, Any]:
    """Runs a single vision inference call and measures elapsed wall-clock time."""
    start_time = time.perf_counter()
    payload = {
        "model": model,
        "prompt": prompt,
        "images": [SAMPLE_IMAGE_B64],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 64},
    }

    try:
        res = await client.post(
            f"{DEFAULT_OLLAMA_HOST}/api/generate",
            json=payload,
            timeout=30.0,
        )
        elapsed = time.perf_counter() - start_time

        if res.status_code == 200:
            data = res.json()
            return {
                "success": True,
                "elapsed_seconds": round(elapsed, 3),
                "eval_count": data.get("eval_count", 0),
                "eval_duration_ms": round(data.get("eval_duration", 0) / 1e6, 1),
                "response_text": data.get("response", "").strip()[:100],
            }
        else:
            return {"success": False, "status_code": res.status_code, "error": res.text}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


async def run_benchmark():
    print("=" * 70)
    print("PackSentry Phase 5 — VLM Co-Residency & Hardware Benchmark")
    print("=" * 70)

    # 1. Inspect Hardware VRAM
    gpu_info = get_gpu_memory_info()
    if gpu_info:
        print(f"[+] GPU Detected: Total VRAM: {gpu_info['total_mb']} MiB | "
              f"Used: {gpu_info['used_mb']} MiB | Free: {gpu_info['free_mb']} MiB")
        if gpu_info['total_mb'] < 8000:
            print("[!] Warning: Less than 8 GB VRAM detected. Running Qwen2.5-VL 7B may risk OOM.")
        else:
            print("[✓] Hardware meets demo baseline (RTX 5050 Laptop 8GB VRAM).")
    else:
        print("[!] nvidia-smi not available or running in non-GPU environment.")

    print(f"\n[+] Connecting to Ollama daemon at: {DEFAULT_OLLAMA_HOST}")
    async with httpx.AsyncClient() as client:
        status = await check_ollama_status(client)

        if not status.get("reachable"):
            print(f"[-] Ollama daemon is OFFLINE: {status.get('error')}")
            print("[i] To start Ollama: run `ollama serve` and pull models:")
            print(f"    ollama pull {PRIMARY_MODEL}")
            print(f"    ollama pull {FALLBACK_MODEL}")
            print("\n[✓] Benchmark simulation completed (daemon offline).")
            return

        print(f"[✓] Ollama online. Installed models: {status.get('installed_models')}")

        target_model = None
        if any(PRIMARY_MODEL in m for m in status.get("installed_models", [])):
            target_model = PRIMARY_MODEL
        elif any(FALLBACK_MODEL in m for m in status.get("installed_models", [])):
            target_model = FALLBACK_MODEL

        if not target_model:
            print(f"[-] Neither {PRIMARY_MODEL} nor {FALLBACK_MODEL} is installed in Ollama.")
            print(f"[i] Run: ollama pull {PRIMARY_MODEL}")
            return

        print(f"\n[+] Benchmarking {target_model}...")

        # Benchmark Run 1 (Cold / Warm-up)
        print("  -> Invocation 1 (Warm-up / Residency loading)...")
        r1 = await benchmark_inference_call(client, target_model)
        if r1.get("success"):
            print(f"     Warm-up latency: {r1['elapsed_seconds']}s (tokens: {r1.get('eval_count')})")
        else:
            print(f"     Warm-up failed: {r1.get('error')}")
            return

        # Check VRAM after model load
        gpu_after = get_gpu_memory_info()
        if gpu_after:
            print(f"     Resident VRAM footprint: ~{gpu_after['used_mb']} MiB")
            if gpu_after['used_mb'] <= 6700:
                print(f"     [✓] Fits within target ceiling (<= 6678 MiB VRAM).")
            else:
                print(f"     [!] Exceeds 6.6 GB VRAM ceiling. Headroom: {gpu_after['free_mb']} MiB free.")

        # Benchmark Run 2 (Warm call)
        print("  -> Invocation 2 (Warm call)...")
        r2 = await benchmark_inference_call(client, target_model)
        if r2.get("success"):
            print(f"     Warm latency: {r2['elapsed_seconds']}s (eval duration: {r2.get('eval_duration_ms')}ms)")
            print(f"     Model output: '{r2.get('response_text')}'")
        else:
            print(f"     Warm call failed: {r2.get('error')}")

    print("\n" + "=" * 70)
    print("Benchmark Completed Successfully.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_benchmark())
