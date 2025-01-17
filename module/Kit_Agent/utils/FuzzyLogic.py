# pip install -U scikit-fuzzy matplotlib
# https://oleg-dubetcky.medium.com/mastering-fuzzy-logic-in-python-c90463bf1135
import numpy as np
from time import sleep
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from datetime import datetime
##### 
# CHANGE VIEW TO BELOW 
# def view(self, fname,*args, **kwargs):
#     """""" + FuzzyVariableVisualizer.view.__doc__
#     fig, ax = FuzzyVariableVisualizer(self).view(*args, **kwargs)
#     fig.savefig(fname)
#     fig.show()
#####
class SRule:
    def __init__(self):
        # Step 1: Define the fuzzy sets for input variables (cost and benefit)
        likelihood = ctrl.Antecedent(np.arange(0, 2.5, 0.5), 'likelihood')
        # Past indication that subject is malicious 
        sub_malig = ctrl.Antecedent(np.arange(0, 1.1, 0.1), 'sub_malig')
        # Chance that current abnormal call is also malicious
        sysc_malig = ctrl.Antecedent(np.arange(0, 1.1, 0.1), 'sysc_malig')

        # Membership functions for cost and benefit

        # TRIANGULAR MEMBERSHIP FUNCTIONS 
        # low index is more likely 
        likelihood['likely'] = fuzz.trimf(likelihood.universe, [0, 0, 1])
        likelihood['plausible'] = fuzz.trimf(likelihood.universe, [0.5, 1, 1.5])
        likelihood['unlikely'] = fuzz.trimf(likelihood.universe, [1, 2, 2])

        # sub_malig['low'] = fuzz.trimf(sub_malig.universe, [0, 0.1, 0.4])
        # sub_malig['moderate'] = fuzz.trimf(sub_malig.universe, [0.3, 0.5, 0.7])
        # sub_malig['high'] = fuzz.trimf(sub_malig.universe, [0.6, 1, 1])

        # sysc_malig['unique'] = fuzz.trimf(sysc_malig.universe, [0, 0.1, 0.4])
        # sysc_malig['common'] = fuzz.trimf(sysc_malig.universe, [0.3, 0.5, 0.7])
        # sysc_malig['ubiquitous'] = fuzz.trimf(sysc_malig.universe, [0.6, 1.0, 1])

        ### TRAPEZOIDAL MEMBERSHIP FUNCTIONS 
        # likelihood['unlikely'] = fuzz.trapmf(likelihood.universe, [0, 0.4,0.8,1.2])
        # likelihood['plausible'] = fuzz.trapmf(likelihood.universe, [0.8, 1.3, 1.8, 2.2])
        # likelihood['likely'] = fuzz.trapmf(likelihood.universe, [1.8, 2.3, 2.7,3.1])

        sub_malig['low'] = fuzz.trapmf(sub_malig.universe, [0, 0, 0.2, 0.4])
        sub_malig['moderate'] = fuzz.trapmf(sub_malig.universe, [0.2, 0.4,0.6, 0.8])
        sub_malig['high'] = fuzz.trapmf(sub_malig.universe, [0.6,0.8,1, 1])

        sysc_malig['unique'] = fuzz.trapmf(sysc_malig.universe, [0, 0,0.2, 0.4])
        sysc_malig['common'] = fuzz.trapmf(sysc_malig.universe, [0.2, 0.4,0.6, 0.8])
        sysc_malig['ubiquitous'] = fuzz.trapmf(sysc_malig.universe, [0.6,0.8,1, 1])

        # TODO change numberical values below 
        # Step 2: Define the fuzzy sets for output variable (cost benefit)
        subj_trust = ctrl.Consequent(np.arange(0, 1.1, 0.1), 'subject_trust')

        # Membership functions for subject_trust
        subj_trust['low'] = fuzz.trapmf(subj_trust.universe, [0, 0, 0.2, 0.4])
        subj_trust['medium'] = fuzz.trapmf(subj_trust.universe, [0.2,0.4,0.5, 0.7])
        subj_trust['high'] = fuzz.trapmf(subj_trust.universe, [0.5,0.7, 0.8, 1])


        #### MAPPINGS OF FUZZY VARIABLES TO SUBJECT TRUSTS
        [[['unlikely|low|unique', 'unlikely|low|common', 'unlikely|low|ubiquitous'],
        ['unlikely|moderate|unique', 'unlikely|moderate|common', 'unlikely|moderate|ubiquitous'],
        ['unlikely|high|unique', 'unlikely|high|common', 'unlikely|high|ubiquitous']],

        [['plausible|low|unique', 'plausible|low|common', 'plausible|low|ubiquitous'],
        ['plausible|moderate|unique', 'plausible|moderate|common', 'plausible|moderate|ubiquitous'],
        ['plausible|high|unique', 'plausible|high|common', 'plausible|high|ubiquitous']],

        [['likely|low|unique', 'likely|low|common', 'likely|low|ubiquitous'],
        ['likely|moderate|unique', 'likely|moderate|common', 'likely|moderate|ubiquitous'],
        ['likely|high|unique', 'likely|high|common', 'likely|high|ubiquitous']]]
        #### CORRESPONDING SUBJECT TRUST - low trust is bad, high is good
        # all unique syscalls must be assumed to be malicious, so assigned low trust is subject is responsible
        trust_list = [[['medium', 'high', 'high'],
        ['medium', 'high', 'high'],
        ['medium', 'medium', 'high']],
        
        [['medium', 'high', 'high'],
        ['medium', 'medium', 'high'],
        ['low', 'medium', 'medium']],
        # Chance they are responsible; proportion of abnormal syscalls ; frequency of executed syscall in other subjects
        [['low', 'medium', 'high'],
        ['low', 'medium', 'medium'],
        ['low', 'low', 'low']]]

        # Make rules table
        # # Step 3: Define the fuzzy rules from the above table 
        rules_list = [[['' for k in range(3)] for j in range(3)] for i in range(3)]
        rules = list()
        for li,l in enumerate(['unlikely', 'plausible', 'likely']):
            for si,sub in enumerate(['low', 'moderate','high']):
                for syi,sysc in enumerate(['unique','common','ubiquitous']):
                    rules_list[li][si][syi] = l + "|" + sub + "|" +sysc + "->" + trust_list[li][si][syi]
                    rules.append(ctrl.Rule(likelihood[l] & sub_malig[sub]& sysc_malig[sysc], subj_trust[trust_list[li][si][syi]]))
        # print(rules_list)
        # print(rules)

        # # Step 4: Implement the fuzzy inference system

        subj_trust_ctrl = ctrl.ControlSystem(rules) 
        self.subj_trust_sim = ctrl.ControlSystemSimulation(subj_trust_ctrl)
        # likelihood.view(fname="./like.png")
        # sub_malig.view(fname="./subject.png")
        # sysc_malig.view(fname="./sysc.png")
        # subj_trust.view(fname="./strust.png")

    # # Step 5: Test the fuzzy logic system with sample inputs
    # cost_benefit_sim.input['cost'] = 3  # low cost
    # cost_benefit_sim.input['benefit'] = 8  # high benefit

    def simulate(self,l,s,y,log=None):
        self.subj_trust_sim.input['likelihood'] = l
        self.subj_trust_sim.input['sub_malig'] = s
        self.subj_trust_sim.input['sysc_malig'] = y
        # if log is not None: 
            # log.write("Values for previous: likelihood " + str(l) + " sub_malig " + str(s) + " sysc_malig " + str(y) + "\n")
        try:
            self.subj_trust_sim.compute()
            # print(l,s,y,"succeeded.")
            # print(l,s,y,"-->",self.subj_trust_sim.output['subject_trust'])
            # if log is not None: 
            #     log.write("Likelihood "+ str(l) + " sub malig "+ str(s) + "sysc malig "+ str(y) + "--->\n\t "+ str(self.subj_trust_sim.output) + "\n" )
            return self.subj_trust_sim.output['subject_trust']
        except Exception:
            print(l,s,y,"failed.")
            return 1


