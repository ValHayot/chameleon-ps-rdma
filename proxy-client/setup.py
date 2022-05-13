from distutils.core import setup, Extension

module1 = Extension('rdma_transfer',
                    include_dirs = ['/home/cc/spack/opt/spack/linux-centos7-haswell/gcc-11.2.1/mochi-margo-0.9.8-drfshmjljq7fq7w2q6dxpllw5uuhcczs/include',
                                    '/home/cc/spack/opt/spack/linux-centos7-haswell/gcc-11.2.1/mercury-2.1.0-upd2del7j4zmurslpzm2kglenxqh2mcs/include/',
                                    '/home/cc/spack/opt/spack/linux-centos7-haswell/gcc-11.2.1/argobots-1.1-hpvibv22u2xx5wypx7ze3wnq7axtxb3q/include/'],
                    library_dirs = ['/home/cc/spack/opt/spack/linux-centos7-haswell/gcc-11.2.1/mochi-margo-0.9.8-drfshmjljq7fq7w2q6dxpllw5uuhcczs/lib',
                                 '/home/cc/spack/opt/spack/linux-centos7-haswell/gcc-11.2.1/mercury-2.1.0-upd2del7j4zmurslpzm2kglenxqh2mcs/lib',
                                 '/home/cc/spack/opt/spack/linux-centos7-haswell/gcc-11.2.1/json-c-0.15-yc5c7wowlhb3gr2ipmfok7mj5y7ityct/lib64',
                                 '/home/cc/spack/opt/spack/linux-centos7-haswell/gcc-11.2.1/argobots-1.1-hpvibv22u2xx5wypx7ze3wnq7axtxb3q/lib'],
                    libraries = [ 'margo', 'mercury', 'abt' ],
                    sources = ['rdma_transfer.c'])

setup (name = 'rdma_transfer',
       version = '1.0',
       description = 'This is a demo package',
       ext_modules = [module1])
