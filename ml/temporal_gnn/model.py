"""TGN-inspired, causal last-message aggregation + GRU + temporal attention.
One event is processed at a time; the last-message aggregator is identity for
that singleton. State resets for each bounded replay; gradients propagate
through the replay during training.
"""
import torch
from torch import nn
from torch_geometric.nn import TransformerConv

class TemporalGraph(nn.Module):
    def __init__(self,features=8,hidden=32,memory=True,graph=True):
        super().__init__()
        self.hidden=hidden;self.use_memory=memory;self.use_graph=graph
        self.types=nn.Embedding(7,8);self.edges=nn.Embedding(9,8)
        self.time=nn.Linear(1,8)
        self.message=nn.Sequential(nn.Linear(2*hidden+32+features,hidden),nn.ReLU(),nn.Linear(hidden,hidden))
        self.gru=nn.GRUCell(hidden,hidden)
        self.project=nn.Linear(features,hidden)
        self.attention=TransformerConv(hidden,hidden,heads=2,concat=False,edge_dim=16,dropout=0.0)
        self.head=nn.Sequential(nn.Linear(hidden*2+features,hidden),nn.ReLU(),nn.Linear(hidden,2),nn.Softplus())
        self.reset_state()
    def reset_state(self):
        self.memory={};self.last={};self.history=[]
    def state(self,node):
        return self.memory.get(node,torch.zeros(self.hidden,device=self.project.weight.device))
    def encoding(self,delta):
        return torch.cos(self.time(torch.tensor([[max(0,delta)/3600]],dtype=torch.float32,device=self.project.weight.device))).squeeze(0)
    def forward(self,src,dst,t,x,src_type=0,dst_type=2):
        # Strictly past, bounded neighborhood. No label or future interaction is read.
        past=[e for e in self.history if e[2]<t and (src in e[:2] or dst in e[:2])][-32:]
        nodes=sorted({src,dst}|{n for e in past for n in e[:2]});mapping={n:i for i,n in enumerate(nodes)}
        states=torch.stack([self.state(n) if self.use_memory else torch.zeros_like(self.state(n)) for n in nodes])
        states=states.clone();states[mapping[dst]]=states[mapping[dst]]+self.project(x)
        if self.use_graph and past:
            pairs=[];attrs=[]
            for a,b,when,kind in past:
                for u,v in [(a,b),(b,a)]:
                    pairs.append([mapping[u],mapping[v]])
                    attrs.append(torch.cat([self.edges(torch.tensor(kind,device=x.device)),self.encoding(t-when)]))
            states=self.attention(states,torch.tensor(pairs,device=x.device).T,torch.stack(attrs))
        prediction=self.head(torch.cat([states[mapping[src]],states[mapping[dst]],x]))
        return prediction
    def observe(self,src,dst,t,x,edge=0,src_type=0,dst_type=2):
        if self.history and t<self.history[-1][2]: raise ValueError('Events must be chronological')
        a,b=self.state(src),self.state(dst)
        msg=self.message(torch.cat([a,b,self.types(torch.tensor(src_type,device=x.device)),self.types(torch.tensor(dst_type,device=x.device)),self.edges(torch.tensor(edge,device=x.device)),self.encoding(t-self.last.get(src,t)),x]))
        if self.use_memory:
            self.memory[src]=self.gru(msg,a)
            self.memory[dst]=self.gru(msg,b)
        self.last[src]=t;self.last[dst]=t
        self.history.append((src,dst,t,edge));self.history=self.history[-4096:]
    def predict_context(self,src,dst,t,x,context):
        # Identical bounded replay contract in training and live inference.
        from ml.context import validate_context
        validate_context(context,t)
        self.reset_state()
        for event in context:
            self.observe(event['src'],event['dst'],event['time'],
                         torch.tensor(event['x'],dtype=torch.float32,device=x.device),
                         event['edge'],event['src_type'],event['dst_type'])
        return self(src,dst,t,x)
    def detach_state(self):
        self.memory={k:v.detach() for k,v in self.memory.items()}
