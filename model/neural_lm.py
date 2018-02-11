# coding=utf-8
import os
from itertools import chain

import torch
import torch.nn as nn
import torch.nn.utils
from torch.autograd import Variable
import torch.nn.functional as F
from torch.nn.utils.rnn import pad_packed_sequence, pack_padded_sequence

from model import nn_utils


class LSTMLanguageModel(nn.Module):
    def __init__(self, vocab, embed_size, hidden_size, dropout=0.):
        super(LSTMLanguageModel, self).__init__()

        self.vocab = vocab
        self.embed_size = embed_size
        self.hidden_size = hidden_size
        self.dropout_rate = dropout

        self.embed = nn.Embedding(len(vocab), embed_size)
        nn.init.xavier_normal(self.embed.weight)

        self.lstm = nn.LSTM(embed_size, hidden_size)
        self.read_out = nn.Linear(hidden_size, len(vocab))
        self.dropout = nn.Dropout(dropout)

        self.cross_entropy_loss = nn.CrossEntropyLoss(ignore_index=vocab['<pad>'], size_average=False, reduce=False)

    def forward(self, sent_var):
        """
        :param sent_var: (sent_len, batch_size)
        :return:
        """

        # (sent_len, batch_size, embed_size)
        token_embed = self.embed(sent_var)

        # (sent_len, batch_size, hidden_size)
        states, (last_state, last_cell) = self.lstm(token_embed[:-1])

        states = self.dropout(states)

        # (sent_len, batch_size, vocab_size)
        logits = self.read_out(states)
        sent_len = logits.size(0)
        batch_size = logits.size(1)
        vocab_size = logits.size(2)

        scores = self.cross_entropy_loss(logits.view(-1, vocab_size), sent_var[1:].view(-1)).view(sent_len, batch_size)
        scores = scores.sum(dim=0)

        return scores

    @classmethod
    def load(self, model_path, cuda=False):
        params = torch.load(model_path, map_location=lambda storage, loc: storage)
        model = LSTMLanguageModel(params['vocab'], *params['args'])
        model.load_state_dict(params['state_dict'])

        return model

    def save(self, path):
        dir_name = os.path.dirname(path)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

        params = {
            'args': (self.embed_size, self.hidden_size, self.dropout_rate),
            'vocab': self.vocab,
            'state_dict': self.state_dict()
        }

        torch.save(params, path)