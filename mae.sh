SUFFIXES="base"

# nohup python run.py   --output_dir "mae/models/atlasv2_model_$SUFFIXES"   \
#                 --data_dir "mae/pretrain_data/benign_atlasv2" \
#                 --do_train True   --save_steps 20000   \
#                 --per_device_train_batch_size 128   \
#                 --max_seq_length 30   \
#                 --model_name_or_path Shitao/RetroMAE  \
#                 --fp16 True   \
#                 --warmup_ratio 0.1   \
#                 --learning_rate 1e-4   \
#                 --num_train_epochs 20   \
#                 --overwrite_output_dir True   \
#                 --dataloader_num_workers 6   \
#                 --weight_decay 0.01   \
#                 --encoder_mlm_probability 0.3   \
#                 --decoder_mlm_probability 0.5 > ./logs/train_atlasv2_$SUFFIXES.log

DATA="s1"

# python mae/run_test.py --data_dir "mae/pretrain_data/$DATA" --data "$DATA" --model_type "$SUFFIXES" --output_dir "mae/test"
python mae/mae_result.py --data "$DATA"
 
