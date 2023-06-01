
from __future__ import absolute_import, print_function, unicode_literals
from .MicroPush import MicroPush



def create_instance(c_instance):
    return MicroPush(c_instance)
