from statsmodels.stats.multitest import multipletests
from scipy.stats import binom_test

def radicl_seq_norm(xs, num_interactions, bin_size, genome_size, p_accept=0.05):
    num_bins = genome_size/bin_size
    ps = [binom_test(x, num_interactions, 1/num_bins, alternative='greater') for x in xs]
    return [1 if x < p_accept else 0 for x in multipletests(ps, alpha=float("NaN"), method='fdr_bh')[1]]