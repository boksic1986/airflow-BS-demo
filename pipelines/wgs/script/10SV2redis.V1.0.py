#!/usr/bin/env python  
# -*- coding:utf-8 _*-
""" 
@author:Rzhang 
@license: Apache Licence 
@file: 10SV2redis.V1.0.py 
@time: 2024/01/22
@contact: zhiangrian@126.com
@site:  
@software: PyCharm 
"""

# !/usr/bin/env python3
import argparse
import os
import redis
import re
import pandas as pd


def load_sv(svFile, redis_host, redis_port, redis_password):
    SampleName = ""
    baseInfile = os.path.basename(svFile)
    if re.match(r'(.*?)-WGS\.SV.sort\.tsv', baseInfile):
        SampleName = re.match(r'(.*?)-WGS\.SV.sort\.tsv', baseInfile).group(1)
    r = redis.Redis(host = redis_host, port = redis_port, password = redis_password, decode_responses = True)
    svData = pd.read_csv(svFile, sep = '\t', header = 'infer')
    for index, row in svData.iterrows():
        hash = {}
        score = 0
        pos1 = row['染色体位置']
        pos2 = row['染色体位置2']
        svtype = row['SVTYPE']
        SV_ID = f"{pos1}-{pos2}-{svtype}"
        SV_ID = SV_ID.replace(':', '__').replace('-', '__')
        hash['ReferenceV'] = "hg38"
        if svtype == "BND":
            chr1, start1, end1, chr2, start2, end2, stype = SV_ID.split('__')
            ID = f"{SampleName}-{chr1}-{start1.zfill(9)}-{end1.zfill(9)}-{chr2}-{start2.zfill(9)}-{end2.zfill(9)}-{svtype}"
        else:
            chr1, start1, end1, pos2, stype = SV_ID.split('__')
            ID = f"{SampleName}-{chr1}-{start1.zfill(9)}-{end1.zfill(9)}-.-{svtype}"
        print(ID)
        variantdict = {}
        if 'SVTYPE' in ID:
            pass
        else:
            redisKey = SampleName + '-SV'
            variantdict[ID] = score
            r.hdel(ID, 'ReferenceV')
            r.hmset(ID, hash)
            r.zrem(f"{SampleName}-SV", ID)
            r.zadd(redisKey, {ID: score})
    print("Done load", svFile)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Load SV file into Redis database.")
    parser.add_argument("--sv", dest = "svFile", required = True, help = "SV file")
    parser.add_argument("--host", dest = "redis_host", default = "172.17.61.99", help = "Redis host")
    parser.add_argument("--port", dest = "redis_port", default = 6481, type = int, help = "Redis port")
    parser.add_argument("--password", dest = "redis_password", default = "BioSan", help = "Redis password")

    args = parser.parse_args()

    if not args.svFile:
        parser.print_help()
        exit(1)

    load_sv(args.svFile, args.redis_host, args.redis_port, args.redis_password)
