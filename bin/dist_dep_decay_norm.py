def sample_dist_dep_dec(in_file_name, out_file_name):
    dist_decays = {}
    with open(in_file_name, "r") as in_file:
        for line in in_file:
            if len(line) == 0 or line[0] == "#":
                continue
            chr_1, pos_1, chr_2, pos_2, score, *extra = line.split()
            if chr_1 == chr_2:
                dist = abs(int(pos_1) - int(pos_2))
                if dist not in dist_decays:
                    dist_decays[dist] = (0, 0)
                sum_score, num_scores = dist_decays[dist]
                sum_score += float(score)
                dist_decays[dist] = (sum_score, num_scores + 1)

    with open(out_file_name, "w") as out_file:
        out_file.write("## Distance dependent decay of " + in_file_name + "\n")
        out_file.write("#Distance\tAverage Score\n")
        for dist, (sum_score, num_scores) in sorted(dist_decays.items()):
            out_file.write(str(dist) + "\t" + str(sum_score / num_scores) + "\n")

def load_dist_dep_decay(meta, in_file_name, chr_list):
    dists = []
    scores = []
    with open(in_file_name, "r") as in_file:
        for line in in_file:
            if len(line) == 0 or line[0] == "#":
                continue
            dist, avg_score, *extra = line.split()
            dists.append(int(dist))
            scores.append(float(avg_score))
    for chr_ in chr_list:
        if chr_ not in meta.chr_sizes.chr_sizes:
            print("ERROR: tried adding distance dependent decay function to non-existant contig", chr_ + ".", 
                  "Available contigs are:", *list(meta.chr_sizes.chr_sizes.keys()))
        meta.add_dist_dep_decay(chr_, dists, scores)