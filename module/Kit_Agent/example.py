from Kitsune import Kitsune
import numpy as np
import time
from argparse import ArgumentParser

##############################################################################
# Kitsune a lightweight online network intrusion detection system based on an ensemble of autoencoders (kitNET).
# For more information and citation, please see our NDSS'18 paper: Kitsune: An Ensemble of Autoencoders for Online Network Intrusion Detection

# This script demonstrates Kitsune's ability to incrementally learn, and detect anomalies in recorded a pcap of the Mirai Malware.
# The demo involves an m-by-n dataset with n=115 dimensions (features), and m=100,000 observations.
# Each observation is a snapshot of the network's state in terms of incremental damped statistics (see the NDSS paper for more details)

#The runtimes presented in the paper, are based on the C++ implimentation (roughly 100x faster than the python implimentation)
###################  Last Tested with Anaconda 3.6.3   #######################

# Load Mirai pcap (a recording of the Mirai botnet malware being activated)
# The first 70,000 observations are clean...
# print("Unzipping Sample Capture...")
# import zipfile
# with zipfile.ZipFile("mirai.zip","r") as zip_ref:
#     zip_ref.extractall()


# File location
path = "/home/dc/ZT_RKE2/performance/50_sample_14_9.pcap.tsv" #the pcap, pcapng, or tsv file to process.
packet_limit = np.inf #the number of packets to process
parser = ArgumentParser()
# parser.add_argument("file", help="Path of file to anlayse")
parser.add_argument("-f","--from_path",help="Path of file to analyse")
parser.add_argument("-t","--to_path",help="Path of file to write to")
args = parser.parse_args()
print("From",args.from_path,"to",args.to_path)
path = args.from_path
to_path = args.to_path
# exit()
# KitNET params:
maxAE = 10 #maximum size for any autoencoder in the ensemble layer
FMgrace = 5000 #the number of instances taken to learn the feature mapping (the ensemble's architecture)
ADgrace = 15000 #the number of instances used to train the anomaly detector (ensemble itself)

# Build Kitsune
K = Kitsune(path,packet_limit,maxAE,FMgrace,ADgrace,online=False)

print("Running Kitsune:")
RMSEs = []
i = 0
start = time.time()
loop_time = time.time()
# Here we process (train/execute) each individual packet.
# In this way, each observation is discarded after performing process() method.
with open(to_path,'w') as f:
    while True:
        i+=1
        pack_time = time.time()
        if i % 1000 == 0:
            cur_time = time.time()
            print(i,"in",cur_time - loop_time)
            loop_time = cur_time
        # elif i >= 100000:
        #     print("Cancelling")
        #     break
        rmse = K.proc_next_packet(f)
        # print(rmse)
        if rmse == -1:
            break
        # elif rmse >= 0.4: 
        #     print("Error noticed ")
        end_time = time.time()
        f.write(str(rmse) + "\n")
        RMSEs.append(rmse)
        f.write("Time " + str(end_time - pack_time) + "\n")
stop = time.time()
print("Complete. Time elapsed: "+ str(stop - start))


# Here we demonstrate how one can fit the RMSE scores to a log-normal distribution (useful for finding/setting a cutoff threshold \phi)
from scipy.stats import norm
benignSample = np.log(RMSEs[FMgrace+ADgrace+1:100000])
logProbs = norm.logsf(np.log(RMSEs), np.mean(benignSample), np.std(benignSample))

# plot the RMSE anomaly scores
print("Plotting results")
from matplotlib import pyplot as plt
from matplotlib import cm
plt.figure(figsize=(10,5))
fig = plt.scatter(range(FMgrace+ADgrace+1,len(RMSEs)),RMSEs[FMgrace+ADgrace+1:],s=0.1,c=logProbs[FMgrace+ADgrace+1:],cmap='RdYlGn')
plt.yscale("log")
plt.title("Anomaly Scores from Kitsune's Execution Phase")
plt.ylabel("RMSE (log scaled)")
plt.xlabel("Time elapsed [min]")
figbar=plt.colorbar()
figbar.ax.set_ylabel('Log Probability\n ', rotation=270)
# plt.show()
plt.savefig("output_y.png")
