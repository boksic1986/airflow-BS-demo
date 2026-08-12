#!/usr/bin/env python  
# -*- coding:utf-8 _*-
""" 
@author:Rzhang 
@license: Apache Licence 
@file: imprintRegion.py 
@time: 2023/08/02
@contact: zhiangrian@126.com
@site:  
@software: PyCharm 
"""
import sys


def imprintRegion(inputfile, outfile):
    imprint_region = ["6q24.2", "7q32.2", "11p15", "14q32.2", "15q11.2", "15q12", "15q13.1", "15q13.2", "15q13.3", "20q11.1", "20q11.21", "20q11.22", "20q11.23", "20q12", "20q13.11", "20q13.12",
                      "20q13.13", "20q13.2", "20q13.31", "20q13.32", "20q13.33"]
    f2 = open(outfile, 'w')
    with open(inputfile, 'rb') as fp:
        for line in fp:
            line = line.decode('utf-8')
            line = line.strip('\r\n')
            arhead = line.split('\t')
            cytobandlist = []
            chr = arhead[0].replace("chr", "")
            cytoband = arhead[6]
            if "," in cytoband:
                cytobandlist = cytoband.split(",")
                chrlist = [chr] * len(cytobandlist)
                newlist = [x + y for x, y in zip(chrlist, cytobandlist)]
                interlist = sorted(list(set(newlist).intersection(set(imprint_region))))
                newcytoband = cytobandlist[0] + "-" + cytobandlist[-1]

            else:
                cytobandlist.append(cytoband)
                chrlist = [chr] * len(cytobandlist)
                newlist = [x + y for x, y in zip(chrlist, cytobandlist)]
                interlist = list(set(newlist).intersection(set(imprint_region)))
                newcytoband = cytoband
            if len(interlist) > 0:
                f2.write("\t".join(arhead[0:6]) + "\t" + newcytoband + '\t' + ','.join(interlist) + '\n')
            else:
                f2.write("\t".join(arhead[0:6]) + "\t" + newcytoband + '\t' + "NO" + '\n')
    f2.close()


if __name__ == '__main__':
    imprintRegion(sys.argv[1], sys.argv[2])
