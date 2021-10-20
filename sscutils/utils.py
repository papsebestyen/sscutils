import os
import sys
from contextlib import contextmanager
from pathlib import Path
from subprocess import check_call
from tempfile import TemporaryDirectory
from typing import Union

import isort
from black import Mode, format_file_contents
from black.report import NothingChanged

from .naming import SRC_PATH

LINE_LEN = 119
PRIMITIVE_MODULES = ["builtins", "datetime"]
OWN_NAME = "sscutils"


def get_cls_defined_in_module(module, parent):
    # TODO: discard imported things
    out = {}
    for poss_cls_name in dir(module):
        cls = getattr(module, poss_cls_name)
        try:
            if parent in cls.mro()[1:]:
                out[poss_cls_name] = cls
        except AttributeError:
            pass
    return out


def get_instances_from_module(module, cls):
    out = {}
    for obj_name in dir(module):
        obj = getattr(module, obj_name)
        if isinstance(obj, cls):
            out[obj_name] = obj
    return out


def is_repo(s):
    return any(map(str(s).startswith, ["git@", "http://", "https://"]))


@contextmanager
def cd_into(dirpath: Union[str, Path], reset_src=True, checkout=None):
    wd = os.getcwd()
    needs_clone = is_repo(dirpath)

    if needs_clone:
        tmp_dir = TemporaryDirectory()
        cd_path = tmp_dir.__enter__()
        check_call(["git", "clone", str(dirpath), "."], cwd=cd_path)
    else:
        cd_path = dirpath

    if checkout:
        check_call(["git", "checkout", checkout], cwd=cd_path)

    os.chdir(cd_path)
    sys.path.insert(0, str(cd_path))

    if reset_src:
        for m_id in [
            *filter(
                lambda k: k.startswith(f"{SRC_PATH}.") or (k == f"{SRC_PATH}"),
                sys.modules.keys(),
            )
        ]:
            sys.modules.pop(m_id)
    yield

    os.chdir(wd)
    sys.path.pop(0)
    if needs_clone:
        tmp_dir.__exit__()


def format_code(code_str):
    try:
        blacked = format_file_contents(
            code_str, fast=True, mode=Mode(line_length=LINE_LEN)
        )
    except NothingChanged:
        blacked = code_str

    return isort.code(
        blacked,
        profile="black",
    )