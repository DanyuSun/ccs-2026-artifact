import random
from copy import deepcopy
from dataclasses import dataclass

import torch.utils.data.dataset
from datasets import Dataset
# from pretrain.utils import tensorize_batch
from utils import tensorize_batch
from transformers import DataCollatorForWholeWordMask

#  loading the dataset from disk and making it compatible with PyTorch's Dataset class.
class DatasetForPretraining(torch.utils.data.Dataset):
    def __init__(self, data_dir):
        self.dataset = Dataset.load_from_disk(data_dir)
        
        # for k in range(10):
        #     print(self.dataset['cmd'][k])
        #     print(self.dataset['token_ids'][k])
        #     print(tokenizer.decode(self.dataset['token_ids'][k]))
        # print(hhh)

    def __getitem__(self, item):
        return self.dataset[item]
    
    # def __getitem__(self, idx):
    #     return {
    #         'process_id': self.dataset.iloc[idx]['process_id'],  # Unique identifier
    #         'title': self.dataset.iloc[idx]['title'],  # Unique identifier
    #         'text': self.dataset.iloc[idx]['text']  # Text or tokenized data
    #     }

    def __len__(self):
        return len(self.dataset)


@dataclass
class RetroMAECollator(DataCollatorForWholeWordMask):
    max_seq_length: int = 512
    encoder_mlm_probability: float = 0.15
    decoder_mlm_probability: float = 0.15

    def __call__(self, examples):
        input_ids_batch = []
        attention_mask_batch = []
        encoder_mlm_mask_batch = []
        decoder_labels_batch = []
        decoder_matrix_attention_mask_batch = []
        process_cmd_ids_batch = []  # To store the process_ids of each example in the batch

        # target length for the actual content, excluding special tokens like [CLS] and [SEP], 
        tgt_len = self.max_seq_length - self.tokenizer.num_special_tokens_to_add(False)

        for e in examples:
            # Create a unique identifier using process_id and cmd
            # process_cmd_id = f"{e['process_id']}_{e['cmd']}"
            process_cmd_id = f"{e['process_id']}"
            process_cmd_ids_batch.append(process_cmd_id)

            e_trunc = self.tokenizer.build_inputs_with_special_tokens(e['token_ids'][:tgt_len])
            tokens = [self.tokenizer._convert_id_to_token(tid) for tid in e_trunc]
            
            self.mlm_probability = self.encoder_mlm_probability
            # text_encoder_mlm_mask is a list that indicates which tokens should be masked for the encoder.
            text_encoder_mlm_mask = self._whole_word_mask(tokens)
            if self.mlm_probability == 0:
                text_encoder_mlm_mask = torch.zeros(len(text_encoder_mlm_mask))
            
            # create decode mlm mask
            self.mlm_probability = self.decoder_mlm_probability
            mask_set = []
            for _ in range(min(len(tokens), 256)): # generate enough masking patterns, but not too many
                mask_set.append(self._whole_word_mask(tokens))
            # text_matrix_attention_mask is the final attention mask used by the deconder
            text_matrix_attention_mask = []
            for i in range(len(tokens)):
                # random selects a mask from mask set
                idx = random.randint(0, min(len(tokens), 256) - 1)
                text_decoder_mlm_mask = deepcopy(mask_set[idx])
                # ensures the token can always attend to itself.
                text_decoder_mlm_mask[i] = 1
                text_matrix_attention_mask.append(text_decoder_mlm_mask)

            input_ids_batch.append(torch.tensor(e_trunc))
            attention_mask_batch.append(torch.tensor([1] * len(e_trunc)))
            # Sets the first and last token of e_trunc to -100 to ensure they are ignored during loss computation for the decoder.
            e_trunc[0] = -100
            e_trunc[-1] = -100
            decoder_labels_batch.append(torch.tensor(e_trunc))

            encoder_mlm_mask_batch.append(torch.tensor(text_encoder_mlm_mask))
            decoder_matrix_attention_mask_batch.append(1 - torch.tensor(text_matrix_attention_mask))

        # Batch Tensorization and Padding
        input_ids_batch = tensorize_batch(input_ids_batch, self.tokenizer.pad_token_id)
        attention_mask_batch = tensorize_batch(attention_mask_batch, 0)
        origin_input_ids_batch = input_ids_batch.clone()
        encoder_mlm_mask_batch = tensorize_batch(encoder_mlm_mask_batch, 0)

        # print(self.encoder_mlm_probability)
        # print(input_ids_batch[1], encoder_mlm_mask_batch[1])
        encoder_input_ids_batch, encoder_labels_batch = self.torch_mask_tokens(input_ids_batch, encoder_mlm_mask_batch)
        # print(encoder_input_ids_batch[1], encoder_labels_batch[1])
        # print(hhh)

        decoder_labels_batch = tensorize_batch(decoder_labels_batch, -100)
        matrix_attention_mask_batch = tensorize_batch(decoder_matrix_attention_mask_batch, 0)
        batch = {
            "encoder_input_ids": encoder_input_ids_batch,
            "encoder_attention_mask": attention_mask_batch,
            "encoder_labels": encoder_labels_batch,
            "decoder_input_ids": origin_input_ids_batch,
            "decoder_attention_mask": matrix_attention_mask_batch,  # [B,L,L]
            "decoder_labels": decoder_labels_batch,
            "process_cmd_ids": process_cmd_ids_batch   # Add combined process_id and cmd to the batch
        }

        # print('----------------batch----------------')
        # print(batch)

        return batch


