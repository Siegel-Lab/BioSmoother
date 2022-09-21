
PRINT_MODULO = 10000
import subprocess
import errno
import os

TEST_FAC = 10000

def simplified_filepath(path):
    if "/" in path:
        x = path[path.rindex("/")+1:]
    if "." in path:
        return x[:x.index(".")]
    return x

def read_xa_tag(tags):
    if tags == "notag" or len(tags) < 5:
        return []
    l = []
    for tag in tags[5:].split(";"):
        split = tag.split(",")
        if len(split) == 5:
            chrom,str_pos,_CIGAR,_NM = split
            #strand = str_pos[0]
            pos = int(str_pos[1:])
            l.append([chrom, pos])
    return l

def parse_heatmap(in_filename, test, chr_filter):
    with open(in_filename, "r") as in_file_1:
        cnt = 0
        for line in in_file_1:
            # parse file columns
            num_cols = len(line.split())
            if num_cols == 7:
                read_name, chr_1, pos_1, chr_2, pos_2, mapq_1, mapq_2 = line.split()
                tag_a = "?"
                tag_b = "?"
            elif num_cols == 9:
                read_name, chr_1, pos_1, chr_2, pos_2, mapq_1, mapq_2, tag_a, tag_b = line.split()
            elif num_cols == 11:
                read_name, _1, chr_1, pos_1, _2, _3, chr_2, pos_2, _4, mapq_1, mapq_2 = line.split()
                tag_a = "?"
                tag_b = "?"
            elif num_cols == 13:
                read_name, _1, chr_1, pos_1, _2, _3, chr_2, pos_2, _4, mapq_1, mapq_2, tag_a, tag_b = line.split()
            else:
                raise ValueError("line \"" + line + "\" has " + str(num_cols) + 
                                 ", columns which is unexpected. There can be 7, 9, 11, or 13 columns.")
            
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

            yield read_name, chr_1, int(pos_1), chr_2, int(pos_2), mapq_1, mapq_2, tag_a, tag_b

def group_heatmap(in_filename, file_size, chr_filter, no_groups=False, test=False):
    file_name = simplified_filepath(in_filename)
    curr_read_name = None
    group_1 = []
    group_2 = []
    def deal_with_group():
        nonlocal group_1
        nonlocal group_2
        do_cont = True
        chr_1_cmp = group_1[0][0]
        for chr_1, _1, _2 in group_1:
            if chr_1_cmp != chr_1:
                do_cont = False # no reads that come from different chromosomes
        chr_2_cmp = group_2[0][0]
        for chr_2, _1, _2 in group_2:
            if chr_2_cmp != chr_2:
                do_cont = False # no reads that come from different chromosomes
        if do_cont:
            if no_groups:
                pos_1_s = group_1[1]
                pos_1_e = group_1[1]
                pos_2_s = group_2[1]
                pos_2_e = group_2[1]
            else:
                pos_1_s = min([p for _1, p, _2 in group_1])
                pos_1_e = max([p for _1, p, _2 in group_1])
                pos_2_s = min([p for _1, p, _2 in group_2])
                pos_2_e = max([p for _1, p, _2 in group_2])
            map_q = min(max(x for _1, _2, x in group_1), max(x for _1, _2, x in group_2))
            if len(group_1) > 1 and len(group_2) > 1:
                map_q += 1
            yield curr_read_name, chr_1, pos_1_s, pos_1_e, chr_2, pos_2_s, pos_2_e, map_q
        group_1 = []
        group_2 = []
    for idx_2, (read_name, chr_1, pos_1, chr_2, pos_2, mapq_1, mapq_2, tag_1, tag_2) in enumerate(
                                                                                        parse_heatmap(in_filename,
                                                                                                        test,
                                                                                                        chr_filter)):
        if read_name != curr_read_name and len(group_1) > 0:
            yield from deal_with_group()
        curr_read_name = read_name
        if tag_1 == "notag":
            have_no_tag_1 = True
        if tag_2 == "notag":
            have_no_tag_1 = True
        group_1.append((chr_1, int(pos_1), int(mapq_1)))
        group_2.append((chr_2, int(pos_2), int(mapq_2)))
        for chr_1, pos_1 in read_xa_tag(tag_1):
            group_1.append((chr_1, int(pos_1), 0))
        for chr_2, pos_2 in read_xa_tag(tag_2):
            group_2.append((chr_2, int(pos_2), 0))
        
        if idx_2 % PRINT_MODULO == 0:
            print("loading file", file_name, ", line", idx_2+1, "of", file_size, "=", 
                    round(100*(idx_2+1)/file_size, 2), "%", end="\033[K\r", flush=True)
    yield from deal_with_group()

def get_filesize(path):
    if not os.path.exists(path):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
    return int(subprocess.run(['wc', '-l', path], stdout=subprocess.PIPE).stdout.decode('utf-8').split(" ")[0])