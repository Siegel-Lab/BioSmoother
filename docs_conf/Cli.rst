.. _cli_target:

Command line API reference
--------------------------

Below is the technical documentation for Smoother's command line interface.

.. argparse::
   :module: biosmoother
   :func: make_versioned_parser
   :prog: biosmoother
   :nodefault:

   serve : @before
    .. index:: serve
    .. _serve_command:

   init : @before
    .. index:: init
    .. _init_command:

   reset : @before
    .. index:: reset
    .. _reset_command:

   repl : @before
    .. index:: repl
    .. _repl_command:

   repl : @after
    The detailed explanation for the input format can be found :ref:`here <input_table>`.

   track : @before
    .. index:: track
    .. _track_command:

   track : @after
    The detailed explanation for the input format can be found :ref:`here <track_input_format>`.

   export : @before
    .. index:: export
    .. _export_command:

   set : @before
    .. index:: set
    .. _set_command:

   get : @before
    .. index:: get
    .. _get_command:

   ploidy : @before
    .. index:: ploidy
    .. _ploidy_command:

.. mdinclude:: ../generated_docs/IndexParameters.md