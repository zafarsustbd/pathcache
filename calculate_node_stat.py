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
import pickle

all_graphs = {}

files = [ x for x in os.listdir( settings.GRAPH_DIR_FINAL ) \
          if os.path.isfile( os.path.join( settings.GRAPH_DIR_FINAL, x ) ) ]
files = [ os.path.join( settings.GRAPH_DIR_FINAL, f ) for f in files ]
TOTAL_MMT_PER_SRC = 20
node_count = {}
node_freq = {}

for f in files:
    asn = f.split( '/' )[ -1 ].split('.')[0]
    #print "COMBIBED graph for ASN", asn
    gr = load_graph(f, fmt="gt")
    #print gr
    cnt = 0
    for v in gr.vertices():
        cnt += 1
    #print cnt
    #pdb.set_trace()
    if cnt not in node_freq:
        node_freq[cnt] = 0
    node_freq[cnt] += 1

for key, value in node_freq.iteritems():
    print key, ',' , value

    '''
    remove_parallel_edges(gr)
    remove_self_loops(gr)
    overall_origins = {}
    for e in gr.edges():
        origin_dict = gr.ep.origin[e]
        
        asn_s = gr.vp.asn[e.source()]
        asn_t = gr.vp.asn[e.target()]
        if asn_s not in node_count:
            node_count[asn_s] = 0
        if asn_t not in node_count:
            node_count[asn_t] = 0
        node_count[asn_s] += 1
        node_count[asn_t] += 1
    cnt = len(node_count)
    if cnt not in
    '''
