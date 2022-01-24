from perfcomp.utils import get_file, red, green
from perfcomp.config import PIP_LOC


def get_pip_modules_names(file_content):
    flag = False
    result = []
    for line in file_content:
        if flag:
            result.append(line)
        if '---------------------------------' in line:
            flag = True
    return result


def pip_modules(good, bad):
    g = get_file(good, PIP_LOC, json_file=False)
    b = get_file(bad, PIP_LOC, json_file=False)
    good, bad = [get_pip_modules_names(i.decode("utf-8").splitlines())
                 for i in (g, b)]
    common = [i.strip()
              for i in list(set(good).intersection(bad)) if i.strip()]
    g_uniq_set1 = (i.strip()
                   for i in good if i.strip() not in common and i.strip())
    b_uniq_set2 = (i.strip()
                   for i in bad if i.strip() not in common and i.strip())
    tup_uniq_set1 = (i.split() for i in g_uniq_set1)
    tup_uniq_set2 = (i.split() for i in b_uniq_set2)
    uniq_set1 = [(i[0].strip(), i[1].strip()) for i in tup_uniq_set1]
    uniq_set2 = [(i[0].strip(), i[1].strip()) for i in tup_uniq_set2]
    uniq_dict1 = {i[0]: i[1] for i in uniq_set1}
    uniq_dict2 = {i[0]: i[1] for i in uniq_set2}
    common_names = list(set([i[0] for i in uniq_set1]).intersection(
        [i[0] for i in uniq_set2]))
    uniq1_list = list(set([i[0] for i in uniq_set1])
                      - set([i[0] for i in uniq_set2]))
    uniq2_list = list(set([i[0] for i in uniq_set2])
                      - set([i[0] for i in uniq_set1]))
    uniq1 = ["-".join([i, uniq_dict1[i]]) for i in uniq1_list]
    uniq2 = ["-".join([i, uniq_dict2[i]]) for i in uniq2_list]
    inline = [
        ("-".join([i, green(uniq_dict1[i])]),
         "-".join([i, red(uniq_dict2[i])]))
        for i in common_names
    ]
    return inline, uniq1, uniq2
