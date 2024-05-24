#include <stdio.h>
#include <string.h> 
#include <pcap/pcap.h> 
#include <ctype.h>
#include <pthread.h> 
#include <stdlib.h>
#include <netinet/ip.h>
#include <net/ethernet.h>
#include <netinet/ether.h> 
#include <netinet/tcp.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

struct tcp_head { 
    unsigned short sport; 
    unsigned short dport; 
    unsigned int seq; 
    unsigned int ack; 
    unsigned char thl : 4; 
    unsigned char reserved: 4; 
};

struct outputs { 
    // MAC addresses should be max 16 char representation
    char s_mac[17];
    char d_mac[17]; 
    // IPv4 addresses should be max 15 char representation.
    char s_ip[16];
    char d_ip[16]; 
    long time; 
    // char *s_port;
    // char *d_port;
};
struct pack_inputs { 
    char *svc;
    char **cap_store;
    int *num;
    struct outputs **output;
    int pipe_fd; 
};
struct mapping { 
    char *svc; 
    char *if_name;
    FILE *fp; 
};
struct mapping** get_svc_mappings(int *size){
    FILE *fp; 
    printf("Entered the function");
    char line[1000];
    // figure out how to arbitrarily add details to mapping 
    fp = popen("./svc_res.sh | grep '^|' | sed 's/^|//' | sort -u","r");
    if (fp == NULL) { 
        printf("Could not resolve mappings."); 
        exit(1); 
    }
    // Read header size 
    if (fgets(line,sizeof(line),fp) != NULL) { 
        *size = atoi(line);
    }
    struct mapping **maps = malloc(sizeof(struct mapping*) * *size);
    printf("There are %d elements\n",*size);
    int i = 0;
    while (fgets(line,sizeof(line),fp) != NULL) {
        printf("Mapping %d: %s",i,line);
        char *token = strtok(line, "|");
        struct mapping* cur = malloc(sizeof(struct mapping)); 
        printf("%p address of cur\n",cur);
        int j = 0;
        while (token != NULL) {
            switch (j){
                // TODO check malloc success
                case 0: 
                    cur->svc = malloc(strlen(token));
                    strcpy(cur->svc,token);    
                    printf("%p -> %s\n",cur->svc,token);
                    break;
                case 1:
                    cur->if_name = malloc(strlen(token));
                    strcpy(cur->if_name,token); 
                    cur->if_name[strcspn(cur->if_name,"\n")] = 0;
                    printf("%p -> %s\n",cur->svc,token);
                    break;
            }
            printf("%d : %s\n",j,token);
            token = strtok(NULL, " ");
            j++;
        }
        printf("cur %p:\nsvc %p -> %s:\nif %p -> %s\n\n",cur,cur->svc,cur->svc,cur->if_name,cur->if_name);
        maps[i++] = cur;
        // TODO could convert to hashmap 
    }
    return maps;
}
void on_packet(u_char *user,const struct pcap_pkthdr* head,const u_char*
        content)
{
    struct pack_inputs* input = (struct pack_inputs*) user; 
    // printf("Struct addresses: %p || %p || %p -> %d\n",&input->svc,input->cap_store,&input->num,*(input->num));
    struct ether_header* eth_h = (struct ether_header*) content; 
    int ether_len = sizeof(struct ether_header); 
    struct ether_addr* smac = (struct ether_addr*) (&eth_h->ether_shost);
    struct ether_addr* dmac = (struct ether_addr*) (&eth_h->ether_dhost);
    printf("FROM DEVICE %s\n",input->svc);
    /* Pointers to start point of various headers */
    const u_char *ip_header;
    const u_char *tcp_header;
    const u_char *payload;

    struct ip* ip_h = (struct ip*) (content + sizeof(struct ether_header)); 
    int iph_len = (ip_h->ip_hl * 4);  
    u_char protocol = ip_h->ip_p;
    ((input->output)[*input->num]) = malloc(sizeof(struct outputs));

    strncpy(((input->output)[*input->num])->s_mac,ether_ntoa(eth_h->ether_shost),16);
    strncpy(((input->output)[*input->num])->d_mac,ether_ntoa(eth_h->ether_dhost),16);
    strncpy(((input->output)[*input->num])->s_ip,inet_ntoa(ip_h->ip_src),15);
    strncpy(((input->output)[*input->num])->d_ip,inet_ntoa(ip_h->ip_dst),15);
    ((input->output)[*input->num])->time = head->ts.tv_sec * (int)1e6 + head->ts.tv_usec;

    (input->cap_store[*input->num]) = malloc(head->caplen);
    memcpy(input->cap_store[*input->num],content,head->caplen);
    *(input->num) = *(input->num) + 1; 
    // for (int i = 0; i<*(input->num);i++){ 
    //     printf("%d : %p\n",i,((input->cap_store)[i]));
    //     printf("%s || %d\n",(inet_ntoa(ip_h->ip_dst)),strlen(inet_ntoa(ip_h->ip_dst)));
    // }
    if (protocol != IPPROTO_TCP) {
        printf("Not a TCP packet. Skipping...\n");
        return;
    }
    struct tcphdr* tcp_h = (struct tcphdr*) (content + sizeof(struct ether_header) + iph_len); 
    int tcph_len = (tcp_h->th_off * 4);
    // printf("TCPHDRLEN = %d___", tcph_len);
    int total_head_len = ether_len + iph_len + tcph_len;
    // printf("Total len C,T,H: %d :: %d :: %d",head->caplen,head->len,total_head_len);
    int payload_len = head->caplen - total_head_len;
    // printf("%u : %u___\n",ntohs(tcp_h->th_sport),ntohs(tcp_h->th_dport));
    // for (size_t i = 0; i < (size_t) head->caplen;i++){ 
    //     printf("%c",isprint(content[i]) ? content[i] : '.');
    // }
    printf("\n");
}

