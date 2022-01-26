from libkdtree import kdtree

H = 0.5
MAP_Q_MAX = 256



class Tree_4:
    def __init__(self, data, bins, cache_size, threads):
        self.root = {}
        for idx, d in data:
            self.root[idx] = kdtree(d, bins, cache_size, threads, 1)

    def count(self, id, rna_from, rna_to, dna_from, dna_to, map_q_min=0, map_q_max=MAP_Q_MAX):
        return self.root[id].count([int(rna_from), int(dna_from), int(map_q_min)],
                                   [int(rna_to), int(dna_to), int(map_q_max+1)])

    def info(self, id, rna_from, rna_to, dna_from, dna_to, map_q_min=0, map_q_max=MAP_Q_MAX):
        return ""
        l = [n.object for n in self.idx.intersection((id, map_q_min, rna_from, dna_from, id+H, map_q_max-H,
                                                      rna_to-H, dna_to-H), objects=True)]
        s = ""
        for x in l:
            s += x + ", "
        return s



class Tree_3:
    def __init__(self, data, bins, cache_size, threads):
        self.root = {}
        for idx, d in data:
            self.root[idx] = kdtree(d, bins, cache_size, threads, 1)

    def count(self, id, pos_from, pos_to, map_q_min=0, map_q_max=MAP_Q_MAX):
        return self.root[id].count( [int(pos_from), int(map_q_min)], [int(pos_to), int(map_q_max+1)])



    def info(self, id, pos_from, pos_to, map_q_min=0, map_q_max=MAP_Q_MAX):
        return ""
        l = [n.object for n in self.idx.intersection((id, map_q_min, pos_from, id+H, map_q_max-H,
                                                      pos_to-H), objects=True)]
        s = ""
        for x in l:
            s += x + ", "
        return s
