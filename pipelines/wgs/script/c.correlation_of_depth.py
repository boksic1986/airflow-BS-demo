#! /bi/software/micromamba/bin/python
# _*_ coding: utf-8 _*_
import os
import argparse
import pandas as pd
import seaborn as sns
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
def get_options():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-i', '--input', required=True, type=str)
    parser.add_argument('-o', '--output', required=True, type=str) 
    args=parser.parse_args()
    return {'input':args.input,'output':args.output}

def main():
    input_message=get_options()
    corr=os.path.abspath(input_message['input'])
    png_file=os.path.abspath(input_message['output'])
    data = pd.read_csv(corr)
    plt.figure(figsize=(10, 10))
    ax = sns.heatmap(data, cmap = 'OrRd', linewidths = 0.02, vmin=0.6, vmax=1)
    ax.set_title('Correlation between depths', fontsize=10, position=(0.5,1.05))
    ax.tick_params(axis='y',labelsize=8)
    ax.tick_params(axis='x',labelsize=8)
    plt.savefig(png_file, bbox_inches = 'tight')
if __name__ == "__main__":
    main()
