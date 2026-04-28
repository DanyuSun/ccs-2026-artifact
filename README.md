# CCS-2026-#1547

## Introduction

This codebase reproduces the results of Shield, the proposed host-based intrusion detection system (HIDS). The detection pipeline consists of three stages: (1) data preprocessing, (2) event-level MAE–based attack window identification, and (3) LLM-based intrusion detection that generates structured attack narratives. In addition, the framework provides evaluation at the event, tactic, and story levels to comprehensively assess detection performance.


## Experimental setup

1. Download dataset.

    DARPA-E3: [here](https://drive.google.com/drive/folders/1QlbUFWAGq3Hpl8wVdzOdIoZLFxkII4EK). 
    
    ATLASV2: [here](https://bitbucket.org/sts-lab/atlasv2/src/master/).

    NL-SD: [here](https://github.com/PKU-ASAL/Simulated-Data).

    Save all downloaded datasets under the folder:

        ./data/

2. Install dependencies.

        pip install -r requirements.txt

3. Set your API key.
    
    Replace the placeholder in the code with your API key.


## Usage

The following scripts reproduce the results of Shield on ATLAS-v2-s1 subdataset. Also, we provide one result of s1 using deepseek-r1 model in the folder `/example_result/`. For other subdatasets of ATLAS-v2 and additional benchmarks (e.g., DARPA-R, Nodlink), the same pipeline can be applied to reproduce the results.

1. Preprocess the dataset.
        
        bash preprocess.sh

2. Run event-level MAE for attack window identification.

        bash mae.sh

3. Run two-stage attack investigation for fine-grained intrusion detection.

        bash llm.sh

4. Evaluate the results at three levels: event, tactic, and story.

        bash evaluation.sh

