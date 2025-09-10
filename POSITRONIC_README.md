# Finetune policy

In order to finetune PI0 policy, prepare dataset in LeRobot format.

### Modify config with new dataset

In src/openpi/training/config.py modify config with new dataset name.

```python
    TrainConfig(
        name="pi0_positronic_lowmem",
        # Here is an example of loading a pi0-FAST model for LoRA finetuning.
        # For setting action_dim, action_horizon, and max_token_len, see the comments above.
        model=pi0.Pi0Config(paligemma_variant="gemma_2b_lora", action_expert_variant="gemma_300m_lora"),

        data=LeRobotPositronicDataConfig(
            repo_id="<PUT YOUR DATASET NAME HERE>",
            base_config=DataConfig(prompt_from_task=True),
        ),

```

### Compute norm stats

Run script to compute normalization stats for your dataset.

```bash
HF_LEROBOT_HOME="path/to/dataset" uv run scripts/compute_norm_stats.py --config-name pi0_positronic_lowmem
```

### Run train

Train policy.

```bash
HF_LEROBOT_HOME="path/to/dataset" XLA_PYTHON_CLIENT_MEM_FRACTION=0.995 uv run scripts/train.py pi0_positronic_lowmem --exp-name=<expriment_name> --overwrite
```

### Serve polciy

After training you could find weights in `checkpoints/pi0_positronic_lowmem/<experiment name>/`. Run policy server with:

```bash
uv run scripts/serve_policy.py policy:checkpoint --policy.config=pi0_positronic_lowmem --policy.dir checkpoints/pi0_positronic_lowmem/<experiment name>/29999/
```