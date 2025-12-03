# _*_ coding: utf-8 _*_
# Copyright (c) 2024, Hangzhou Deep Gaze Sci & Tech Ltd
# All Rights Reserved
#
# For use by  Hangzhou Deep Gaze Sci & Tech Ltd licencees only.
# Redistribution and use in source and binary forms, with or without
# modification, are NOT permitted.
#
# Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in
# the documentation and/or other materials provided with the distribution.
#
# Neither name of  Hangzhou Deep Gaze Sci & Tech Ltd nor the name of
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

import warnings
from functools import wraps


# Decorator to mark functions as deprecated with version information
def deprecated(version, tips=""):
    """
    A decorator to mark functions as deprecated with a specified version.

    This decorator issues a warning whenever a deprecated function is called,
    informing the user about the deprecation and the version it was introduced in.

    Args:
        version (str): The version in which the function was deprecated.
        tips (str): The tips message to show in the warning message.

    Returns:
        function: The decorated function that issues a warning when called.
    """

    def decorator(func):
        """
        The actual decorator that wraps the target function.

        Args:
            func (function): The function being decorated.

        Returns:
            function: A wrapper function that adds deprecation warning functionality.
        """

        @wraps(func)  # Ensures the decorated function retains its original name and docstring
        def wrapper(*args, **kwargs):
            """
            The wrapper function that issues the deprecation warning and calls the original function.

            Args:
                *args: Positional arguments passed to the original function.
                **kwargs: Keyword arguments passed to the original function.

            Returns:
                The return value of the original function.
            """
            warnings.warn(
                f"The function '{func.__name__}' is deprecated since version {version} and will be removed in"
                f" future versions. {tips}",
                DeprecationWarning,  # Specifies that this is a deprecation warning
            )
            return func(*args, **kwargs)  # Calls the original function

        return wrapper  # Return the wrapped version of the function

    return decorator  # Return the decorator function
