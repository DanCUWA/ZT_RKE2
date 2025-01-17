#!/bin/bash

<<description 

This script is responsible for mapping the name of a kubernetes service to the 
interface of the pod that supports it, necessary for the libpcap scraping.
Kubernetes provides no way to do this directly at time of writing, so below
is an implementation relying on the calico utilisation of iptables to redirect traffic. 

First, we identify all services present on the host machine using the kubectl. These 
service names are then related to the ports on which they are hosted, and combined into 
a svc:port string. The endpoints of the pods can be obtained through the Kubernetes CLI, 
and the interface names can then be determined from those names. 

description
# Find user-defined services in the default namespace.
SERVICE_DETAILS=$(sudo kubectl get services -o=custom-columns=NAME:.metadata.name,PORTS:.spec.ports[*].port | tail -n +2 | grep -v '^kubernetes ' | tr -s [:space:])
# Hold svc:port mappings.
MAPPINGS=()
# Uses internal ports, so should work for both clusterIP's and NodePorts.
for i in $(sudo kubectl get services -o=custom-columns=NAME:.metadata.name,PORTS:.spec.ports[*].port | tail -n +2 | grep -v '^kubernetes ' | tr -s [:space:] | tr ' ' '|') 
	do SVC_NAME=$(echo "$i" | cut -d'|' -f 1) 
	PORTS=$(echo "$i" | cut -d'|' -f 2)
	for i in $(echo "$PORTS" | tr ',' ' ')
		do 
		echo "-$SVC_NAME:$i"
		MAPPINGS+=( "$SVC_NAME:$i" )
	done
done
# Use the iptables rules (calico svc implementation) to get the pod address of the relevant service. 
RULES=$(sudo iptables -t nat -L)
IF_DETAILS=$(ip a) 
SEARCH_STR="";
OUTPUT=""
# Get details about interfaces for all relevant services.
for i in ${MAPPINGS[@]}; do
	CUR_SVC=$(echo "$i" | cut -d: -f 1)
	EP_OUT=$(sudo kubectl get endpoints -o=custom-columns=NAME:.metadata.name,EP:.subsets..addresses..ip,PNAME:.subsets..addresses..targetRef..name | grep "$CUR_SVC" | tr -s '[:space:]')
	IP=$(echo "$EP_OUT" | cut -d' ' -f 2)
	POD_NAME=$(echo "$EP_OUT" | cut -d' ' -f 3)
	# echo "Episode is $EP_OUT - IP is $IP - Pod name is $POD_NAME" 
	# IP=$(echo "$RULES" |  grep "$i" | grep all | grep -oE '([0-9]{1,4}\.){3}[0-9]{1,4}' | sort -u)
	# POD_NAME=$(sudo kubectl get pods -o=custom-columns=NAME:.metadata.name,IP:.status.podIP | tr -s [:space:] | tail -n +2 | grep $IP | cut -d' ' -f 1)
	# Get interface name from pods. 
	IF_NUM=$(sudo kubectl exec "$POD_NAME" -- cat /sys/class/net/eth0/iflink )
	IF_NAME=$(echo "$IF_DETAILS" | grep "^$IF_NUM" | cut -d':' -f 2 | cut -d'@' -f 1 | tr -d '[:space:]') 
	SVC=$(echo $i | cut -d':' -f 1)
	echo "Mapping service $SVC: $i --> $IP --> $POD_NAME --> $IF_NUM --> $IF_NAME"; 
	# echo "|$SVC|$IF_NAME"
	if [[ $OUTPUT == "" ]]; then
		OUTPUT="|$SVC|$IF_NAME"
	else
		OUTPUT="$OUTPUT"$'\n'"|$SVC|$IF_NAME"
	fi
	#if [ -z "$SEARCH_STR" ]; then 
	#	echo "Empty string"
	#	SEARCH_STR="$i"
	#else
	#	SEARCH_STR="$SEARCH_STR\|$i"
	#fi 
done
# Print the results starting with '|' to facilitate parsing.
echo "|$(echo "$OUTPUT" | sort -u | wc -l)" 
for i in $(echo "$OUTPUT" | sort -u); do
	echo "$i"
done

