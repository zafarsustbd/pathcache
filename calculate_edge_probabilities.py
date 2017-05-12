#!/usr/bin/python
import math
import json
from networkx.readwrite import json_graph
import networkx as nx
import pdb
from graph_tool.all import *
import os
import settings
import numpy as np
import graph_tool as gt

all_graphs = {}
files = [ x for x in os.listdir( settings.GRAPH_DIR_FINAL ) \
          if os.path.isfile( os.path.join( settings.GRAPH_DIR_FINAL, x ) ) ]
files = [ os.path.join( settings.GRAPH_DIR_FINAL, f ) for f in files ]
TOTAL_MMT_PER_SRC = 20

ugr = None
for i in range(1):
    f = files[i]
    asn = f.split( '/' )[ -1 ].split('.')[0]
    print "COMBIBED graph for ASN", asn
    gr = load_graph(f, fmt="gt")
    if ugr == None:
        ugr = gr
    else:
        #val = int64_t(1)
        ugr = graph_union(ugr, gr)#, ugr.vp.asn)
ugr.set_directed(False)
graph_draw(ugr, directed=False,  output = "graphdraw.png")
pdb.set_trace()

for f in files:
    asn = f.split( '/' )[ -1 ].split('.')[0]
    #print "COMBIBED graph for ASN", asn
    gr = load_graph(f, fmt="gt")

    graph_draw(gr, output = "graphdraw.png")
    
    remove_parallel_edges(gr)
    remove_self_loops(gr)
    overall_origins = {}
    #pos = gt.random_layout(gr)

    pdb.set_trace()
    for e in gr.edges():
        origin_dict = gr.ep.origin[e]
        for src in origin_dict:
            if src not in overall_origins:
                overall_origins[src] = 0
            overall_origins[src] += origin_dict[src]
    for e in gr.edges():
        origin_dict = gr.ep.origin[e]
        origin_dict_new = {}
        for src in origin_dict:
            origin_dict_new[src] = \
                                   (float(origin_dict[src])*TOTAL_MMT_PER_SRC)/overall_origins[src]
        gr.ep.origin[e] = origin_dict_new
    #eprop_prob = gr.new_edge_property("float")
    #gr.ep.prob = eprop_prob
    #for e in gr.edges():
        #origin_dict = gr.ep.origin[e]
        #prob_src = 1.0/len(overall_origins)
        #e_prob = 0
        #for src in origin_dict:
        #    e_prob += (prob_src * origin_dict[src])/TOTAL_MMT_PER_SRC
        #gr.ep.prob[e] = e_prob
    all_graphs[int(asn)] = gr
#np.save('all_graphs.npy', all_graphs)

#all_graphs = np.load('all_graphs.npy').item()
print 'all graphs loaded'

def dfs_paths(gr, src_node, dst_node):
    visited = set()
    stack = [(src_node, [src_node])]
    while stack:
        (vertex, path) = stack.pop()
        visited.add(vertex)
        for next in set(vertex.out_neighbours()):
            if next in visited:
                continue
            if next == dst_node:
                yield path + [next]
            else:
                stack.append((next, path + [next]))
def get_path_prob(p, gr):
    prob = 0
    for first, second in zip(p, p[1:]):
        e = gr.edge(first, second)
        prob += math.log(gr.ep.prob[e])
    return prob

def get_path( src, dst):
    print src, dst
    if dst in all_graphs:
        print 'dst found in all_graph'
        gr = all_graphs[dst]
        # Find all paths from src to dst in this graph
        src_node = find_vertex(gr, gr.vp.asn, int(src))
        #if not src_node:
        #    return None
        print "SRC Node: ", src_node
        src_node = src_node[0]
        print "SRC Node idx: ", src_node
        dst_node = find_vertex(gr, gr.vp.asn, int(dst))
        print "DST Node: ", dst_node
        #assert dst_node
        dst_node = dst_node[0]
        print "DST Node idx: ", dst_node
        src_dst_paths = dfs_paths(gr, src_node, dst_node)
        #first = next(src_dst_paths, None)
        #if not first:
        #    print "Could not find a path from data plane measurements."
        #    src_dst_paths = dfs_paths(gr, src_node, dst_node)
        paths = []
        count = 0
        for p in src_dst_paths:
            count += 1
            if count > 10000:
                break
            pr = get_path_prob(p, gr)
            paths.append((pr, p))
        paths_sorted = sorted(paths, key=lambda x:x[0], reverse=True)
        paths_sorted = paths_sorted[:10]
        final_paths = []
        for prob, p in paths_sorted:
            path_ases = [gr.vp.asn[x] for x in p]
            final_paths.append((prob, path_ases))
        return final_paths
    else:
        return []

def get_most_probable_path(src, dst):
    paths = get_path(src, dst)
    print paths
    paths = sorted(paths, key=lambda x: x[0], reverse=True)
    paths = paths[:5]
    final_paths = []
    for p in paths:
        final_paths.append(p[1])
    return final_paths

#pdb.set_trace()
#paths = get_most_probable_path("101.0.33.0_24","101.0.64.0_18")
paths = get_most_probable_path(5719,3333)
print "len: ", len(paths), "Path: ", paths
#paths = get_most_probable_path(2119, 4608)
#print "len: ", len(paths), "Path: ", paths
#paths = get_most_probable_path(3265, 3333)
print "len: ", len(paths), "Path: ", paths


