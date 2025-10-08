# _*_ coding: utf-8 _*_
# Author: GC Zhu
# Email: zhugc2016@gmail.com
import glob
import os

from pupilio import EventDetection

ed = EventDetection()

out_dir = 'output'
os.makedirs(out_dir, exist_ok=True)
for i in glob.glob('data/*.csv'):
    ed.detect(i, output_dir=out_dir, which_eye='right')
