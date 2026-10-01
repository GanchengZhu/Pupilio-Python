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
#
# !/usr/bin/python
# Author: GC Zhu
# Email: zhugc2016@gmail.com
# Last updated: 2026/10/01 by Zhiguo Wang

import inspect
import warnings
from functools import wraps
from typing import Callable


# Decorator to mark functions as deprecated with version information
def deprecated(version: str, tips: str = "") -> Callable:
    """
    A decorator to mark functions as deprecated with a specified version.

    This decorator issues a warning whenever a deprecated function is called,
    informing the user about the deprecation and the version it was introduced in.

    Both synchronous and asynchronous functions are supported; ``async def`` targets
    keep their coroutine nature so the decorated call still has to be awaited.

    Args:
        version (str): The version in which the function was deprecated.
        tips (str): Additional message appended to the warning.

    Returns:
        Callable: A decorator that wraps the target function so that calling it emits
        a :class:`DeprecationWarning` before delegating to the original implementation.
    """

    def decorator(func: Callable) -> Callable:
        """
        The actual decorator that wraps the target function.

        Args:
            func (Callable): The function being decorated.

        Returns:
            Callable: A wrapper that adds deprecation warning functionality.
        """
        warning_message = (
            f"The function '{func.__name__}' is deprecated since version "
            f"{version} and will be removed in future versions. {tips}"
        )

        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                warnings.warn(
                    warning_message,
                    DeprecationWarning,
                    stacklevel=2,
                )
                return await func(*args, **kwargs)

            return wrapper

        @wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                warning_message,
                DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)

        return wrapper

    return decorator