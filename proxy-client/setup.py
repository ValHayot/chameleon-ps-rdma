from distutils.core import setup, Extension

module1 = Extension('rdma_transfer',
                    include_dirs = ['/home/cc/spack/opt/spack/linux-centos7-haswell/gcc-11.2.1/mochi-margo-0.9.9-obklmzu7bpepcdeagouyzvwxrederno6/include',
                                    '/home/cc/spack/opt/spack/linux-centos7-haswell/gcc-11.2.1/mercury-2.1.0-uiizvaeo6pcnnd22gbelrctih3jsnhgo/include/',
                                    '/home/cc/spack/opt/spack/linux-centos7-haswell/gcc-11.2.1/argobots-1.1-6uc7mwbses3i3o7u2fnasud26jzgdd4j/include/'],
                    library_dirs = ['/home/cc/spack/opt/spack/linux-centos7-haswell/gcc-11.2.1/mochi-margo-0.9.9-obklmzu7bpepcdeagouyzvwxrederno6//lib',
                                 '/home/cc/spack/opt/spack/linux-centos7-haswell/gcc-11.2.1/mercury-2.1.0-uiizvaeo6pcnnd22gbelrctih3jsnhgo/lib',
                                 '/home/cc/spack/opt/spack/linux-centos7-haswell/gcc-11.2.1/json-c-0.15-zfzvec36zsbsyuhcgcdtce53f7qvvp6y/lib64',
                                 '/home/cc/spack/opt/spack/linux-centos7-haswell/gcc-11.2.1/argobots-1.1-6uc7mwbses3i3o7u2fnasud26jzgdd4j/lib'],
                    libraries = [ 'margo', 'mercury', 'abt' ],
                    sources = ['rdma_transfer.c'])

setup (name = 'rdma_transfer',
       version = '1.0',
       description = 'This is a demo package',
       ext_modules = [module1])
