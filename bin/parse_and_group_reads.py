
PRINT_MODULO = 10000
import subprocess

TEST_FAC = 800000

def simplified_filepath(path):
    if "/" in path:
        x = path[path.rindex("/")+1:]
    if "." in path:
        return x[:x.index(".")]
    return x

def parse_heatmap(in_filename, test, chr_filter):
    with open(in_filename, "r") as in_file_1:
        cnt = 0
        for line in in_file_1:
            # parse file columns
            read_name, strnd_1, chr_1, pos_1, _, strnd_2, chr_2, pos_2, _2, mapq_1, mapq_2 = line.split()
            
            if not chr_1 in chr_filter:
                continue
            if not chr_2 in chr_filter:
                continue
            # convert number values to ints
            pos_1, pos_2, mapq_1, mapq_2 = (int(x) for x in (pos_1, pos_2, mapq_1, mapq_2))
            pos_1 -= 1
            pos_2 -= 1

            if cnt > TEST_FAC and test:
                break
            cnt += 1

            yield read_name, strnd_1, chr_1, int(pos_1), strnd_2, chr_2, int(pos_2), mapq_1, mapq_2

def group_heatmap(in_filename, file_size, chr_filter, no_groups=False, test=False):
    file_name = simplified_filepath(in_filename)
    groups = {}
    for idx_2, (read_name, _, chr_1, pos_1, _, chr_2, pos_2, mapq_1, mapq_2) in enumerate(parse_heatmap(in_filename,
                                                                                                        test,
                                                                                                        chr_filter)):
        map_q = min(mapq_1, mapq_2)
        if not read_name in groups:
            groups[read_name] = []
        groups[read_name].append((chr_1, int(pos_1), chr_2, int(pos_2), int(map_q)))
        
        if idx_2 % PRINT_MODULO == 0:
            print("loading file", file_name, ", line", idx_2+1, "of", file_size, "=", 
                    round(100*(idx_2+1)/file_size, 2), "%", end="\033[K\r")

    for idx, (read_name, group) in enumerate(groups.items()):
        if idx % PRINT_MODULO == 0:
            print("grouping ", file_name, ", read", idx+1, "of", len(groups), "=", 
                    round(100*(idx+1)/len(groups), 2), "%", end="\033[K\r")
        chr_1 = group[0][0]
        chr_2 = group[0][2]
        do_cont = False
        for g_chr_1, _, g_chr_2, _, _ in group:
            if g_chr_1 != chr_1:
                do_cont = True # no reads that come from different chromosomes
            if g_chr_2 != chr_2:
                do_cont = True # no reads that come from different chromosomes
        if do_cont:
            continue
        if no_groups:
            pos_1_s = group[0][1]
            pos_2_s = group[0][3]
            pos_1_e = group[0][1]
            pos_2_e = group[0][3]
        else:
            pos_1_s = min([g[1] for g in group])
            pos_2_s = min([g[3] for g in group])
            pos_1_e = max([g[1] for g in group])
            pos_2_e = max([g[3] for g in group])
        map_q = max([g[4] for g in group])
        yield read_name, chr_1, pos_1_s, pos_1_e, chr_2, pos_2_s, pos_2_e, map_q

def get_filesize(path):
    return int(subprocess.run(['wc', '-l', path], stdout=subprocess.PIPE).stdout.decode('utf-8').split(" ")[0])