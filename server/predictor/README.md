# modernbert_lenbucket

Predict output-token buckets (exponential buckets) using ModernBERT + SE (squeeze/excitation/recalibrate),
then map to inference time by a simple TPS model.

## Install
pip install -r requirements.txt

## Train
python train.py \
  --model_name answerdotai/ModernBERT-base \
  --dataset_name abinzzz/ForeLen \
  --output_dir ./ckpt_lenbucket \
  --max_length 2048 \
  --bucket_base 32 --bucket_max 2048 \
  --se_ratio 16 \
  --batch_size 8 \
  --lr 2e-5 \
  --epochs 1 \
  --train_size 200000 \
  --eval_size 20000 \
  --log_every 50 \
  --fp16

Training will print loss every log_every steps and eval metrics each epoch.
Checkpoints go to ./ckpt_lenbucket/epoch{N}

## Predict
python predict.py \
  --ckpt_dir ./ckpt_lenbucket/epoch1 \
  --prompt "请一步一步推导并给出详细解释，最后列出要点。" \
  --prefill_tps 8000 \
  --decode_tps 800 \
  --token_estimate upper \
  --p_quantile 0.9