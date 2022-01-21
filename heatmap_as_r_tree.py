from rtree import index, core
import ctypes

H = 0.5
CACHE_CHUNK_SIZE = 100000
MAP_Q_MAX = 256

core.rt.Index_Setup_count.argtypes = [ctypes.c_void_p]

class Tree_4:
    def __init__(self, file_name):
        p = index.Property()
        p.dimension = 4
        self.idx = index.Index(file_name, properties=p)
        self.next_id = 0

    def insert(self, info, id, rna_pos, dna_pos, map_q=MAP_Q_MAX):
        self.idx.insert(self.next_id, (id, map_q, rna_pos, dna_pos,
                        id+H, map_q+H, rna_pos+H, dna_pos+H), obj=info)
        self.next_id += 1

    def count(self, id, rna_from, rna_to, dna_from, dna_to, map_q_min=0, map_q_max=MAP_Q_MAX, from_cache=False):
        return self.idx.count((id, map_q_min, rna_from, dna_from, id+H, map_q_max-H, rna_to-H, dna_to-H))

    def info(self, id, rna_from, rna_to, dna_from, dna_to, map_q_min=0, map_q_max=MAP_Q_MAX):
        l = [n.object for n in self.idx.intersection((id, map_q_min, rna_from, dna_from, id+H, map_q_max-H,
                                                      rna_to-H, dna_to-H), objects=True)]
        s = ""
        for x in l:
            s += x + ", "
        return s

    def make_count_cache(self):
        core.rt.Index_Setup_count(self.idx.handle)


class Tree_3:
    def __init__(self, file_name):
        p = index.Property()
        p.dimension = 3
        self.idx = index.Index(file_name, properties=p)
        self.next_id = 0

    def insert(self, info, id, pos, map_q=254):
        self.idx.insert(self.next_id, (id, map_q, pos,
                        id+H, map_q+H, pos), obj=info)
        self.next_id += 1

    def count(self, id, pos_from, pos_to, map_q_min=0, map_q_max=MAP_Q_MAX, from_cache=False):
        return self.idx.count((id, map_q_min, pos_from, id+H, map_q_max-H, pos_to-H))

    def make_count_cache(self):
        core.rt.Index_Setup_count(self.idx.handle)


    def info(self, id, pos_from, pos_to, map_q_min=0, map_q_max=MAP_Q_MAX):
        l = [n.object for n in self.idx.intersection((id, map_q_min, pos_from, id+H, map_q_max-H,
                                                      pos_to-H), objects=True)]
        s = ""
        for x in l:
            s += x + ", "
        return s
