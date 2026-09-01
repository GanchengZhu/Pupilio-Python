# _*_ coding: utf-8 _*_
# Author: GC Zhu
# Email: zhugc2016@gmail.com

import glob
import os

from pupilio import EventDetection

# ed = EventDetection()
#
# out_dir = 'output_test'
# os.makedirs(out_dir, exist_ok=True)
# f = open('error.txt', 'w')
# for i in glob.glob(r'F:\event_detection_pipeline_test\data\*\*.csv'):
#     try:
#         ed.detect(i, output_dir=out_dir, which_eye='right')
#     except Exception as e:
#         f.write(i + ',' + str(e) + '\n')
#         f.flush()


ed = EventDetection()

out_dir = 'output_test'
os.makedirs(out_dir, exist_ok=True)
f = open('error.txt', 'w')
for i in glob.glob(r'data/fvTask_HC042.csv'):
    try:
        ed.detect(i, output_dir=out_dir, which_eye='right')
    except Exception as e:
        f.write(i + ',' + str(e) + '\n')
        f.flush()
