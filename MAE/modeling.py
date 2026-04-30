import logging

import os
import torch
# from pretrain.arguments import ModelArguments
# from pretrain.enhancedDecoder import BertLayerForDecoder
from arguments import ModelArguments
from enhancedDecoder import BertLayerForDecoder
from torch import nn
from transformers import BertForMaskedLM, AutoModelForMaskedLM
from transformers.modeling_outputs import MaskedLMOutput

logger = logging.getLogger(__name__)


class RetroMAEForPretraining(nn.Module):
    def __init__(
            self,
            bert: BertForMaskedLM,
            model_args: ModelArguments,
    ):
        super(RetroMAEForPretraining, self).__init__()
        self.lm = bert

        self.decoder_embeddings = self.lm.bert.embeddings
        self.c_head = BertLayerForDecoder(bert.config)
        self.c_head.apply(self.lm._init_weights)

        self.cross_entropy = nn.CrossEntropyLoss()

        self.model_args = model_args

    def forward(self,
                encoder_input_ids, encoder_attention_mask, encoder_labels,
                decoder_input_ids, decoder_attention_mask, decoder_labels,
                process_cmd_ids=None, embeddings_dict=None):
        # return (torch.sum(self.lm.bert.embeddings.position_ids[:, :decoder_input_ids.size(1)]), )
        lm_out: MaskedLMOutput = self.lm(
            encoder_input_ids, encoder_attention_mask,
            labels=encoder_labels,
            output_hidden_states=True,
            return_dict=True
        ) #### self.lm is an instance of BertForMaskedLM, BertForMaskedLM is a pre-trained BERT model from Hugging Face that is designed for Masked Language Modeling (MLM)
        cls_hiddens = lm_out.hidden_states[-1][:, :1]  # B 1 D

        ### encoder embedding
        encoder_embeddings = lm_out.hidden_states[-1] # Extract final hidden states as embeddings
        # print(len(decoder_input_ids))

        decoder_embedding_output = self.decoder_embeddings(input_ids=decoder_input_ids)
        # decoder_embedding_output: torch.Size([128, 150, 768]) # batch size 128, sequence length 150. embedding dimension 768 (Each of the 150 tokens is represented by a 768-dimensional vector.)
        
        # print(decoder_embedding_output)
        # print(decoder_embedding_output.size())
        
        hiddens = torch.cat([cls_hiddens, decoder_embedding_output[:, 1:]], dim=1)

        decoder_position_ids = self.lm.bert.embeddings.position_ids[:, :decoder_input_ids.size(1)]
        decoder_position_embeddings = self.lm.bert.embeddings.position_embeddings(decoder_position_ids)  # B L D
        query = decoder_position_embeddings + cls_hiddens

        matrix_attention_mask = self.lm.get_extended_attention_mask(
            decoder_attention_mask,
            decoder_attention_mask.shape,
            decoder_attention_mask.device
        )

        hiddens = self.c_head(query=query,
                              key=hiddens,
                              value=hiddens,
                              attention_mask=matrix_attention_mask)[0]
        pred_scores, loss, accuracy = self.mlm_loss(hiddens, decoder_labels)

        print(f"--------GPU: {torch.cuda.current_device()} - loss + lm_out.loss--------")
        print(f"Loss 1: {loss}, Loss 2: {lm_out.loss}, Accuracy: {accuracy:.4f}")

        # torch.save(cls_hiddens, 'embeddings.pt')


        #  ---------- ADD ----------
        # Save Embeddings Using `process_ids` to `embeddings_dict`
        if process_cmd_ids is not None and embeddings_dict is not None:
            for i, process_cmd_id in enumerate(process_cmd_ids):
                embedding = cls_hiddens[i].cpu().detach().numpy()  # Convert to NumPy
                embeddings_dict[process_id] = embedding

        return (loss + lm_out.loss), cls_hiddens

    def mlm_loss(self, hiddens, labels):
        pred_scores = self.lm.cls(hiddens)
        masked_lm_loss = self.cross_entropy(
            pred_scores.view(-1, self.lm.config.vocab_size),
            labels.view(-1)
        )

        ## add here for accuracy
        predictions = torch.argmax(pred_scores, dim=-1)  # Get predicted token IDs
        # Calculate accuracy
        active_labels = labels != -100  # Ignore positions where label is -100
        correct_predictions = (predictions == labels) & active_labels
        num_correct = correct_predictions.sum().item()
        num_active_labels = active_labels.sum().item()

        if num_active_labels > 0:
            accuracy = num_correct / num_active_labels
        else:
            accuracy = 0.0  # If no active labels, accuracy is undefined; set to 0.0


        return pred_scores, masked_lm_loss, accuracy

    def save_pretrained(self, output_dir: str):
        self.lm.save_pretrained(output_dir)
        torch.save(self.c_head.state_dict(), os.path.join(output_dir,'c_head.pth'))

    @classmethod
    def from_pretrained(
            cls, model_args: ModelArguments,
            *args, **kwargs
    ):
        hf_model = AutoModelForMaskedLM.from_pretrained(*args, **kwargs)
        model = cls(hf_model, model_args)
        return model