@dataclass
class DupMAECollator(DataCollatorForWholeWordMask):
    max_seq_length: int = 512
    encoder_mlm_probability: float = 0.15
    decoder_mlm_probability: float = 0.15

    def __call__(self, examples):
        input_ids_batch = []
        attention_mask_batch = []
        encoder_mlm_mask_batch = []
        decoder_labels_batch = []
        decoder_matrix_attention_mask_batch = []
        bag_word_weight = []

        tgt_len = self.max_seq_length - self.tokenizer.num_special_tokens_to_add(False)

        for e in examples:
            e_trunc = self.tokenizer.build_inputs_with_special_tokens(e['token_ids'][:tgt_len])
            tokens = [self.tokenizer._convert_id_to_token(tid) for tid in e_trunc]

            self.mlm_probability = self.encoder_mlm_probability
            text_encoder_mlm_mask = self._whole_word_mask(tokens)

            self.mlm_probability = self.decoder_mlm_probability
            mask_set = []
            for _ in range(min(len(tokens), 256)):
                mask_set.append(self._whole_word_mask(tokens))

            text_matrix_attention_mask = []
            for i in range(len(tokens)):
                idx = random.randint(0, min(len(tokens), 256) - 1)
                text_decoder_mlm_mask = deepcopy(mask_set[idx])
                text_decoder_mlm_mask[i] = 1
                text_matrix_attention_mask.append(text_decoder_mlm_mask)

            input_ids_batch.append(torch.tensor(e_trunc))
            attention_mask_batch.append(torch.tensor([1] * len(e_trunc)))
            e_trunc[0] = -100
            e_trunc[-1] = -100
            decoder_labels_batch.append(torch.tensor(e_trunc))

            encoder_mlm_mask_batch.append(torch.tensor(text_encoder_mlm_mask))
            decoder_matrix_attention_mask_batch.append(1 - torch.tensor(text_matrix_attention_mask))

            weight = torch.zeros(size=(self.tokenizer.vocab_size,))
            for t in e['token_ids'][:tgt_len]:
                weight[t] = 1 / len(e['token_ids'][:tgt_len])
            bag_word_weight.append(weight.unsqueeze(0))

        input_ids_batch = tensorize_batch(input_ids_batch, self.tokenizer.pad_token_id)
        attention_mask_batch = tensorize_batch(attention_mask_batch, 0)
        origin_input_ids_batch = input_ids_batch.clone()
        encoder_mlm_mask_batch = tensorize_batch(encoder_mlm_mask_batch, 0)
        encoder_input_ids_batch, encoder_labels_batch = self.torch_mask_tokens(input_ids_batch, encoder_mlm_mask_batch)
        decoder_labels_batch = tensorize_batch(decoder_labels_batch, -100)
        matrix_attention_mask_batch = tensorize_batch(decoder_matrix_attention_mask_batch, 0)
        bag_word_weight = torch.cat(bag_word_weight, dim=0)

        batch = {
            "encoder_input_ids": encoder_input_ids_batch,
            "encoder_attention_mask": attention_mask_batch,
            "encoder_labels": encoder_labels_batch,
            "decoder_input_ids": origin_input_ids_batch,
            "decoder_attention_mask": matrix_attention_mask_batch,  # [B,L,L]
            "decoder_labels": decoder_labels_batch,
            "bag_word_weight": bag_word_weight
        }

        # print('----------------batch----------------')
        # print(batch)

        return batch

