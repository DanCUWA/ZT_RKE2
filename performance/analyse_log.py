from argparse import ArgumentParser
import matplotlib.pyplot as plt
import numpy as np
from analysis_funcs import (
    get_groups_from_analyser,get_group_times,parse_log_file,
    parse_attack_file,get_average_atk_delay,analyse_comparison
)

def main(): 
    parser = ArgumentParser()
    parser.add_argument("file", help="Path of file to anlayse")
    parser.add_argument("-a","--attack-file",help="Path of file containing the attack logs")
    args = parser.parse_args()
    results = parse_log_file(args.file)
    atks = parse_attack_file(args.attack_file,results.start_time)
    get_average_atk_delay(atks)
    all_groups = get_groups_from_analyser(results,atks,results.start_time)
    print("ANALYSER COUNT",results.total_count)
    zt_rke2_group = get_group_times(all_groups,results.start_time)
    comp_analyser = analyse_comparison("../module/Kit_Agent/100k_minimal.log")
    comp_groups = get_groups_from_analyser(comp_analyser,atks,results.start_time)
    print("ANALYSER COUNT",comp_analyser.total_count)
    kit_group = get_group_times(comp_groups,results.start_time)
    # print("ZT_RKE2 GROUPS")
    # for i in all_groups: 
    #     print("(( ",i,end=" ))")
    # print("COMPARISON GROUPS")
    # for i in kit_group: 
    #     print("(( ",i,end=" ))")
    # from 22:15 to 23:05 
    # Create the line plot
    values = range(0, 3600)
    ground_truths = dict()
    for atk in atks.all: 
        ground_truths[int(atk.ts - results.start_time)] = atk.get_class()
    # Create a list to store the corresponding values
    plot_values = []
    net_atks = []
    host_atks = []
    all_atks = []
    comp_vals = []
    for value in values:
        if any(start <= value <= end for start, end in zt_rke2_group):
            plot_values.append(1)
        else:
            plot_values.append(None)
        if any(start <= value <= end for start, end in kit_group):
            comp_vals.append(1.25)
        else:
            comp_vals.append(None)

        if value in ground_truths:
            all_atks.append(0.25)
            if ground_truths[value] == "Network": 
                net_atks.append(0.75)
                host_atks.append(None)
            else: 
                host_atks.append(0.5)
                net_atks.append(None)
        else:
            net_atks.append(None)
            all_atks.append(None)
            host_atks.append(None)

    # print("Values",plot_values)
    plt.figure(figsize=(20,10))
    plt.plot(values, plot_values, drawstyle='steps-post',markersize=3,marker='o',label="Detected Attacks")
    plt.plot(values, host_atks, drawstyle='steps-post',color="orange",markersize=3,marker='o',label="Host Attacks")
    plt.plot(values, all_atks, drawstyle='steps-post',color="green",markersize=3,marker='o',label="All Attacks")
    plt.plot(values, net_atks, drawstyle='steps-post',color="red",markersize=3,marker='o',label="Network Attacks")
    plt.plot(values, comp_vals, drawstyle='steps-post',color="purple",markersize=3,marker='o',label="General model")
    plt.xlabel("Time since start (seconds)")

    plt.ylabel("Attack Category")
    plt.xticks(np.arange(0,3600,step=600))
    plt.yticks(np.arange(0,2,step=0.5))
    plt.legend()
    plt.title("Analysis of ZT-RKE2 model")
    # plt.savefig(f'out/31_8_{time.strftime("%Y%m%d-%H%M%S")}.png')
    # plt.show()


if __name__ == "__main__": 
    # analyse_comparison("../module/Kit_Agent/50k_minimal.log")
    main()
    