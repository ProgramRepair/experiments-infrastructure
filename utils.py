import itertools
import subprocess

# helper things that Python inexplicably doesn't define 
def flatten(l):
    for el in l:
        if isinstance(el, collections.Iterable) and not isinstance(el, basestring):
            for sub in flatten(el):
                yield sub
        else:
            yield el

def partition(pred, iterable):
    'Use a predicate to partition entries into false entries and true entries'
    # partition(is_odd, range(10)) --> 0 2 4 6 8   and  1 3 5 7 9
    t1, t2 = itertools.tee(iterable)
    return list(itertools.ifilterfalse(pred, t1)), list(filter(pred, t2))

def extendf(lst1,lst2):
    lst1.extend(lst2)
    return lst1

def appendf(lst1,newarg):
    lst1.append(newarg)
    return lst1

def enum(**enums):
    return type('Enum', (), enums)

def popen(cmd):
    return subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE)
