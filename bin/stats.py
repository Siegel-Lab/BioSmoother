from statsmodels.stats.multitest import multipletests
from scipy.stats import binom_test

# code https://github.com/scipy/scipy/blob/v1.9.2/scipy/stats/_binomtest.py#L199-L329
def radicl_seq_norm(xs, num_interactions, bin_size, genome_size, p_accept=0.05):
    num_bins = genome_size/bin_size
    ps = [binom_test(x, num_interactions, 1/num_bins, alternative='greater') for x in xs]
    return [1 if x < p_accept else 0 for x in multipletests(ps, alpha=float("NaN"), method='fdr_bh')[1]]


# OPTIONS:
# - z-test for binom-test approximation:
#   - https://www.boost.org/doc/libs/1_80_0/libs/math/doc/html/math_toolkit/z_test.html
# - implementation of multipletests
#   - https://www.statsmodels.org/dev/_modules/statsmodels/stats/multitest.html
# - embedded interpreter:
#   - https://pybind11.readthedocs.io/en/stable/advanced/embedding.html
#
# - return another type of value?
# - trampoline functions
#   - https://pybind11.readthedocs.io/en/stable/advanced/classes.html?highlight=trampoline#overriding-virtual-functions-in-python