from distutils.core import setup, Extension
from glob import glob
import os

module1 = Extension('rdma_transfer',
                    libraries = [ 'margo', 'mercury', 'abt' ],
                    sources = ['rdma_transfer.c'])

setup (name = 'rdma_transfer',
       version = '1.0',
       description = 'This is a demo package',
       ext_modules = [module1])
