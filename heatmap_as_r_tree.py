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
        return sum(self.index.count(id, [int(rna_from), int(dna_from)], [int(rna_to), int(dna_to)]))

    def save(self):
        pass

    def info(self, id, rna_from, rna_to, dna_from, dna_to, map_q_min=0, map_q_max=MAP_Q_MAX):
        return ""



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
        return sum(self.index.count(id, int(pos_from), int(pos_to)))

    def save(self):
        pass

    def info(self, id, pos_from, pos_to, map_q_min=0, map_q_max=MAP_Q_MAX):
        return ""
