# Finetune policy

In order to finetune PI0 policy, prepare dataset in LeRobot format.

### Modify config with new dataset

In src/openpi/training/config.py modify config with new dataset name.

```python
    TrainConfig(
        name="pi05_positronic_lowmem",
        # Pi05 model with LoRA finetuning for low memory usage on Positronic dataset.
        model=pi0.Pi0Config(
            pi05=True,
            paligemma_variant="gemma_2b_lora",
            action_expert_variant="gemma_300m_lora",
        ),

        data=LeRobotPositronicDataConfig(
            repo_id="<PUT YOUR DATASET NAME HERE>",
            base_config=DataConfig(prompt_from_task=True),
        ),

```

### Compute norm stats

Run script to compute normalization stats for your dataset.

```bash
HF_LEROBOT_HOME="path/to/dataset" uv run scripts/compute_norm_stats.py --config-name pi05_positronic_lowmem
```

### Run train

Train policy.

```bash
HF_LEROBOT_HOME="path/to/dataset" XLA_PYTHON_CLIENT_MEM_FRACTION=0.995 uv run scripts/train.py pi05_positronic_lowmem --exp-name=<expriment_name> --overwrite
```

### Serve policy

After training you could find weights in `checkpoints/pi05_positronic_lowmem/<experiment name>/`. Run policy server with:

```bash
uv run scripts/serve_policy.py policy:checkpoint --policy.config=pi05_positronic_lowmem --policy.dir checkpoints/pi05_positronic_lowmem/<experiment name>/29999/
```

By default, the server is served from port 8000, so if you serve it on Nebius or other cloud provider, you need to have this port open:
```bash
ssh -L 8000:localhost:8000 <YOUR-MACHINE-IP>
```

Then on the local machine, you will run the inference script (from `positronic` repository root):
```bash
python -m positronic.run_inference sim_pi0 --output_dir=../datasets/inference/ --show_gui --num_iterations=10 --simulation_time=15
```

## Using Docker

### Build and Push Docker Image

Build and push the training image to Nebius Container Registry:

```bash
cd docker
make push
```

This will:
1. Build the Docker image with all source code baked in
2. Tag it with version, git SHA, and `latest`
3. Push to the Nebius registry at `cr.eu-north1.nebius.cloud/e00a0ahqzcp9x0xczz/openpi-training`

### Run Training in Docker

All commands can be run using the cloud Docker image. The code is already baked into the image, so no source code mounting is needed:

```bash
docker run --rm -it --gpus all --pull=always \
  -v /datasets:/datasets \
  -v /outputs:/outputs \
  cr.eu-north1.nebius.cloud/e00a0ahqzcp9x0xczz/openpi-training \
  <your command>
```

#### Docker Examples

**Compute norm stats:**
```bash
docker run --rm -it --gpus all --pull=always \
  -v /datasets:/datasets \
  -v /outputs/openpi/assets:/openpi/assets \
  -e HF_LEROBOT_HOME=/datasets/<path to your dataset> \
  cr.eu-north1.nebius.cloud/e00a0ahqzcp9x0xczz/openpi-training \
  python -m scripts.compute_norm_stats --config-name pi05_positronic_lowmem
```

**Run train:**
```bash
docker run --rm -it --gpus all --pull=always \
  -v /datasets:/datasets \
  -v /outputs/openpi/assets:/openpi/assets \
  -v /outputs/checkpoints:/openpi/checkpoints \
  -e HF_LEROBOT_HOME=/datasets/<path to your dataset> \
  cr.eu-north1.nebius.cloud/e00a0ahqzcp9x0xczz/openpi-training \
  python -m scripts.train pi05_positronic_lowmem --exp-name=<experiment_name>
```

**Serve policy:**
```bash
docker run --rm -it --gpus all --pull=always \
  -v /outputs/openpi/checkpoints:/openpi/checkpoints \
  -p 8000:8000 \
  cr.eu-north1.nebius.cloud/e00a0ahqzcp9x0xczz/openpi-training \
  python -m scripts.serve_policy policy:checkpoint \
    --policy.config=pi05_positronic_lowmem \
    --policy.dir=/openpi/checkpoints/pi05_positronic_lowmem/<experiment_name>/29999/
```

### Local Development (Optional)

For local development with live code editing, use `Dockerfile.training`:

```bash
docker build -f docker/Dockerfile.training -t openpi-training-dev .
docker run --rm -it --gpus all \
  -v $PWD:/openpi \
  -v /datasets:/datasets \
  openpi-training-dev \
  bash -lc 'uv pip install --no-deps -e /openpi && <your command>'
```