void capture_interface(struct mapping *map){
    char errbuf[PCAP_ERRBUF_SIZE];
    pcap_t *handle; 
    // char fnames[250];
    // snprintf(fnames,250,"./%s_svc.log",map->svc);
    // FILE* log_files = fopen(fnames,"a");
    FILE *log_files = map->fp;
    if (log_files == NULL) { 
        perror("Failed to open log file."); 
        exit(1); 
    };
    printf("Args to interface thread: %s, %s: %d fd\n",map->svc,map->if_name,fileno(log_files));
    // Start a capture on the given interface - NULL -> any 
    // TODO: Should return error or remap if no device is availables
    handle = pcap_open_live(map->if_name, BUFSIZ, 0, 262144, errbuf); 
    if (handle == NULL){ 
        fprintf(stderr, "Couldn't open device %s: %s___", map->if_name, errbuf); 
        exit(EXIT_FAILURE);
    }
    // // Get ethernet headers 
    int ll = pcap_datalink(handle);
    printf("Link layer %d___",ll);
    if (ll != DLT_EN10MB) {
        fprintf(stderr, "Device %s doesn't provide Ethernet headers - not supported___", map->if_name);
        return;
    }   
    fflush(stdout);
    // pcap_set_timeout(handle,100);
    int BATCH_SIZE = 10; 
    while (1){
        printf("Loop %s : %d\n", map->svc,fileno(log_files));
        // This struct should have static references - all 10 packs should access same addresses
        int num = 0;
        char *captured_contents[BATCH_SIZE];
        struct outputs* results[BATCH_SIZE]; 
        struct pack_inputs input = { .svc=map->svc, .cap_store=captured_contents, .num=&num, .output=results};
        pcap_loop(handle,BATCH_SIZE,on_packet,&input);
        fflush(stdout);
        for (int i = 0; i < BATCH_SIZE; i++){ 
            fprintf(log_files,"%s|%s|%s|%s|%s|%ld\n",map->svc,results[i]->s_mac,results[i]->d_mac,results[i]->s_ip,results[i]->d_ip,results[i]->time);
            fflush(log_files);
            // fsync(fileno(log_files));
            if (ferror(log_files)){ 
                printf("Write to pipe failed\n");
            } else { 
                printf("Write to pipe succeeded.\n");
            }
            printf("%d address at %p\n\t %s -> %s\n\t %s -> %s\n",i,(results[i]),(results[i])->s_mac,results[i]->d_mac,results[i]->s_ip,results[i]->d_ip);        
        }
    }
    printf("Closing");
    pcap_close(handle);
    fclose(log_files);
}

int main(int argc, char *argv[])
{   
    int size;
    struct mapping** svcs = get_svc_mappings(&size);
    // printf("SIZE is %d\n",size);
    // Create pipe to write to rule handler.
    char *fifo_name = "traffic_data"; 
    mkfifo(fifo_name,0666);

    // Open write to pipe 
    int fd = open(fifo_name,O_WRONLY);
    // FILE *fp = fopen(fifo_name, "w"  );
    // if (fp == NULL){ 
    if (fd == -1){ 
        perror("Can't open pipe:");
        exit(EXIT_FAILURE);
    }
    FILE *fp = fdopen(fd,"w");
    pthread_t *threads; 
    // Create thread for each k8s network
    if ((threads = malloc(size * sizeof(pthread_t))) == NULL) { 
        perror("Failure in thread initialisation:");
        return(1); 
    };

    for (int i = 0; i < size; i++) { 
        struct mapping *cur = svcs[i]; 
        cur->fp = fp; 
        printf("map %d at %p %s -> %s\n",i,cur,cur->svc, cur->if_name);
        printf("Creating thread for device %s at %p: i is %d\n",cur->if_name,&threads[i],i);
        int ret = pthread_create( &threads[i], NULL, capture_interface, cur);
    }

    // Initialise threads 
    for (int i = 0; i < size; i++){ 
        pthread_join( threads[i], NULL);
    }
    close(fd);
	return(0);
}

