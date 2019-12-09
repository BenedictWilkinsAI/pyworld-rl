#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jul  5 15:36:14 2019

@author: ben
"""

# W&B Imports

import os

#doesnt work... why not :(
if 'WB_ONLINE' in globals():
    __WANDB_MODE = {'offline':'dryrun', 'online':'run'}
    mode = globals()['WB_ONLINE']
    assert isinstance(mode, bool) #WANDB_ONLINE must be a boolean
    if mode:
        os.environ['WANDB_MODE'] = __WANDB_MODE['online']
    else:
        os.environ['WANDB_MODE'] = __WANDB_MODE['offline']
  
import wandb
import torch

from . import fileutils as fu

class WB:
   
    def __init__(self, project, model, save=True, id=None,  config={}, **options):
        self.project = project
        self.model = model
        self.__save = save
        if id is None:
            id = fu.file_datetime()

        wandb.init(project="ppo", id=id, config = config, **options)

    def __enter__(self):
        wandb.watch(self.model, log='all')
        
    def __call__(self, **info):
        wandb.log(info)
        
    def save(self, overwrite=True):
        file = os.path.join(wandb.run.dir, 'model.pt')
        if not overwrite:
            file = fu.file(file)
        torch.save(self.model.state_dict(), file)
        
    def __exit__(self, type, value, traceback):
        if self.__save:
            self.save()
            
            
        


            
