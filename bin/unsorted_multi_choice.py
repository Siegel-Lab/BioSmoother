from bokeh.core.properties import Bool, Tuple, List, Either, String, Nullable, Int
from bokeh.models import CustomJS, InputWidget

class UnsortedMultiChoice(InputWidget):
    ''' UnsortedMultiChoice widget.
    '''
    __implementation__ = 'unsorted_multi_choice.ts'

    # explicit __init__ to support Init signatures
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    options = List(Either(String, Tuple(String, String)), help="""
    Available selection options. Options may be provided either as a list of
    possible string values, or as a list of tuples, each of the form
    ``(value, label)``. In the latter case, the visible widget text for each
    value will be corresponding given label.
    """)

    value = List(String, help="""
    Initial or selected values.
    """)

    delete_button = Bool(default=True, help="""
    Whether to add a button to remove a selected option.
    """)

    max_items = Nullable(Int, help="""
    The maximum number of items that can be selected.
    """)

    option_limit = Nullable(Int, help="""
    The number of choices that will be rendered in the dropdown.
    """)

    search_option_limit = Nullable(Int, help="""
    The number of choices that will be rendered in the dropdown
    when search string is entered.
    """)

    placeholder = Nullable(String, help="""
    A string that is displayed if not item is added.
    """)

    solid = Bool(default=True, help="""
    Specify whether the choices should be solidly filled.""")

    shouldSort = Bool(default=True, help="""
    Specify whether the choices should be sorted filled.""")