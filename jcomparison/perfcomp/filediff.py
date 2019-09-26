#!/usr/bin/python3
import argparse
import difflib


def make_diff(fromfile=None, tofile=None, fromstr=None, tostr=None):
    if fromfile:
        with open(fromfile) as ff:
            fromlines = ff.readlines()
    if tofile:
        with open(tofile) as tf:
            tolines = tf.readlines()
    if fromstr:
        if isinstance(fromstr, bytes):
            fromstr = fromstr.decode("utf-8")
        fromlines = fromstr.splitlines()
    if tostr:
        if isinstance(tostr, bytes):
            tostr = tostr.decode("utf-8")
        tolines = tostr.splitlines()
    inline, uniq1, uniq2 = [], [], []
    d = difflib.Differ()
    diff_gen = d.compare(fromlines, tolines)
    diff = list(diff_gen)
    for i, line in enumerate(diff):
        # Inline differences
        if line.startswith('-') and diff[i + 1].startswith('?'):
            if diff[i + 2].startswith('+') and diff[i + 3].startswith('?'):
                inline.append([line.lstrip("-+ "), diff[i + 2].lstrip("-+ ")])
            else:
                uniq1.append(line.lstrip("-+ "))
        # Unique differences
        elif line.startswith('-') and not diff[i + 1].startswith('?'):
            uniq1.append(line.lstrip("-+ "))
        if line.startswith('+') and not diff[i + 1].startswith('?'):
            uniq2.append(line.lstrip("-+ "))
    return inline, uniq1, uniq2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('fromfile')
    parser.add_argument('tofile')
    options = parser.parse_args()
    inline, uniq1, uniq2 = make_diff(options.fromfile, options.tofile)
    print("Inline\n", "\n".join(["".join(i) for i in inline]))
    print("Uniq for file 1\n", "".join(uniq1))
    print("Uniq for file 2\n", "".join(uniq2))


if __name__ == '__main__':
    main()
