python mae/atlasv2.py --file benign
python mae/atlasv2.py --file s1
python mae/preprocess.py --data atlasv2 --output_dir mae/pretrain_data/benign_atlasv2 --columns "base" --csv_path data/atlasv2/benign/edr-h1-benign-merge.csv
python mae/preprocess.py --data atlasv2 --output_dir pretrain_data/s1 --columns "base" --csv_path data/atlasv2/attack/edr-h1-s1-merge.csv