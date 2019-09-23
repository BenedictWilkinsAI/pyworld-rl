#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 20 13:41:51 2019

@author: ben
"""
import numpy as np
import torch

import pyworld.toolkit.tools.datautils as du


def dataset(iterator, states, actions, onehot=True):
    assert states.shape[0] == actions.shape[0]
    stop = states.shape[0] - 1
    for i,x in enumerate(iterator):
        states[i] = x[0]
        if onehot:
            actions[i] = du.onehot_int(x[1], actions.shape[1])
        else:
            actions[i] = x[1]
        if i >= stop:
            #vu.play(vu.channels_to_cv(states), name='batch')
            return states, actions
                
def replay_iterator(env_iterator, state_input_shape, action_input_shape, batch_size = 64, replay_size = 10000, onehot = True):

    actions_replay = np.empty((replay_size, action_input_shape))
    states_replay = np.empty((replay_size, *state_input_shape))

    states_replay, actions_replay = dataset(env_iterator, states_replay, actions_replay, onehot)
    
    states_replay = torch.FloatTensor(states_replay)
    actions_replay = torch.FloatTensor(actions_replay)
    

    for i, x in enumerate(env_iterator):
        s, a = x
       
        if onehot:
            a = du.onehot_int(a, action_input_shape)

        states_replay[i % replay_size] = torch.FloatTensor(s)
        actions_replay[i % replay_size] = torch.FloatTensor(a)

        indx = np.random.randint(0, replay_size, batch_size)
        indx[np.where(indx == i)] += 1 #the only s_t -> s_t+1 that is invalid is at position i
        indx = indx % replay_size
        
        batch_states = states_replay[indx]
        batch_nstates = states_replay[(indx + 1) % replay_size] 
        batch_actions = actions_replay[indx]
        
        yield batch_states, batch_actions, batch_nstates
        
        #vu.play(vu.channels_to_cv(tu.numpy(batch_states)))
        
        #optimiser.step(batch_states, batch_actions, batch_nstates)
        
        #if not i % epoch_iterations:
        #    print(i, optimiser.cma())
        #    optimiser.cma.reset() 
        #    yield optimiser
            