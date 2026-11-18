#!/usr/bin/env python3
"""Streaming ideal-cost reduction on the compute worker, before gzip publication."""
import csv

THREADS = (1, 2, 4, 6, 8, 12)
HEADER = ['graph', 'algo', 'variant', 'filter', 'threads', 'delta', 'source', 'phase',
          'bucket', 'heavy', 'frontier', 'expanded', 'edges', 'max_vertex_edges']


def summarize(stream):
    reader = csv.reader(stream)
    if next(reader, None) != HEADER:
        raise ValueError('invalid phase header')
    result, seen, current = [], set(), None
    for row in reader:
        if len(row) != len(HEADER):
            raise ValueError('malformed phase row')
        key = tuple(row[:7])
        if key != current:
            if key in seen:
                raise ValueError('noncontiguous phase run')
            seen.add(key)
            current = key
            record = dict(zip(HEADER[:7], key), phases=0, edges=0,
                          ideal={str(k): 0 for k in THREADS}, ideal_no_max={str(k): 0 for k in THREADS})
            result.append(record)
        edges, maximum = int(row[12]), int(row[13])
        if int(row[7]) != record['phases'] or not 0 <= maximum <= edges:
            raise ValueError('invalid phase index or edge counters')
        record['phases'] += 1
        record['edges'] += edges
        for k in THREADS:
            share = (edges + k - 1) // k
            record['ideal'][str(k)] += max(share, maximum)
            record['ideal_no_max'][str(k)] += share
    if not result:
        raise ValueError('empty phase log')
    return result
