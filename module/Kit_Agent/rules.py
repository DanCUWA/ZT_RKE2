import os
import re
import threading
import subprocess
from utils.DataStructs import Packet
from utils.Service import Service
from utils.FuzzyLogic import RRule
import queue
import sys
import sched
import datetime
from time import sleep, time
import json
sys.path.append("../syscall-monitor")
import msg_handler as rq
# sport:Connection -  should ocassionally wipe
s = sched.scheduler(time,sleep)
msg_q = queue.Queue()
Rfuzz = RRule()
svc_dict = dict()
pod_cidr = ""

def parse_conntrack(conn_str,packet):
    """
    Reverses conntrack mappings used by Calico to retrieve endpoint 
    host addresses from the Calico SNAT.
    """
# tcp      6 82684 ESTABLISHED src=192.168.122.10 dst=10.43.238.254 sport=51682 dport=8003 src=10.42.0.62 dst=10.1.1.243 sport=22 dport=59424 [ASSURED] mark=0 use=1
    # print("SEARCHING FOR ", conn_str)
    patterns = ["src","dst","sport","dport"]
    raw_det = list()
    new_details = list()
    for pattern in patterns: 
        cur_pat = pattern +r"=(\S*) "
        res = re.findall( cur_pat , conn_str)
        raw_det.append(res)
        # print(res)
    if packet.external_port(pod_cidr)[0] == raw_det[1][1]:
        # External ip is first value - new values should be first values
        if packet.external_port(pod_cidr)[0] == packet.sip: 
            packet.sip = raw_det[0][0]
            packet.sport = raw_det[2][0]
        else: 
            packet.dip = raw_det[0][0]
            packet.dport = raw_det[2][0]
        return packet        
        pass
    # print("result is ", raw_det)
    return conn_str + "\n"

