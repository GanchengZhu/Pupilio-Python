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

import os
import shutil

from setuptools import setup, find_packages
from setuptools.command.build_ext import build_ext

package_name = 'pupilio'
build_file = 'build_number.txt'


def get_build_number():
    if os.path.exists(build_file):
        with open(build_file, 'r') as f:
            build_number = int(f.read().strip())
    else:
        build_number = 0
    build_number += 1
    # 将新的 build 号写入文件
    with open(build_file, 'w') as f:
        f.write(str(build_number))
    return build_number


build_number = get_build_number()


class CustomBuildExt(build_ext):
    def run(self):
        # Ensure the build_ext is run first
        build_ext.run(self)
        # Copy the DLL file to the build/lib/my_package/lib directory
        build_lib = os.path.join(self.build_lib, package_name, 'lib')
        os.makedirs(build_lib, exist_ok=True)
        shutil.copy('pupilio/lib/*.dll', build_lib)
        # shutil.copy('pupilio/lib/libfilter.dll', build_lib)
        # shutil.copy('pupilio/lib/PupilioET.dll', build_lib)


from pupilio import version

major_version, minor_version, patch_version = version.__version__.split(".")

setup(
    name="pupilio",
    version=f"{major_version}.{minor_version}.{patch_version}",
    author="Pupilio",
    author_email="zhugc2016@gmail.com",
    description="Pupilio Library",
    url="https://github.com/GanchengZhu/Pupilio",
    packages=find_packages(),
    long_description=open('README.md').read(),  # 或者使用其他文档文件
    long_description_content_type='text/markdown',  # 如果使用 Markdown 格式
    package_data={
        'pupilio': ['lib/*.dll', 'resources/*', "asset/*"],
    },

    install_requires=[
        'numpy', 'pygame', 'opencv-python',
    ],

    cmdclass={'build_ext': CustomBuildExt},
)
