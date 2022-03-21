import os
os.environ["STXXLLOGFILE"] = "/dev/null"
os.environ["STXXLERRLOGFILE"] = "/dev/null"

from libKdpsTree import *

H = 0.5
MAP_Q_MAX = 256



class Tree_4:
    def __init__(self, file_name):
        self.file_name = file_name
        self.index = KdpsTree(file_name)

    def setup(self, data, bins, cache_size, threads):
        return self

    def load(self, num_data, cache_size, threads):
        return self

    def count(self, id, rna_from, rna_to, dna_from, dna_to, map_q_min=0, map_q_max=MAP_Q_MAX):
        ret = sum(self.index.count(id, [int(rna_from), int(dna_from)], [int(rna_to), int(dna_to)]))
        return ret

    def save(self):
        pass

    def get(self, id, rna_from, rna_to, dna_from, dna_to):
        return self.index.get(id, [int(rna_from), int(dna_from)], [int(rna_to), int(dna_to)])

    def info(self, id, rna_from, rna_to, dna_from, dna_to, map_q_min=0, map_q_max=MAP_Q_MAX):
        ret = ""
        for layer, d in enumerate(self.get(id, rna_from, rna_to, dna_from, dna_to)):
            if layer >= map_q_min and layer < map_q_max:
                for _, read_name in d:
                    if not len(ret) == 0:
                        ret += ", "
                    ret += read_name
        return ret



class Tree_3:
    def __init__(self, file_name):
        self.index = PsArray(file_name + ".norm")
        self.file_name = file_name
        self.root = {}

    def setup(self, data, bins, cache_size, threads):
        return self

    def load(self, num_data, cache_size, threads):
        return self

    def count(self, id, pos_from, pos_to, map_q_min=0, map_q_max=MAP_Q_MAX):
        ret = sum(self.index.count(id, int(pos_from), int(pos_to)))
        return ret

    def save(self):
        pass

    def get(self, id, pos_from, pos_to):
        return self.index.get(id, int(pos_from), int(pos_to))

    def info(self, id, pos_from, pos_to, map_q_min=0, map_q_max=MAP_Q_MAX):
        ret = ""
        for layer, d in enumerate(self.get(id, pos_from, pos_to)):
            if layer >= map_q_min and layer < map_q_max:
                for _, read_name in d:
                    if not len(ret) == 0:
                        ret += ", "
                    ret += read_name
        return ret
