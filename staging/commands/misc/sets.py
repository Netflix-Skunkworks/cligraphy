#!/usr/bin/env/python

"""Print the intersection or union of two line-delimited data sets
"""


OPERATIONS = {
    'union': lambda left, right: left.union(right),
    'inter': lambda left, right: left.intersection(right),
    'ldiff': lambda left, right: left - right,
    'rdiff': lambda left, right: right - left,
}

def read_dataset(filename):
    result = set()
    with open(filename, 'r') as fpin:
        while True:
            line = fpin.readline()
            if not line:
                break
            result.add(line[:-1])
    return result


def configure(parser):
    parser.add_argument('-o', '--operation', help='Set operation', choices=OPERATIONS.keys(), default='inter')
    parser.add_argument('left', help='Left-side data set')
    parser.add_argument('right', help='Right-side data set')


def main(args):
    left = read_dataset(args.left)
    right = read_dataset(args.right)
    print '\n'.join(OPERATIONS[args.operation](left, right))
