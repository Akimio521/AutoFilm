import os

from setuptools import setup  # type: ignore
from Cython.Build import cythonize  # type: ignore


def find_py_files(directory):
    py_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py") and file not in [
                "main.py",
                "__init__.py",
                "setup.py",
            ]:
                py_files.append(os.path.join(root, file))
    return py_files


if __name__ == "__main__":
    setup(
        ext_modules=cythonize(
            find_py_files("./"),
            compiler_directives={
                "language_level": "3",  # 使用Python 3语法
                "annotation_typing": True,  # 使用类型注解
                "infer_types": True,  # 启用类型推断
            },
            nthreads=os.cpu_count() or 1,  # 使用所有可用的CPU核心
            force=True,  # 强制重新编译所有文件
        ),
        script_args=["build_ext", "--inplace"],
    )