# test = SRule()
# test.simulate(1,0.34,0.8)
    # print("Cost Benefit: ", cost_benefit_sim.output['cost_benefit'])

class RRule:
    def __init__(self):
        # Step 1: Define the fuzzy sets for input variables (cost and benefit)
        object_trust = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'o_trust')
        subject_trust = ctrl.Antecedent(np.arange(0, 1.1, 0.1), 's_trust')
        # print(np.arange(0, 1.01, 0.01))
        # Membership functions for cost and benefit
        # print(np.arange(0, 1, 0.1))

        # Clamp object trust rmse 
        object_trust['high'] = fuzz.trapmf(object_trust.universe, [0,0, 0.1, 0.3])
        object_trust['moderate'] = fuzz.trapmf(object_trust.universe, [0.1, 0.3,0.4, 0.5])
        object_trust['low'] = fuzz.trapmf(object_trust.universe, [0.4,0.5, 1, 1])

        subject_trust['low'] = fuzz.trapmf(subject_trust.universe, [0, 0, 0.2, 0.4])
        subject_trust['moderate'] = fuzz.trapmf(subject_trust.universe, [0.2,0.4,0.5, 0.7])
        subject_trust['high'] = fuzz.trapmf(subject_trust.universe, [0.5,0.7, 1, 1])

        # TODO change numberical values below 
        # Step 2: Define the fuzzy sets for output variable (cost benefit)
        request_trust = ctrl.Consequent(np.arange(0, 11, 1), 'r_trust')

        # Membership functions for subject_trust
        request_trust['low'] = fuzz.trapmf(request_trust.universe, [0, 0, 2, 4])
        request_trust['medium'] = fuzz.trapmf(request_trust.universe, [2, 3, 5, 7])
        request_trust['high'] = fuzz.trapmf(request_trust.universe, [6, 8, 10, 10])

        #### MAPPINGS OF FUZZY VARIABLES TO SUBJECT TRUSTS

        #### CORRESPONDING SUBJECT TRUST - low trust is bad, high is good
        # all unique syscalls must be assumed to be malicious, so assigned low trust is subject is responsible


        # Make rules table


        # # Step 3: Define the fuzzy rules from the above table 
        rules_list = [['' for k in range(3)] for j in range(3)]
        # Object | Subject trusts
        [['low|low', 'low|moderate', 'low|high'],
        ['moderate|low', 'moderate|moderate', 'moderate|high'],
        ['high|low', 'high|moderate', 'high|high']]
        # Resulting Request trusts
        trust_list = [['low', 'low', 'low'],
        ['low', 'medium', 'high'],
        ['medium', 'high', 'high']]
        rules = list()
        # print(rules_list)
        for oi,ot in enumerate(['low', 'moderate','high']):
            for si,st in enumerate(['low', 'moderate','high']):
                print(ot, st,"-->",request_trust[trust_list[oi][si]])
                rules_list[oi][si] = (ot + "|" + st)
                rules.append(ctrl.Rule(object_trust[ot] & subject_trust[st], request_trust[trust_list[oi][si]]))
        # print(rules)

        # print(rules_list)
        # print(rules)
        # subject_trust.view('./s_trust.png')
        # object_trust.view('./o_trust.png')
        # request_trust.view('./r_trust.png')

        # # Step 4: Implement the fuzzy inference system

        req_trust_ctl = ctrl.ControlSystem(rules) 
        self.req_trust_sim = ctrl.ControlSystemSimulation(req_trust_ctl)

    # # Step 5: Test the fuzzy logic system with sample inputs
    # cost_benefit_sim.input['cost'] = 3  # low cost
    # cost_benefit_sim.input['benefit'] = 8  # high benefit

    def simulate(self,o,s,log=None):
        self.req_trust_sim.input['o_trust'] = o
        self.req_trust_sim.input['s_trust'] = s 
        # print("Trying values ",o,s)
        self.req_trust_sim.compute()
        # print(o,s,"--->",self.req_trust_sim.output['r_trust'])
        result = self.req_trust_sim.output['r_trust']
        if log is not None and result < 5:
            log.write("Request trust is " + str(self.req_trust_sim.output['r_trust']) + " from object trust" + str(o)  + " and subject trust" + str(s)  + " at " + datetime.now().strftime("%d/%m/%Y %H:%M:%S:%f"))
                # +"\n" )         
        # print("Request trust is ", self.req_trust_sim.output['r_trust'], " from object trust", o , " and subject trust", s )
        return result
    
# SRule().simulate(1,0.8,0.8)
# RRule().simulate(0.0,5.1)
r = RRule()
# for o in np.arange(0, 1.01, 0.01):
#     for s in np.arange(0, 1.1, 0.1):
#         r.simulate(o,s)
# sr = SRule()
# # sleep(5)
# # while True:
# #     continue
# for l in np.arange(0, 3, 1):
#     for s in np.arange(0, 1.1, 0.1):
#         for y in np.arange(0, 1.1, 0.1):
#             sr.simulate(l,s,y)
