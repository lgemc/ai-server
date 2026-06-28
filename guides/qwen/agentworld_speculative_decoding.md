# MTP Speculative Decoding for Qwen-AgentWorld-35B-A3B-NVFP4

Enables ~1.7–1.9× decode speedup via Multi-Token Prediction (MTP) speculative decoding on the `sakamakismile/Qwen-AgentWorld-35B-A3B-NVFP4` model.

## Background

The AgentWorld NVFP4 fine-tune lost its MTP weights during training — they were never saved to the checkpoint. The base `Qwen/Qwen3.6-35B-A3B` model architecture supports MTP, so the weights can be borrowed from any compatible Qwen3.6-35B NVFP4 model that ships with them.

Additionally, the AgentWorld `config.json` was missing the `re:^mtp.*` entry in `quantization_config.ignore`, which caused vLLM's compressed-tensors handler to apply NVFP4 quantization to the MTP head. This made the internal parameter names mismatch the BF16 disk tensors, crashing with:

```
KeyError: 'layers.0.mlp.experts.routed_experts.w2_weight'
```

The working `RedHatAI/Qwen3.6-35B-A3B-NVFP4` model has both the MTP tensors and the ignore entry, which is why it works out of the box.

## What Was Done

### 1. Download the donor model

`nvidia/Qwen3.6-35B-A3B-NVFP4` ships with its MTP head in BF16 (unquantized) inside the main checkpoint. Download it so vLLM can cache it locally:

```bash
sudo HF_HOME=/home/lmanrique/Do/ai-server/vllm/models \
  /home/lmanrique/miniconda3/bin/hf download nvidia/Qwen3.6-35B-A3B-NVFP4
```

> Note: `sudo` is required because `vllm/models/hub/` is root-owned (written by Docker containers).
> Use the full path to `hf` since it's not in root's PATH.

### 2. Merge MTP tensors into AgentWorld

The script `scripts/merge_mtp_into_agentworld.py`:

- Backs up the original AgentWorld snapshot to `<hash>.orig_backup/` before touching anything
- Extracts all 19 `mtp.*` tensors (BF16) from the nvidia model
- Writes them to `model_mtp_head.safetensors` in the AgentWorld snapshot
- Creates `model.safetensors.index.json` pointing to both the original shard and the new MTP shard

```bash
sudo /home/lmanrique/miniconda3/bin/python3 \
  /home/lmanrique/Do/ai-server/scripts/merge_mtp_into_agentworld.py
```

### 3. Patch config.json to exclude MTP from quantization

Without this, vLLM applies NVFP4 compression to the MTP decoder layer, giving it different internal parameter names than the BF16 tensors on disk.

```bash
sudo /home/lmanrique/miniconda3/bin/python3 -c "
import json

path = '/home/lmanrique/Do/ai-server/vllm/models/hub/models--sakamakismile--Qwen-AgentWorld-35B-A3B-NVFP4/snapshots/1a5ef1e04df2e84554889b839a2d96a20773d15f/config.json'

with open(path) as f:
    cfg = json.load(f)

ignore = cfg['quantization_config']['ignore']
if 're:^mtp.*' not in ignore:
    ignore.append('re:^mtp.*')
    with open(path, 'w') as f:
        json.dump(cfg, f, indent=2)
    print('Patched.')
else:
    print('Already present.')
"
```

### 4. Enable speculative decoding in docker-compose.yml

Add to the `qwen-agentworld` service command (already done):

```yaml
--speculative-config '{"method":"mtp","num_speculative_tokens":3}'
```

### 5. Restart the service

```bash
docker compose up qwen-agentworld -d
```

## Rollback

The original AgentWorld weights are preserved at:
```
vllm/models/hub/models--sakamakismile--Qwen-AgentWorld-35B-A3B-NVFP4/snapshots/
  1a5ef1e04df2e84554889b839a2d96a20773d15f.orig_backup/
```

To rollback: restore the snapshot dir from the backup and remove `--speculative-config` from `docker-compose.yml`.

## Why This Works

| Model | MTP tensors | `re:^mtp.*` in ignore | MTP works |
|---|---|---|---|
| `RedHatAI/Qwen3.6-35B-A3B-NVFP4` | ✅ baked in (BF16) | ✅ | ✅ |
| `nvidia/Qwen3.6-35B-A3B-NVFP4` | ✅ baked in (BF16) | ✅ | ✅ |
| `sakamakismile/Qwen-AgentWorld-35B-A3B-NVFP4` (original) | ❌ missing | ❌ | ❌ |
| `sakamakismile/Qwen-AgentWorld-35B-A3B-NVFP4` (patched) | ✅ merged from nvidia | ✅ | ✅ |

The `re:^mtp.*` ignore entry tells compressed-tensors to leave MTP layers as BF16, so vLLM's `Qwen3_5MoeMTP` loader initializes the MTP module with standard (unquantized) parameter names that match the BF16 disk tensors.

## References

- [vLLM bug #43304](https://github.com/vllm-project/vllm/issues/43304) — MTP draft model inherits main model quant config (root cause)
- [sakamakismile/Qwen3.6-27B-Text-NVFP4-MTP](https://huggingface.co/sakamakismile/Qwen3.6-27B-Text-NVFP4-MTP) — reference for the MTP-embedded NVFP4 pattern
- `scripts/merge_mtp_into_agentworld.py` — merge script used in step 2
