import sys

def split_md(md_file_in, prefix_out):
    lines = [("", [])]
    with open(md_file_in, "r") as in_file:
        for line in in_file:
            if line[0] == "#":
                lines.append((line[:-1].replace("#", "").strip().replace(" ", "_"), []))
                continue
            lines[-1][1].append(line)

    for file_name, file_lines in lines:
        if file_name != "":
            with open(prefix_out + "/" + file_name + ".md", "w") as out_file:
                out_file.write("# " + file_name.replace("_", " ") + "\n\n")
                for line in file_lines:
                    line = line.replace(":bus:", "|:bus:|")
                    line = line.replace(":exclamation:", "|:exclamation:|")
                    out_file.write(line)

if __name__ == "__main__":
    split_md(sys.argv[1], sys.argv[2])