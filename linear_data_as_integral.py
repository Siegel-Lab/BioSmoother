import bisect
import random

class Coverage:
    def __init__(self):
        self.yys = []
        self.num_reads = 0
        self.sorted = []
        self.chr_sizes = []
        self.chr_starts = []
        self.xs = None

    def set_x_y(self, xs, ys):
        self.xs = xs
        self.yys = []
        c = 0
        for y in ys:
            c += y
            self.yys.append(c)
        return self

    def set(self, starts, ends, s, chr_sizes):
        starts.sort()
        ends.sort()
        self.sorted = sorted(s)
        self.num_reads = len(starts)
        assert self.num_reads == len(ends)

        xs = []
        ys = []
        i1 = 0
        i2 = 0
        c = 0
        # compute coverage
        while i1 < len(starts):
            ys.append(c)
            if starts[i1] < ends[i2]:
                c += 1
                xs.append(starts[i1])
                i1 += 1
            else:
                c -= 1
                xs.append(ends[i2])
                i2 += 1
        while i2 < len(ends):
            ys.append(c)
            c -= 1
            xs.append(ends[i2])
            i2 += 1

        # collapse regions where multiple reads started/ended
        ys_2 = [0]
        self.xs = [0]
        for x, y in zip(xs, ys):
            if len(self.xs) == 0 or x != self.xs[-1]:
                self.xs.append(x)
                ys_2.append(y)
            else:
                ys_2[-1] = max(y, ys_2[-1])

        # compute integral
        self.yys = []
        c = 0
        for y in ys_2:
            c += y
            self.yys.append(c)

        for c_start, c_size in zip(chr_sizes.chr_starts, chr_sizes.chr_sizes_l):
            self.chr_starts.append(self.count(0, c_start))
            self.chr_sizes.append(self.count(c_start, c_start + c_size))

        return self

    def count(self, f, t):
        return self.yys[min(bisect.bisect_right(self.xs, t-1), len(self.yys)-1)] - \
               self.yys[min(bisect.bisect_right(self.xs, f)-1, len(self.yys)-1)]

    def info(self, f, t):
        idx_f = max(bisect.bisect_left(self.sorted, (f, 0, ""))-1, 0)
        idx_t = min(bisect.bisect_left(self.sorted, (t, 0, ""))+1, len(self.sorted)-1)
        if idx_f >= len(self.sorted):
            return "n/a"
        s = ""
        for idx in range(idx_f, idx_t):
            if self.sorted[idx][1] > f and self.sorted[idx][0] < t:
                if len(s) > 0:
                    s += "; "
                s += self.sorted[idx][2]
        return s

    def bin_cols_or_rows(self, h_bin, chr_order, chr_starts, start=0, end=None, none_for_chr_border=False, 
                         chr_filter=None,
                         annotation_combination_strategy="combine"):
        if end is None:
            end = self.chr_starts[-1] + self.chr_sizes[-1]
        h_bin = max(1, h_bin)
        ret = []
        ret_2 = []
        ret_3 = []
        x_chrs = []
        subs = 0
        cont_idx = 0
        for idx, (c_start, c_size, n) in enumerate(zip(self.chr_starts, self.chr_sizes, chr_order)):
            if len(chr_filter) > 0 and n not in chr_filter:
                subs += c_size
            elif c_start-subs <= end and c_start-subs + c_size >= start:
                x_chrs.append((idx, subs))
        if none_for_chr_border:
            ret.append(None)
            ret_2.append(None)
            ret_3.append(None)
        for x_chr, sub in x_chrs:
            x_start = self.chr_starts[x_chr]
            x_end = self.chr_starts[x_chr] + self.chr_sizes[x_chr]
            e_start = max(int(start), x_start)
            e_end = min(int(end), x_end, len(self.sorted))
            annos_per_bin = int(h_bin)
            if annotation_combination_strategy == "force_separate":
                annos_per_bin = 1
            for idx in range(e_start, e_end, annos_per_bin):
                if annotation_combination_strategy == "combine":
                    s, _, _ = self.sorted[idx]
                    #print(idx + annos_per_bin - 1, e_end-1, len(self.sorted))
                    _, e, _ = self.sorted[min(idx + annos_per_bin - 1, e_end-2)]
                elif annotation_combination_strategy == "random":
                    s, e, _ = self.sorted[random.randint(idx, min(idx + annos_per_bin - 1, e_end-2))]
                else: # first or force_separate
                    s, e, _ = self.sorted[idx]
                ret.append((s, e - s))
                ret_2.append((chr_order[x_chr], s - chr_starts[x_chr]))
                ret_3.append((cont_idx - sub, annos_per_bin))
                cont_idx += annos_per_bin
            if none_for_chr_border:
                ret.append(None)
                ret_2.append(None)
                ret_3.append(None)
        return ret, ret_2, ret_3