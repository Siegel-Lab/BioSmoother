from rtree import index

class Tree:
    def __init__(self, file_name):
        p = index.Property()
        p.dimension = 3
        self.idx = index.Index(file_name, properties=p)
        self.next_id = 0

    def insert(self, info, rna_pos, dna_pos, map_q=254):
        self.idx.insert(self.next_id, (map_q, rna_pos, dna_pos, map_q+1, rna_pos+1, dna_pos+1), obj=info)
        self.next_id += 1

    def count(self, rna_from, rna_to, dna_from, dna_to, map_q_min=0, map_q_max=255):
        return self.idx.count(map_q_min, rna_from, dna_from, map_q_max, rna_to, dna_to)

    def get(self, rna_from, rna_to, dna_from, dna_to, map_q_min=0, map_q_max=255):
        return [n.object for n in self.idx.intersection((map_q_min, rna_from, dna_from, map_q_max, rna_to, dna_to),
                                                        objects=True)]

    def clear(self):
        self.idx.clear()