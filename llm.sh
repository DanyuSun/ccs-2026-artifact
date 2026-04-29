# -----------------------------  building RAG -----------------------------

start=$(date +%s)

echo "Running ..."

python src/atlasv2_rag.py \
    -input_dir data/atlasv2/benign/edr-h1-benign.csv \
    -output_filename  data/atlasv2-profiles.json \



python src/atlasv2_rag_representive_sampling.py \
    -input_file  data/atlasv2-profiles.json \
    -condensed_file  data/atlasv2-profiles-condensed.json

end=$(date +%s)
echo "Total runtime: $((end - start)) seconds"

# -----------------------------  Log partition -----------------------------

attack="s1"
model="r1" ## you can choose from {o3-mini, r1, llama, sonar}

python src/generate_prompt.py \
        -attack ${attack}\
        -model ${model}

start=$(date +%s)

echo "Running ..."

python src/atlasv2_log_filter-${model}.py \
    -input_file "data/atlasv2/attack/edr-h1-${attack}-attack.csv" \
    -output_file "filtered/${attack}/filtered_logs_${attack}_${model}.csv" \
    -profiles_file "data/atlasv2-profiles-condensed.json" \
    -output_profiles_file "filtered/${attack}/filtered-profiles_${attack}.json"  \
    -k 2 \
    -attack $attack
 

end=$(date +%s)
echo "Total runtime: $((end - start)) seconds"

# ----------------------------- LLM part -----------------------------

start=$(date +%s)

echo "Running ..."
 
python src/llm_prompt.py \
    -base_dir  "" \
    -attack  ${attack} \
    -model ${model}

end=$(date +%s)
echo "Total runtime: $((end - start)) seconds"
