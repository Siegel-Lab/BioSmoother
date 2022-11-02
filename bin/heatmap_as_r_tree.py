import os
os.environ["STXXLLOGFILE"] = "/dev/null"
os.environ["STXXLERRLOGFILE"] = "/dev/null"

from bin.libSps import make_sps_index, IntersectionType


H = 0.5
MAP_Q_MAX = 255


WITH_DEPENDENT_DIM = False
UNIFORM_OVERLAYS = True

INT_TYPES = {
    "enclosed": IntersectionType.enclosed,
    "encloses": IntersectionType.encloses,
    "overlaps": IntersectionType.overlaps,
    "first": IntersectionType.first,
    "last": IntersectionType.last,
    "points_only": IntersectionType.points_only,
}

class Tree_4:
    def __init__(self, file_name):
        self.file_name = file_name
        self.index = {}
        for map_q in [True, False]:
            self.index[map_q] = {}
            for multi_map in [True, False]:
                idx_suff = (".3" if map_q else ".2") + (".2" if multi_map else ".0")
                self.index[map_q][multi_map] = make_sps_index(file_name + ".smoother_index/repl" + idx_suff, 
                                                              3 if map_q else 2, 
                                                              WITH_DEPENDENT_DIM, UNIFORM_OVERLAYS, 
                                                              2 if multi_map else 0, 
                                                              "PickByFileSize", False )

    def setup(self, data, bins, cache_size, threads):
        return self

    def load(self, num_data, cache_size, threads):
        return self

    def to_query(self, id, rna_from, rna_to, dna_from, dna_to, map_q_min, map_q_max, 
                 has_map_q, multi_map):
        dna_to = max(dna_from+1, dna_to)
        rna_to = max(rna_from+1, rna_to)
        if has_map_q:
            return (id, [int(dna_from), int(rna_from), MAP_Q_MAX-map_q_max], 
                    [int(dna_to), int(rna_to), MAP_Q_MAX-map_q_min])
        else: #if not has_map_q
            return (id, [int(dna_from), int(rna_from)], [int(dna_to), int(rna_to)])


    def count(self, id, rna_from, rna_to, dna_from, dna_to, map_q_min, map_q_max,
              intersection_type, map_q, multi_map):
        return self.index[map_q][multi_map].count(
                                *self.to_query(id, rna_from, rna_to, dna_from, dna_to, map_q_min, map_q_max,
                                               map_q, multi_map),
                                INT_TYPES[intersection_type])

    def count_multiple(self, queries, intersection_type, map_q, multi_map):
        return self.index[map_q][multi_map].count_multiple(queries, INT_TYPES[intersection_type])

    def save(self):
        pass

    def get_overlay_grid(self, idx):
        return self.index.get_overlay_grid(idx)

    def get(self, idx, rna_from, rna_to, dna_from, dna_to):
        return self.index.get(idx, [int(dna_from), int(rna_from)], [int(dna_to), int(rna_to)])

    def info(self, idx, rna_from, rna_to, dna_from, dna_to, map_q_min=0, map_q_max=MAP_Q_MAX):
        ret = ""
        return ret
        for layer, d in enumerate(self.get(idx, rna_from, rna_to, dna_from, dna_to)):
            if layer >= map_q_min and layer < map_q_max:
                for _, read_name in d:
                    if not len(ret) == 0:
                        ret += ", "
                    ret += read_name
        return ret



class Tree_3:
    def __init__(self, file_name):
        self.index = make_sps_index(file_name + ".smoother_index/norm", 2, False, True, 1, "PickByFileSize", False )
        self.file_name = file_name
        self.root = {}

    def setup(self, data, bins, cache_size, threads):
        return self

    def load(self, num_data, cache_size, threads):
        return self

    def to_query(self, pos_from, pos_to, map_q_min=0, map_q_max=MAP_Q_MAX):
        pos_to = max(pos_from+1, pos_to)
        return ([int(pos_from), MAP_Q_MAX-map_q_max], [int(pos_to), MAP_Q_MAX-map_q_min])

    def count(self, id, pos_from, pos_to, map_q_min=0, map_q_max=MAP_Q_MAX, intersection_type="enclosed"):
        return self.index.count(id, *self.to_query(pos_from, pos_to, map_q_min, map_q_max),
                                INT_TYPES[intersection_type])

    def count_multiple(self, id, queries, intersection_type="enclosed"):
        return self.index.count_multiple(id, queries, INT_TYPES[intersection_type])

    def save(self):
        pass

    def get(self, id, pos_from, pos_to):
        return self.index.get(id, int(pos_from), int(pos_to))

    def info(self, id, pos_from, pos_to, map_q_min=0, map_q_max=MAP_Q_MAX):
        ret = ""
        return ret
        for layer, d in enumerate(self.get(id, pos_from, pos_to)):
            if layer >= map_q_min and layer < map_q_max:
                for _, read_name in d:
                    if not len(ret) == 0:
                        ret += ", "
                    ret += read_name
        return ret
