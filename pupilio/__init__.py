# _*_ coding: utf-8 _*_
# Copyright (c) 2024, Hangzhou DeepGaze Science and Technology Co., Ltd
# All Rights Reserved
#
# For use by  Hangzhou DeepGaze Science and Technology Co., Ltd licencees only.
# Redistribution and use in source and binary forms, with or without
# modification, are NOT permitted.
#
# Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in
# the documentation and/or other materials provided with the distribution.
#
# Neither name of  Hangzhou DeepGaze Science and Technology Co., Ltd nor the name of
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS ``AS
# IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# DESCRIPTION:
# This demo shows how to configure the calibration process

# Author: GC Zhu
# Email: zhugc2016@gmail.com

# _*_ coding: utf-8 _*_
# Author: GC Zhu
# Email: zhugc2016@gmail.com

# _*_ coding: utf-8 _*_
# Author: GC Zhu
# Email: zhugc2016@gmail.com

import logging
import importlib

__all__ = [
    'Pupilio',
    'DefaultConfig',
    'EventDetection',
    'EventType',
    'ET_ReturnCode',
    'CalibrationMode',
    'ActiveEye',
    'CameraMode',
    '__version__'
]

# 配置日志记录器
logging.getLogger(__name__).addHandler(logging.NullHandler())

# 建立 属性/类名 -> 对应子模块 的映射表
_MODULE_MAP = {
    'Pupilio': '.core',
    'DefaultConfig': '.default_config',
    'EventDetection': '.event_detection',
    'EventType': '.misc',
    'ET_ReturnCode': '.misc',
    'CalibrationMode': '.misc',
    'ActiveEye': '.misc',
    'CameraMode': '.misc',
    '__version__': '.version'
}


def __getattr__(name):
    # 如果请求的名称在映射表中，则动态导入对应模块
    if name in _MODULE_MAP:
        module_name = _MODULE_MAP[name]
        module = importlib.import_module(module_name, __package__)
        return getattr(module, name)

    # 如果请求的名称不存在，抛出标准 AttributeError
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__():
    return __all__