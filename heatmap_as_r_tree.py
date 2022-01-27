from libkdtree import *

H = 0.5
MAP_Q_MAX = 256



class Tree_4:
    def __init__(self, file_name):
        self.file_name = file_name
        self.root = {}

    def setup(self, data, bins, cache_size, threads):
        for idx, d in data:
            self.root[idx] = kdtree_3(self.file_name + "." + str(idx), d, bins, cache_size, threads, 1, 0, 10000)
        return self

    def load(self, num_data, cache_size, threads):
        for idx in range(num_data):
            self.root[idx] = kdtree_3(self.file_name + "." + str(idx), cache_size, threads, 1, 0, 10000)
        return self

    def count(self, id, rna_from, rna_to, dna_from, dna_to, map_q_min=0, map_q_max=MAP_Q_MAX):
        return self.root[id].count([int(rna_from), int(dna_from), int(map_q_min)],
                                   [int(rna_to), int(dna_to), int(map_q_max+1)])

    def save(self):
        for d in self.root.values():
            d.make_caches(10000)
            d.save()


    def info(self, id, rna_from, rna_to, dna_from, dna_to, map_q_min=0, map_q_max=MAP_Q_MAX):
        return ""
        l = [n.object for n in self.idx.intersection((id, map_q_min, rna_from, dna_from, id+H, map_q_max-H,
                                                      rna_to-H, dna_to-H), objects=True)]
        s = ""
        for x in l:
            s += x + ", "
        return s



class Tree_3:
    def __init__(self, file_name):
        self.file_name = file_name
        self.root = {}

    def setup(self, data, bins, cache_size, threads):
        for idx, d in data:
            self.root[idx] = kdtree_2(self.file_name + "." + str(idx), d, bins, cache_size, threads, 1, 0, 10000)
        return self

    def load(self, num_data, cache_size, threads):
        for idx in range(num_data):
            self.root[idx] = kdtree_2(self.file_name + "." + str(idx), cache_size, threads, 1, 0, 10000)
        return self

    def count(self, id, pos_from, pos_to, map_q_min=0, map_q_max=MAP_Q_MAX):
        return self.root[id].count( [int(pos_from), int(map_q_min)], [int(pos_to), int(map_q_max+1)])

    def save(self):
        for d in self.root.values():
            d.make_caches(10000)
            d.save()


    def info(self, id, pos_from, pos_to, map_q_min=0, map_q_max=MAP_Q_MAX):
        return ""
        l = [n.object for n in self.idx.intersection((id, map_q_min, pos_from, id+H, map_q_max-H,
                                                      pos_to-H), objects=True)]
        s = ""
        for x in l:
            s += x + ", "
        return s
