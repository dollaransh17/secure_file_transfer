"""Experimental byte-image CNN. Disabled in mandatory AV policy.
Input must be licensed original bytes, never EMBER feature vectors.
Binary vs family labels are declared in a manifest, not inferred.
"""
import torch
from torch import nn
import numpy as np

class ByteCNN(nn.Module):
    def __init__(self,classes=2):
        super().__init__()
        self.net=nn.Sequential(nn.Conv2d(1,16,3,padding=1),nn.ReLU(),nn.MaxPool2d(2),nn.Conv2d(16,32,3,padding=1),nn.ReLU(),nn.AdaptiveAvgPool2d((4,4)),nn.Flatten(),nn.Linear(512,classes))
    def forward(self,x): return self.net(x)
def image(data):
    # Fixed byte budget; truncation/padding are part of the model specification.
    array=np.zeros(65536,dtype=np.float32);source=np.frombuffer(data[:65536],dtype=np.uint8);array[:len(source)]=source/255.
    return torch.tensor(array.reshape(1,256,256))
