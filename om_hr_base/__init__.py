from . import models
from .moved import take_over


def pre_init_hook(env):
    take_over(env.cr)
