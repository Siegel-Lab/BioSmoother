from rtree import index
import bisect
import os

H = 0.5
CACHE_CHUNK_SIZE = 100000


class Tree_4:
    def __init__(self, file_name):
        p = index.Property()
        p.dimension = 4
        self.idx = index.Index(file_name, properties=p)
        self.cache_file_name = file_name + ".cache"
        self.next_id = 0
        self.cache = []
        self.cache_bins = []
        self.num_ids = 0
        self.load_cache()

    def insert(self, info, id, rna_pos, dna_pos, map_q=254):
        self.idx.insert(self.next_id, (id, map_q, rna_pos, dna_pos,
                        id+H, map_q+H, rna_pos+H, dna_pos+H), obj=info)
        self.next_id += 1

    def count(self, id, rna_from, rna_to, dna_from, dna_to, map_q_min=0, map_q_max=255, from_cache=False):
        if from_cache:
            c = 0
            x_s = bisect.bisect_left(self.cache_bins, rna_from)
            x_e = bisect.bisect_left(self.cache_bins, rna_to)
            y_s = bisect.bisect_left(self.cache_bins, dna_from)
            y_e = bisect.bisect_left(self.cache_bins, dna_to)
            for i in range(x_s, x_e):
                for j in range(y_s, y_e):
                    c += self.cache(self.cache_idx(i, j, id, map_q_max))
                    c -= self.cache(self.cache_idx(i, j, id, map_q_min))
            return c
        else:
            return self.idx.count((id, map_q_min, rna_from, dna_from, id+H, map_q_max-H, rna_to-H, dna_to-H))

    def info(self, id, rna_from, rna_to, dna_from, dna_to, map_q_min=0, map_q_max=255):
        l = [n.object for n in self.idx.intersection((id, map_q_min, rna_from, dna_from, id+H, map_q_max-H,
                                                      rna_to-H, dna_to-H), objects=True)]
        s = ""
        for x in l:
            s += x + ", "
        return s

    def cache_idx(self, i, j, k, m):
        return m + 255*(k + self.num_ids * (j + len(self.cache_bins) * i))

    def load_cache(self):
        self.cache = []
        self.cache_bins = []
        if os.path.exists(self.cache_file_name):
            with open(self.cache_file_name, "r") as in_file:
                for l in in_file.readlines():
                    if len(l) > 0:
                        if l[:len("#bin=")] == "#bin=":
                            self.cache_bins.append(int(l[len("#bin="):]))
                        elif l[:len("#num_ids=")] == "#num_ids=":
                            self.num_ids = int(l[len("#num_ids="):])
                        else:
                            self.cache.append(int(l))

    def make_cache(self, bins, num_ids, callback=lambda x: x):
        self.num_ids = num_ids
        self.cache_bins = bins
        self.cache = [0]*255*self.num_ids * \
            len(self.cache_bins)*len(self.cache_bins)
        idx = 0
        for i, (x, w) in enumerate(bins):
            for j, (y, h) in enumerate(bins):
                for id in range(self.num_ids):
                    for m in range(225):
                        c = self.count(id, x, x+w, y, y+h, 0, m+1)
                        self.cache[self.cache_idx(i, j, id, m)] = c
                        callback(idx)
                        idx += 1
        with open(self.cache_file_name, "w") as out_file:
            for x, w in self.bins:
                out_file.write("#bin=" + str(x))
            out_file.write("#num_ids=" + str(self.num_ids))
            for c in self.cache:
                out_file.write(str(c))
                out_file.write("\n")


class Tree_3:
    def __init__(self, file_name):
        p = index.Property()
        p.dimension = 3
        self.idx = index.Index(file_name, properties=p)
        self.cache_file_name = file_name + ".cache"
        self.next_id = 0
        self.cache = []
        self.cache_bins = []
        self.num_ids = 0
        self.load_cache()

    def insert(self, info, id, pos, map_q=254):
        self.idx.insert(self.next_id, (id, map_q, pos,
                        id+H, map_q+H, pos), obj=info)
        self.next_id += 1

    def count(self, id, pos_from, pos_to, map_q_min=0, map_q_max=255, from_cache=False):
        if from_cache:
            c = 0
            x_s = bisect.bisect_left(self.cache_bins, pos_from)
            x_e = bisect.bisect_left(self.cache_bins, pos_to)
            for i in range(x_s, x_e):
                c += self.cache(self.cache_idx(i, id, map_q_max))
                c -= self.cache(self.cache_idx(i, id, map_q_min))
            return c
        return self.idx.count((id, map_q_min, pos_from, id+H, map_q_max-H, pos_to-H))

    def cache_idx(self, j, k, m):
        return m + 255*(k + self.num_ids * j)

    def load_cache(self):
        self.cache = []
        self.cache_bins = []
        if os.path.exists(self.cache_file_name):
            with open(self.cache_file_name, "r") as in_file:
                for l in in_file.readlines():
                    if len(l) > 0:
                        if l[:len("#bin=")] == "#bin=":
                            self.cache_bins.append(int(l[len("#bin="):]))
                        elif l[:len("#num_ids=")] == "#num_ids=":
                            self.num_ids = int(l[len("#num_ids="):])
                        else:
                            self.cache.append(int(l))

    def make_cache(self, bins, num_ids, callback=lambda x: x):
        self.num_ids = num_ids
        self.cache_bins = bins
        self.cache = [0]*255*self.num_ids * \
            len(self.cache_bins)*len(self.cache_bins)
        idx = 0
        for i, (x, w) in enumerate(bins):
            for id in range(self.num_ids):
                for m in range(225):
                    c = self.count(id, x, x+w, 0, m+1)
                    self.cache[self.cache_idx(i, id, m)] = c
                    callback(idx)
                    idx += 1
        with open(self.cache_file_name, "w") as out_file:
            for x, w in self.bins:
                out_file.write("#bin=" + str(x))
            out_file.write("#num_ids=" + str(self.num_ids))
            for c in self.cache:
                out_file.write(str(c))
                out_file.write("\n")

    def info(self, id, pos_from, pos_to, map_q_min=0, map_q_max=255):
        l = [n.object for n in self.idx.intersection((id, map_q_min, pos_from, id+H, map_q_max-H,
                                                      pos_to-H), objects=True)]
        s = ""
        for x in l:
            s += x + ", "
        return s
