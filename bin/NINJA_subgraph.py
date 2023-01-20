"""
bin/NINJA_subgraph.py
"""

from __future__ import print_function

from build import ninja_lib
from build.ninja_lib import log

_ = log


# TODO: remove this; probably should be sh_binary
RULES_PY = 'build/ninja-rules-py.sh'

def NinjaGraph(ru):
  n = ru.n

  ru.comment('Generated by %s' % __name__)

  for main_name in ('osh_eval', 'oils_cpp'):
    with open('_build/NINJA/%s/translate.txt' % main_name) as f:
      deps = [line.strip() for line in f]

    prefix = '_gen/bin/%s.mycpp' % main_name
    # header exports osh.cmd_eval
    outputs = [prefix + '.cc', prefix + '.h']
    n.build(outputs, 'gen-oils-cpp', deps,
            implicit=['_bin/shwrap/mycpp_main', RULES_PY],
            variables=[('out_prefix', prefix), ('main_name', main_name)])

    # The main program!

    symlinks = ['osh', 'ysh'] if main_name == 'oils_cpp' else []

    ru.cc_binary(
        '_gen/bin/%s.mycpp.cc' % main_name,
        symlinks = symlinks,
        preprocessed = True,
        matrix = ninja_lib.COMPILERS_VARIANTS + ninja_lib.GC_PERF_VARIANTS,
        top_level = True,  # _bin/cxx-dbg/oils_cpp
        deps = [
          '//cpp/core',
          '//cpp/libc',
          '//cpp/fanos',
          '//cpp/osh',
          '//cpp/pgen2',
          '//cpp/pylib',
          '//cpp/stdlib',

          '//cpp/frontend_flag_spec',
          '//cpp/frontend_match',
          '//cpp/frontend_pyreadline',

          '//frontend/arg_types',
          '//frontend/consts',
          '//frontend/id_kind.asdl',
          '//frontend/option.asdl',
          '//frontend/signal',
          '//frontend/syntax.asdl',
          '//frontend/types.asdl',

          '//core/optview',
          '//core/runtime.asdl',

          '//osh/arith_parse',
          '//oil_lang/grammar',

          '//mycpp/runtime',
          ]
        )
