import logging
import os
import sys
import torch
import transformers
from argparse import ArgumentParser
# from pretrain.arguments import DataTrainingArguments, ModelArguments
# from pretrain.data import DatasetForPretraining, RetroMAECollator, DupMAECollator
# from pretrain.modeling import RetroMAEForPretraining
# from pretrain.modeling_duplex import DupMAEForPretraining
# from pretrain.trainer import PreTrainer

from arguments import DataTrainingArguments, ModelArguments
from data import DatasetForPretraining, RetroMAECollator, DupMAECollator
from modeling import RetroMAEForPretraining
from modeling_duplex import DupMAEForPretraining
from trainer import PreTrainer
from transformers import BertConfig, BertModel
import json

from transformers import (
    AutoTokenizer,
    BertForMaskedLM,
    AutoConfig,
    HfArgumentParser, set_seed, )
from transformers import (
    TrainerCallback,
    TrainingArguments,
    TrainerState,
    TrainerControl
)
from transformers.trainer_utils import is_main_process

logger = logging.getLogger(__name__)

class TrainerCallbackForSaving(TrainerCallback):
    def on_epoch_end(self, args: TrainingArguments, state: TrainerState, control: TrainerControl, **kwargs):
        """
        Event called at the end of an epoch.
        """
        control.should_save = True


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = torch.argmax(torch.tensor(logits), dim=-1)
    labels = torch.tensor(labels)
    accuracy = (predictions == labels).float().mean()
    return {"accuracy": accuracy.item()}


# def main():
if __name__ == "__main__":
    parser = HfArgumentParser((ModelArguments, DataTrainingArguments, TrainingArguments))
    if len(sys.argv) == 2 and sys.argv[1].endswith(".json"):
        # If we pass only one argument to the script and it's the path to a json file,
        # let's parse it to get our arguments.
        model_args, data_args, training_args = parser.parse_json_file(json_file=os.path.abspath(sys.argv[1]))
    else:
        model_args, data_args, training_args = parser.parse_args_into_dataclasses()
 

    model_args: ModelArguments
    data_args: DataTrainingArguments
    training_args: TrainingArguments

    training_args.remove_unused_columns = False

    # Setup logging
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(name)s -   %(message)s",
        datefmt="%m/%d/%Y %H:%M:%S",
        level=logging.INFO if is_main_process(training_args.local_rank) else logging.WARN,
    )

    # Log on each process the small summary:
    logger.warning(
        f"Process rank: {training_args.local_rank}, device: {training_args.device}, n_gpu: {training_args.n_gpu}"
        + f"distributed training: {bool(training_args.local_rank != -1)}, 16-bits training: {training_args.fp16}"
    )
    # Set the verbosity to info of the Transformers logger (on main process only):
    if is_main_process(training_args.local_rank):
        transformers.utils.logging.set_verbosity_info()
        transformers.utils.logging.enable_default_handler()
        transformers.utils.logging.enable_explicit_format()
    if training_args.local_rank in (0, -1):
        logger.info("Training/evaluation parameters %s", training_args)
        logger.info("Model parameters %s", model_args)
        logger.info("Data parameters %s", data_args)
    

    set_seed(training_args.seed)

    # initialize the model
    if model_args.pretrain_method == 'retromae':
        model_class = RetroMAEForPretraining
        collator_class = RetroMAECollator
    elif model_args.pretrain_method == 'dupmae':
        model_class = DupMAEForPretraining
        collator_class = DupMAECollator
    else:
        raise NotImplementedError

    print("model_args.model_type: ", model_args.model_type)
    
    model_args.model_name_or_path = f"models/atlasv2_model_{model_args.model_type}"
    print(model_args.model_name_or_path)


    if model_args.model_name_or_path:

        # load a pretrain model
        model = model_class.from_pretrained(model_args, model_args.model_name_or_path)
        model.c_head.load_state_dict(torch.load(os.path.join(model_args.model_name_or_path, 'c_head.pth')))
        print(model.lm.bert.encoder.layer[0].output.dense.weight)
        print(model.c_head.output.dense.weight)
   

        logger.info(f"------Load model from {model_args.model_name_or_path}------")
        tokenizer = AutoTokenizer.from_pretrained(model_args.model_name_or_path)
       
    elif model_args.config_name:
        # or train a new model
        config = AutoConfig.from_pretrained(model_args.config_name)
        bert = BertForMaskedLM(config)
        model = model_class(bert, model_args)
        logger.info("------Init the model------")
        tokenizer = AutoTokenizer.from_pretrained(data_args.tokenizer_name)
    else:
        raise ValueError("You must provide the model_name_or_path or config_name")

    dataset = DatasetForPretraining(data_args.data_dir)
    print("-----------------------print data ----------------------")
    print(dataset[0])
    print(dataset[1])
    print(dataset[2])

    data_collator = collator_class(tokenizer,
                                     encoder_mlm_probability=data_args.encoder_mlm_probability,
                                     decoder_mlm_probability=data_args.decoder_mlm_probability,
                                     max_seq_length=data_args.max_seq_length)
    print("-----------------------data_collator-----------------------")
    print(data_collator)
     
   
     
    trainer = PreTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        eval_dataset=dataset,   
        data_collator=data_collator,
        tokenizer=tokenizer
    )

    
    from torch.utils.data import DataLoader
    # load data in batches 
    dataloader = DataLoader(
        dataset, 
        batch_size= 16,   
        shuffle=False, 
        collate_fn=data_collator   
    )
    print("-----------------------dataloader-----------------------")
    print(dataloader)
     

    embeddings = {}
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


    for batch in dataloader:
        # inputs = {key: value.cuda() for key, value in batch.items()}
        if 'encoder_input_ids' in batch:
            print("Shape of encoder_input_ids:", batch['encoder_input_ids'].shape)

        inputs = {key: value.to(device) if isinstance(value, torch.Tensor) else value for key, value in batch.items()}
        outputs = model(**inputs)
        loss =outputs[0]
        sentence_emb = outputs[1]  
         
        process_cmd_ids = batch['process_cmd_ids']
         
        for i, process_cmd_id in enumerate(process_cmd_ids):
             
            embedding = sentence_emb[i].cpu().detach().numpy().tolist()   
            embeddings[str(process_cmd_id)] = embedding             
        

    print("len embedding: ", len(embeddings))

    # Define the path
    file_path = f"mae/embedding_data/train_trace_{data_args.data}_{model_args.model_type}.json"
    folder_path = os.path.dirname(file_path)

    # Create folder if it does not exist
    os.makedirs(folder_path, exist_ok=True)

    # Write the embeddings to JSON
    with open(file_path, "w") as f:
        json.dump(embeddings, f)
    
