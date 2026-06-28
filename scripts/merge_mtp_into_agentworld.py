#!/usr/bin/env python3
"""
Merges BF16 MTP head tensors from nvidia/Qwen3.6-35B-A3B-NVFP4 into
sakamakismile/Qwen-AgentWorld-35B-A3B-NVFP4.

The AgentWorld fine-tune lost its MTP weights during training. This script
copies them from the Qwen3.6 base model (same architecture), allowing
vLLM MTP speculative decoding to work.

Original AgentWorld weights are backed up to <snapshot_dir>.orig_backup/
before any modification.
"""

import json
import shutil
import sys
from pathlib import Path

try:
    import safetensors
    from safetensors import safe_open
    from safetensors.torch import save_file
    import torch
except ImportError:
    print("ERROR: Install dependencies: pip install safetensors torch")
    sys.exit(1)


HF_CACHE = Path("/home/lmanrique/Do/ai-server/vllm/models/hub")

AGENTWORLD_REPO = "models--sakamakismile--Qwen-AgentWorld-35B-A3B-NVFP4"
NVIDIA_REPO     = "models--nvidia--Qwen3.6-35B-A3B-NVFP4"


def latest_snapshot(repo_dir: Path) -> Path:
    snapshots = list((repo_dir / "snapshots").iterdir())
    if not snapshots:
        raise FileNotFoundError(f"No snapshots in {repo_dir}")
    return max(snapshots, key=lambda p: p.stat().st_mtime)


def iter_safetensors(snapshot: Path):
    """Yield (path, key, tensor) for every key in every safetensors shard."""
    index_file = snapshot / "model.safetensors.index.json"
    if index_file.exists():
        with open(index_file) as f:
            index = json.load(f)
        shards = set(index["weight_map"].values())
        for shard_name in sorted(shards):
            shard = snapshot / shard_name
            with safe_open(shard, framework="pt", device="cpu") as st:
                for key in st.keys():
                    yield shard, key, st.get_tensor(key)
    else:
        # Single-file model
        shard = snapshot / "model.safetensors"
        with safe_open(shard, framework="pt", device="cpu") as st:
            for key in st.keys():
                yield shard, key, st.get_tensor(key)


def main():
    aw_dir    = HF_CACHE / AGENTWORLD_REPO
    nvidia_dir = HF_CACHE / NVIDIA_REPO

    if not aw_dir.exists():
        print(f"ERROR: AgentWorld not found at {aw_dir}")
        sys.exit(1)
    if not nvidia_dir.exists():
        print(f"ERROR: nvidia model not found at {nvidia_dir}")
        print("Download it first:")
        print("  HF_HOME=./vllm/models huggingface-cli download nvidia/Qwen3.6-35B-A3B-NVFP4")
        sys.exit(1)

    aw_snap    = latest_snapshot(aw_dir)
    nvidia_snap = latest_snapshot(nvidia_dir)

    print(f"AgentWorld snapshot : {aw_snap}")
    print(f"nvidia snapshot     : {nvidia_snap}")

    # ── Backup original AgentWorld snapshot ──────────────────────────────────
    backup_dir = aw_snap.parent / f"{aw_snap.name}.orig_backup"
    if not backup_dir.exists():
        print(f"\nBacking up original to {backup_dir} ...")
        shutil.copytree(aw_snap, backup_dir, symlinks=True)
        print("Backup done.")
    else:
        print(f"\nBackup already exists at {backup_dir}, skipping.")

    # ── Collect MTP tensors from nvidia model ─────────────────────────────────
    print("\nScanning nvidia model for MTP tensors ...")
    mtp_tensors: dict[str, torch.Tensor] = {}
    for _shard, key, tensor in iter_safetensors(nvidia_snap):
        if "mtp" in key.lower():
            mtp_tensors[key] = tensor

    if not mtp_tensors:
        print("ERROR: No MTP tensors found in nvidia model.")
        print("Keys in first shard (first 20):")
        for i, (_s, k, _t) in enumerate(iter_safetensors(nvidia_snap)):
            print(f"  {k}")
            if i >= 19:
                break
        sys.exit(1)

    print(f"Found {len(mtp_tensors)} MTP tensors:")
    for k, t in sorted(mtp_tensors.items()):
        print(f"  {k}  {t.dtype}  {list(t.shape)}")

    # ── Write MTP tensors into AgentWorld snapshot ────────────────────────────
    mtp_shard_path = aw_snap / "model_mtp_head.safetensors"
    print(f"\nWriting MTP tensors to {mtp_shard_path} ...")
    save_file(mtp_tensors, mtp_shard_path)
    print("Written.")

    # ── Update / create model.safetensors.index.json ─────────────────────────
    index_file = aw_snap / "model.safetensors.index.json"
    if index_file.exists():
        with open(index_file) as f:
            index = json.load(f)
    else:
        # Single-file model — build an index from scratch
        print("Single-shard model; building index.json ...")
        weight_map = {}
        with safe_open(aw_snap / "model.safetensors", framework="pt", device="cpu") as st:
            for key in st.keys():
                weight_map[key] = "model.safetensors"
        index = {"metadata": {"total_size": 0}, "weight_map": weight_map}

    for key in mtp_tensors:
        index["weight_map"][key] = "model_mtp_head.safetensors"

    with open(index_file, "w") as f:
        json.dump(index, f, indent=2)
    print(f"Updated {index_file}")

    # ── Patch config.json to declare MTP architecture ─────────────────────────
    aw_config_path     = aw_snap / "config.json"
    nvidia_config_path = nvidia_snap / "config.json"

    with open(aw_config_path) as f:
        aw_cfg = json.load(f)
    with open(nvidia_config_path) as f:
        nv_cfg = json.load(f)

    mtp_keys = [k for k in nv_cfg if "mtp" in k.lower()]
    print(f"\nMTP config keys from nvidia: {mtp_keys}")

    changed = False
    for k in mtp_keys:
        if k not in aw_cfg or aw_cfg[k] != nv_cfg[k]:
            print(f"  config: {k} = {nv_cfg[k]}")
            aw_cfg[k] = nv_cfg[k]
            changed = True

    # Also set architecture to MTP variant if nvidia model uses it
    nv_arch = nv_cfg.get("architectures", [])
    if nv_arch and nv_arch != aw_cfg.get("architectures"):
        print(f"  config: architectures = {nv_arch}")
        aw_cfg["architectures"] = nv_arch
        changed = True

    if changed:
        # Backup config before patching
        shutil.copy2(aw_config_path, aw_config_path.with_suffix(".json.orig"))
        with open(aw_config_path, "w") as f:
            json.dump(aw_cfg, f, indent=2)
        print(f"Updated {aw_config_path}")
    else:
        print("config.json already has correct MTP fields, no change needed.")

    print("\nDone! Now restart qwen-agentworld with:")
    print('  --speculative-config \'{"method":"mtp","num_speculative_tokens":3}\'')


if __name__ == "__main__":
    main()
