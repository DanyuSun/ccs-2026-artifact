attack="s1"

nohup python src/evaluation_r1.py \
-data  "atlasv2" \
-attack  ${attack}  
 
nohup python src/eval_tactic.py \
-data  ${attack}  \
-model  r1

nohup python src/eval_story.py \
-attack  ${attack}  \
-model  r1
 
