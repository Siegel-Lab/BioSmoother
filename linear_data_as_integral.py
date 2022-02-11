import bisect

class Coverage:
    def __init__(self):
        self.yys = []
        self.num_reads = 0
        self.sorted = []
        self.xs = None

    def set_x_y(self, xs, ys):
        self.xs = xs
        self.yys = []
        c = 0
        for y in ys:
            c += y
            self.yys.append(c)
        return self

    def set(self, starts, ends, s):
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
