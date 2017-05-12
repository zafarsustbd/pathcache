#!/usr/bin/python
import mkit.ripeatlas.probes as ripeprobes
import mkit.inference.ixp as ixp
import mkit.ripeatlas.parse as parse
import mkit.inference.ippath_to_aspath as asp
import pdb
import urllib
import urllib2
import json
import datetime
import settings
import os
import math
from graph_tool.all import *
import os
import settings
import pyasn
from ripe.atlas.sagan import TracerouteResult
from ripe.atlas.cousteau import Measurement,Probe
import pickle
import numpy as np

API_HOST = 'https://atlas.ripe.net/'
URI = 'api/v2/measurements'

all_graphs={}
count = 1
msms ={}
node_count = {}

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
    MX = max(node_count.values())
    for first, second in zip(p, p[1:]):
        e = gr.edge(first, second)
        asn_t = gr.vp.asn[e.target()]
        p_e = p_n = 1 
        if asn_t in node_count:
            if node_count[asn_t]!=0:
                p_n = node_count[asn_t]/float(MX)
        if gr.ep.prob[e]!=0:
            p_e = gr.ep.prob[e]
            prob += math.log(p_e*p_n)
        print 'asn: ', asn_t, ' p_e: ', p_e, ' p_n: ', p_n
    return prob

def get_path( src, dst):
    if dst in all_graphs:
        gr = all_graphs[dst]
        # Find all paths from src to dst in this graph
        src_node = find_vertex(gr, gr.vp.asn, int(src))
        if not src_node:
            return None
        src_node = src_node[0]
        dst_node = find_vertex(gr, gr.vp.asn, int(dst))
        assert dst_node
        dst_node = dst_node[0]
        src_dst_paths = dfs_paths(gr, src_node, dst_node)
        #first = next(src_dst_paths, None)
        #if not first:
        #    print "Could not find a path from data plane measurements."
        #    src_dst_paths = dfs_paths(gr, src_node, dst_node)
        paths = []
        c = 0
        for p in src_dst_paths:
            c += 1
            if c > 10000:
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

def get_most_probable_path(src, dst, threshold=2):
    paths = get_path(src, dst)
    paths = sorted(paths, key=lambda x: x[0], reverse=True)
    paths = paths[:threshold]
    final_paths = []
    for p in paths:
        final_paths.append(p[1])
    return final_paths

def fetch_json( page ):
    data = []
    api_args = dict(description__startswith="ACCURACY_PC",page=str(page), type="traceroute" )
    url = API_HOST+URI+"/?"+urllib.urlencode( api_args )
    print url
    response = urllib2.urlopen( url )
    data = json.load( response )
    return data

def path_in_cache( src, dst ):
    if dst in all_graphs:
        gr = all_graphs[dst]
        src = find_vertex(gr, gr.vp.asn, src)
        if src:
            return True
    return False

def path_cache(src, dst, threshold=2):
    if not path_in_cache(src, dst):
        return []
    paths = get_most_probable_path(src, dst, threshold=threshold)
    #hops = []
    #for p in paths:
    #    hops.extend(p)
    #hops = list(frozenset(hops))
    #return hops
    return paths


def fetch_results_msmid(msm_id):
    result_url=API_HOST+URI+'/'+str(msm_id)+'/results'
    try:
        response = urllib2.urlopen(result_url)
    except:
        raise ValueError("URL fetch error on : "+ result_url)
    data_result=response.read().decode()
    data_json=json.loads(data_result)
    if len(data_json)!=0:
        #print len(data_json)
        #print msm_id
        data_json=data_json[0]
        #pdb.set_trace()
        for res in data_json['result']:
            res['result']=[r for r in res['result'] if 'edst' not in r]
        tr_result=TracerouteResult(data_result[1:-1])
        return tr_result,data_json
    else:
        return None,None



if __name__=="__main__":
    overestimate_list_pc = []
    underestimate_list_pc = []
    threshold=3
    total = 0
    exact=0
    same = 0
    shorter = 0
    longer = 0
    one_error = two_error = three_error = four_error = 0

    asndb = pyasn.pyasn(settings.IPASN_DB)
    with open('all_graphs.pkl', 'rb') as f:
        all_graphs= pickle.load(f)
    node_count = np.load('node_count.npy').item()

    while( 1 ):
        try:
            data = fetch_json( page=count )
        except urllib2.HTTPError:
            break
        if not data[ 'results' ]:
            break
        for d in data['results']:
            if d['id']:
                msm_id=d['id']
                tr_result,data_json=fetch_results_msmid(msm_id)
                if data_json!=None:
                    msms[msm_id]=[tr_result.probe_id,tr_result.destination_address,data_json]
        count += 1
        if count>4: break
    print len(msms)
    for msm in msms:
        data = msms[msm][2]
        #print data
        #print msms[msm][1].__class__
        #print msms[msm][0].__class__
        #pdb.set_trace()
        src_asn = int(ripeprobes.get_probe_asn(msms[msm][0]))
        dst_asn = int(asndb.lookup(msms[msm][1])[0])
        if not path_in_cache(src_asn, dst_asn): continue
        aslinks = asp.traceroute_to_aspath(data)
        if not aslinks['_links']: continue
        aslinks = ixp.remove_ixps(aslinks)
        hops = []
        for link in aslinks:
            hops.append(int(link['src']))
        hops.append(int(link['dst']))
        real_path = set(hops)
        if not hops:
            continue
        pc_paths = path_cache(int(src_asn), int(dst_asn), threshold)
        print 'PathCache Output: ', pc_paths
        print 'Ripe Output: ', hops
        for pc_path in pc_paths:
            total += 1
            if real_path == set(pc_path):
                exact += 1
            elif (len(real_path- set(pc_path)) + len(set(pc_path) - real_path))==1:
                one_error+=1
            elif (len(real_path- set(pc_path)) + len(set(pc_path) - real_path))==2:
                two_error+=1
            elif (len(real_path- set(pc_path)) + len(set(pc_path) - real_path))==3:
                three_error+=1
            elif (len(real_path- set(pc_path)) + len(set(pc_path) - real_path))==4:
                four_error+=1

            if len(real_path) == len(pc_path) and real_path != set(pc_path):
                same += 1
            elif len(real_path) > len(pc_path):
                shorter += 1
            else:
                longer += 1
            overestimate = len(set(pc_path) - real_path)
            underestimate = len(real_path - set(pc_path))
            overestimate_list_pc.append(overestimate)
            underestimate_list_pc.append(underestimate)
    print 'Total: ', total, ' exact: ', exact, ' 1E: ', one_error, ' 2E: ', two_error, ' 3E:', three_error, ' 4E: ', four_error, ' same: ', same, ' shorter: ', shorter, ' longer: ', longer
    #pdb.set_trace()
    """
    with open("cipollino-verify/over_estimate_exit_dest_pc", "w") as fi:
        json.dump(overestimate_list_pc, fi)

    with open("cipollino-verify/under_estimate_exit_dest_pc", "w") as fi:
        json.dump(underestimate_list_pc, fi)
    """
