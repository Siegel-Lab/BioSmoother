import bisect

class Coverage:
    def __init__(self):
        self.yys = []
        self.num_reads = 0

    def set(self, starts, ends):
        starts.sort()
        ends.sort()
        self.num_reads = len(starts)
        assert self.num_reads == len(ends)

        xs = []
        ys = []
        i1 = 0
        i2 = 0
        c = 0
        # compute coverage
        while i1 < len(starts):
            if starts[i1] < ends[i2]:
                c += 1
                xs.append(starts[i1])
                i1 += 1
            else:
                c -= 1
                xs.append(ends[i2])
                i2 += 1
            ys.append(c)
        while i2 < len(ends):
            c -= 1
            xs.append(ends[i2])
            i2 += 1
            ys.append(c)

        # collapse regions where multiple reads started/ended
        ys_2 = []
        self.xs = []
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

    def count(self, f, t):
        return self.yys[min(bisect.bisect_left(self.xs, t), len(self.yys)-1)] - \
               self.yys[min(bisect.bisect_left(self.xs, f), len(self.yys)-1)]
