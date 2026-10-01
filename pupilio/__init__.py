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
# Pupil.IO package entry point.

# Author: GC Zhu
# Email: zhugc2016@gmail.com
# Last updated: 2026/10/01 by Zhiguo Wang

import importlib
import logging

__all__ = [
    'Pupilio',
    'DefaultConfig',
    'EventDetection',
    'EventType',
    'ET_ReturnCode',
    'CalibrationMode',
    'ActiveEye',
    'CameraMode',
    'LSLManager',
    'PupilioLSLOutlet',
    '__version__',
]

# Add a NullHandler so the library never emits "no handler found" warnings when
# the embedding application has not configured logging. Sub-loggers like
# ``pupilio.core`` inherit this handler.
logging.getLogger(__name__).addHandler(logging.NullHandler())

# Map public name -> submodule that defines it. Used by ``__getattr__`` below to
# resolve attributes lazily, so ``import pupilio`` stays cheap and does not pull
# in numpy / ctypes / pylsl until the caller actually needs them.
_MODULE_MAP = {
    'Pupilio': '.core',
    'DefaultConfig': '.default_config',
    'EventDetection': '.event_detection',
    'EventType': '.misc',
    'ET_ReturnCode': '.misc',
    'CalibrationMode': '.misc',
    'ActiveEye': '.misc',
    'CameraMode': '.misc',
    'LSLManager': '.lsl',
    'PupilioLSLOutlet': '.lsl',
    '__version__': '.version',
}


def __getattr__(name):
    """
    Resolve a public name to its defining submodule on first access.

    The resolved value is cached into the module globals so subsequent lookups
    bypass this function entirely. Names not listed in ``_MODULE_MAP`` raise the
    standard ``AttributeError``.
    """
    if name in _MODULE_MAP:
        module = importlib.import_module(_MODULE_MAP[name], __package__)
        value = getattr(module, name)
        globals()[name] = value  # cache for later lookups
        return value

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__():
    """Return a fresh copy of ``__all__`` so callers cannot mutate it in place."""
    return list(__all__)