import argparse
import os
import shutil
from glob import glob

import accelerate
import numpy as np
import nvidia_smi
import torch


def mkdir(dir_name: str):
    if not os.path.isdir(dir_name):
        os.makedirs(dir_name)


def rmdir(dir_name: str):
    if os.path.isdir(dir_name):
        shutil.rmtree(dir_name, ignore_errors=True)


def rmfile(file_name: str):
    fpaths = glob(file_name)
    for fpath in fpaths:
        if os.path.exists(fpath):
            os.remove(fpath)


def calc_gpu_free_memory(gpu_indices, extra_memory) -> dict:
    nvidia_smi.nvmlInit()

    free_memory = dict()
    for idx in gpu_indices:
        handle = nvidia_smi.nvmlDeviceGetHandleByIndex(idx)
        gpu_memory_info = nvidia_smi.nvmlDeviceGetMemoryInfo(handle)
        each_free_memory = int((gpu_memory_info.free - extra_memory) /
                               int(os.environ['LOCAL_WORLD_SIZE']))
        if each_free_memory > 0:
            free_memory[idx] = each_free_memory

    return free_memory


def save_checkpoint(args: argparse.Namespace, model):
    ckpt_dir = os.path.join(args.data_root_dir, 'checkpoint')
    mkdir(ckpt_dir)

    args.waiting += 1

    args.accelerator.save_state(os.path.join(ckpt_dir, args.checkpoint))

    if args.val_losses[-1] <= min(args.val_losses):
        args.waiting = 0
        filename = 'BEST_' + args.checkpoint + '.ckpt'

        unwrapped_model = args.accelerator.unwrap_model(model)
        args.accelerator.save(unwrapped_model.state_dict(), os.path.join(ckpt_dir, filename))
        print('\t[!] The best checkpoint is updated.\n\n')