def get_connection(pack): 
    """
    Converts a NAT packet to the endpoint addresses.
    """
    command1 = ["conntrack","-L"]
    command2 = ["grep",pack.external_port(pod_cidr)[0]+".*"+pack.external_port(pod_cidr)[1]]  
    # try: 
    p1 = subprocess.Popen(command1, stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    output = subprocess.run(command2, stdin=p1.stdout,stdout=subprocess.PIPE,universal_newlines=True,check=False).stdout
    if output is None or output == "": 
        return pack
    # except CalledProcessError: 
    #     pass
    return parse_conntrack(output,pack)

count_q = queue.Queue()

def get_lines(pipe): 
    """
    Main function for handling packets
    """
    global svc_dict
    global count_q
    total_count = 0 
    # Check packet counts 
    with open(pipe, 'r') as f: 
        print("looping")
        log = open("../logs/py.log",'w')
        log.write(str(datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S:%f"))+"\n")
        # count = 0
        count_q.put(0)
        st = time()
        while True: 
            # Read in data as bytes from pipe 
            data = f.readline()
            start_time = time()
            # Split the string into a list with the necessary 
            #   fields for class parsing.
            # log.write(data + "\n")
            details = data.strip().split("|")
            if len(details) != 10: 
                continue
            pack = Packet(details)
            # print("Packet",pack.ts,"general time",time())
            orig_sip, orig_sport = pack.external_port(pod_cidr)
            get_connection(pack)
            # print(orig_sip,":" ,orig_sport,"-->",pack.sip,pack.sport)
            # continue
            # log.write(str(pack) + "\n")
            # log.write(str(pack.ts) + "\n")

            cur_svc = (svc_dict[pack.svc])
            cur_svc.count += 1
            total_count += 1
            # print(total_count)
            if total_count % 1000 == 0:
                log.write(str(cur_svc.count) + " packets processed.\n")
                log.write(cur_svc.name + ":: " + str(cur_svc.subj_sysc_map) + "\n")
                log.flush()
            cur_svc.log = log

            # Update stored statistics
            cur_svc.stats.enqueue(pack)

            # Train relevant ML instance
            cur_svc.ml.FE.packets.append(pack)
            rmse =  cur_svc.ml.proc_next_packet()
            log.write("RMSE for " + pack.svc + str(cur_svc.ml.FE.curPacketIndx) +  ":" + str(rmse) +"\n")
            
            # Add subject to list of recent for tagging
            subject = pack.external_port(pod_cidr)[0]
            cur_svc.add_recent(subject,pack.ts)
            c = count_q.get()
            count_q.put(c + 1)
            # continue
            # Extract message from queue if one exists
            #   - otherwise pass.
            while not msg_q.empty():
                # TODO Could alter this to retrieve all messages from the queue
                item = msg_q.get(block=False)
                cur_call = item[0]
                alert_time = item[1]
                rel_svc = svc_dict[item[2]]
                print("analysing",item,list(rel_svc.prev_subj.more_recent(0)))
                # New subject trusts are made for the relevant subjects here
                rel_svc.handle_alert(cur_call,alert_time)
                # log.write(" " + str(pack.sip) + " " + str(pack.dip) + cur_svc.name + ":: " + str(cur_svc.subj_sysc_map)+"\n")
            # Evaluate system trust
            obj_trust = rmse
            # Clamp RMSE for fuzzy logic input
            if obj_trust > 1: 
                obj_trust = 1
            subj_trust = cur_svc.subject_trust(subject)

            log.write(str(obj_trust) + ": " + str(pack) + "\n")
            # Pass if the model is still training
            if obj_trust == 0.0: 
                end_time = time()
                log.write("Time " + str(pack.ts) + " " + str(end_time - start_time) + " " + str(time()) + "\n")
                log.write("Count" + str(total_count) + "\n")
                continue
            # log.write(cur_svc.name + str(cur_svc.subj_sysc_map) + "\n")
            # Act on overall request trust
            # print(obj_trust,"vs",subj_trust)
            req_trust = Rfuzz.simulate(obj_trust,subj_trust,log)
            # log.write("Subject trust " + str(subj_trust) + ", Object trust " +
            #           str(obj_trust) + "--> ReqTrust " + str(req_trust) + "\n")
            if req_trust < 5: 
                log.write(" " + str(pack.sip) + " " + str(pack.dip) + cur_svc.name + ":: " + str(cur_svc.subj_sysc_map) + str(obj_trust) + ": " + str(pack) + "\n")
                cur_svc.terminate(orig_sip,orig_sport,log)
            end_time = time()
            log.write("Time " + str(pack.ts) + " " + str(end_time - start_time) + " " + str(time()) + "\n")
            log.write("Count" + str(total_count) + "\n")
            log.flush()
        log.close()
def make_svcs(): 
    global svc_dict
    # global stat_dict
    # global ml_dict
    command1 = ["../scripts/svc_res.sh"]
    p1 = subprocess.Popen(command1, stdout=subprocess.PIPE)
    output = subprocess.check_output(('grep', '^-'), stdin=p1.stdout,universal_newlines=True)
    parsed = [x for x in list(map(lambda x:x.replace('-',''),output.split("\n"))) if x]
    # log.write(parsed)
    # KitNET params - initalisation from Kitsune:
    maxAE = 10 #maximum size for any autoencoder in the ensemble layer
    FMgrace = 5000 #the number of instances taken to learn the feature mapping (the ensemble's architecture)
    ADgrace = 15000
    # ADgrace = 50000 #the number of instances used to train the anomaly detector (ensemble itself)

    for x in parsed: 
        arr = x.split(":")
        svc_dict[arr[0]] = Service(maxAE,FMgrace,ADgrace,arr[0],arr[1])

def get_cidr(): 
    global pod_cidr
    pod_cidr = subprocess.check_output((
        "sudo","kubectl","get","nodes","-o" ,
        "jsonpath={.items[*].spec.podCIDR}")).decode()

def on_recv(channel,method,properties,body): 
    # global prev_time
    fields = json.loads(body.decode())
    # print(fields)
    try: 
        if (fields["output_fields"]["container.name"] in fields["rule"]): 
            # Don't need nanosecond precision
            # time_s = str(int(float(fields["output_fields"]["evt.time"]) / 1000000000))

            msg_q.put([fields["output_fields"]["syscall.type"],fields["output_fields"]["evt.rawtime.s"],fields["output_fields"]["container.name"]])
            # print("Added",[fields["output_fields"]["syscall.type"],fields["output_fields"]["evt.rawtime.s"],fields["output_fields"]["container.name"]])
    except KeyError: 
        print("Error", fields)
        return 
    
def retrieve(): 
    temp = rq.AMQPConnection()
    print("Formed AMQP Connection...")
    # sleep(10)
    while(1):
        print("Consuming")
        temp.channel.basic_consume(queue="events",on_message_callback=on_recv,auto_ack=True)
        temp.channel.start_consuming()
    temp.connection.close()

def adjust_trust(): 
    global subj_sysc_map
    global svc_dict
    for svc in svc_dict:
        sysc_map = (svc_dict[svc]).subj_sysc_map
        for subject in sysc_map:
            sysc_map[subject]["trust"] += 0.5 
            if sysc_map[subject]["trust"] >= 1:
                sysc_map[subject]["trust"] = 1

    print("Increased trusts at ", time())

def count_packs():
    global count_q
    # print("Running count Thread")
    if count_q.empty():
        print("No packets in the last minute since",datetime.datetime.now().time())
    else: 
        c = count_q.get()
        print(c,"packets in the last minute since",datetime.datetime.now().time())
        count_q.put(0)

def repeat_count(): 
    s.enter(5,1,count_packs)
    s.enter(5,1,repeat_count)

def repeat(): 
    # TODO Update for hour
    rep_time = 3600
    s.enter(rep_time,1,adjust_trust)
    s.enter(rep_time,1,repeat)

def run_sched():
    # repeat_count()
    repeat()
    s.run()

def main(): 
    # Communication with scrape.c occurs
    #   through the "traffic_data" pipe. 
    threading.Thread(target=retrieve).start()
    
    # Start the process to update subject trusts every hour. 
    threading.Thread(target=run_sched).start()
    pipe = "../traffic_data"
    while not os.path.exists(pipe):
        pass  
    get_cidr()
    make_svcs()
    # print(svc_dict)
    get_lines(pipe)        
    os.unlink(pipe)  

if __name__ == "__main__":
    print(os.getcwd())
    main()
    # maxAE = 10 #maximum size for any autoencoder in the ensemble layer
    # FMgrace = 100 #the number of instances taken to learn the feature mapping (the ensemble's architecture)
    # ADgrace = 1000 #the number of instances used to train the anomaly detector (ensemble itself)
    # threading.Thread(target=retrieve).start()
    # while True:
    #     if not msg_q.empty():
    #         a = msg_q.get()
    #         print("recv alert",a,"at",time())
