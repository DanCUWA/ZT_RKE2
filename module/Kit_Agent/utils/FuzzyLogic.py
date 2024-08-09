# pip install -U scikit-fuzzy matplotlib
# https://oleg-dubetcky.medium.com/mastering-fuzzy-logic-in-python-c90463bf1135
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
class SRule:
    def __init__(self):
        # Step 1: Define the fuzzy sets for input variables (cost and benefit)
        likelihood = ctrl.Antecedent(np.arange(1, 4, 1), 'likelihood')
        # Past indication that subject is malicious 
        sub_malig = ctrl.Antecedent(np.arange(0, 1.1, 0.1), 'sub_malig')
        # Chance that current abnormal call is also malicious
        sysc_malig = ctrl.Antecedent(np.arange(0, 1.1, 0.1), 'sysc_malig')

        # Membership functions for cost and benefit


        likelihood['unlikely'] = fuzz.trimf(likelihood.universe, [0, 0, 1])
        likelihood['plausible'] = fuzz.trimf(likelihood.universe, [1, 1, 2])
        likelihood['likely'] = fuzz.trimf(likelihood.universe, [2, 2, 3])

        sub_malig['low'] = fuzz.trimf(sub_malig.universe, [0, 0.2, 0.4])
        sub_malig['moderate'] = fuzz.trimf(sub_malig.universe, [0.3, 0.5, 0.7])
        sub_malig['high'] = fuzz.trimf(sub_malig.universe, [0.6, 0.8, 1])

        sysc_malig['unique'] = fuzz.trimf(sysc_malig.universe, [0, 0.2, 0.4])
        sysc_malig['common'] = fuzz.trimf(sysc_malig.universe, [0.3, 0.5, 0.7])
        sysc_malig['ubiquitous'] = fuzz.trimf(sysc_malig.universe, [0.6, 0.8, 1])

        # TODO change numberical values below 
        # Step 2: Define the fuzzy sets for output variable (cost benefit)
        subj_trust = ctrl.Consequent(np.arange(0, 11, 1), 'subject_trust')

        # Membership functions for subject_trust
        subj_trust['low'] = fuzz.trimf(subj_trust.universe, [0, 2, 5])
        subj_trust['medium'] = fuzz.trimf(subj_trust.universe, [3, 5, 7])
        subj_trust['high'] = fuzz.trimf(subj_trust.universe, [5, 10, 10])

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
        print(rules)


        # # Step 4: Implement the fuzzy inference system

        subj_trust_ctrl = ctrl.ControlSystem(rules) 
        self.subj_trust_sim = ctrl.ControlSystemSimulation(subj_trust_ctrl)

    # # Step 5: Test the fuzzy logic system with sample inputs
    # cost_benefit_sim.input['cost'] = 3  # low cost
    # cost_benefit_sim.input['benefit'] = 8  # high benefit

    def simulate(self,l,s,y):
        self.subj_trust_sim.input['likelihood'] = l
        self.subj_trust_sim.input['sub_malig'] = s
        self.subj_trust_sim.input['sysc_malig'] = y
        self.subj_trust_sim.compute()
        print("Subject trust is ", self.subj_trust_sim.output['subject_trust'])


# test = SRule()
# test.simulate(1,0.34,0.8)
    # print("Cost Benefit: ", cost_benefit_sim.output['cost_benefit'])

class RRule:
    def __init__(self):
        # Step 1: Define the fuzzy sets for input variables (cost and benefit)
        object_trust = ctrl.Antecedent(np.arange(0, 1.1, 0.01), 'o_trust')
        subject_trust = ctrl.Antecedent(np.arange(0, 1.1, 0.1), 's_trust')

        # Membership functions for cost and benefit

        # Clamp object trust rmse 
        object_trust['low'] = fuzz.trimf(object_trust.universe, [0, 0.1, 0.2])
        object_trust['moderate'] = fuzz.trimf(object_trust.universe, [0.17, 0.3, 0.45])
        object_trust['high'] = fuzz.trimf(object_trust.universe, [0.4, 0.8, 1])

        subject_trust['low'] = fuzz.trimf(subject_trust.universe, [0, 0.2, 0.4])
        subject_trust['moderate'] = fuzz.trimf(subject_trust.universe, [0.3, 0.5, 0.7])
        subject_trust['high'] = fuzz.trimf(subject_trust.universe, [0.6, 0.8, 1])

        # TODO change numberical values below 
        # Step 2: Define the fuzzy sets for output variable (cost benefit)
        request_trust = ctrl.Consequent(np.arange(0, 11, 1), 'r_trust')

        # Membership functions for subject_trust
        request_trust['low'] = fuzz.trimf(request_trust.universe, [0, 2, 5])
        request_trust['medium'] = fuzz.trimf(request_trust.universe, [3, 5, 7])
        request_trust['high'] = fuzz.trimf(request_trust.universe, [5, 10, 10])

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

        print(rules_list)
        for oi,ot in enumerate(['low', 'moderate','high']):
            for si,st in enumerate(['low', 'moderate','high']):
                print(oi, si )
                rules_list[oi][si] = (ot + "|" + st)
                rules.append(ctrl.Rule(object_trust[ot] & subject_trust[st], request_trust[trust_list[ot][st]]))

        print(rules_list)
        # print(rules)


        # # Step 4: Implement the fuzzy inference system

        req_trust_ctl = ctrl.ControlSystem(rules) 
        self.req_trust_sim = ctrl.ControlSystemSimulation(req_trust_ctl)

    # # Step 5: Test the fuzzy logic system with sample inputs
    # cost_benefit_sim.input['cost'] = 3  # low cost
    # cost_benefit_sim.input['benefit'] = 8  # high benefit

    def simulate(self,o,s):
        self.req_trust_sim.input['o_trust'] = o
        self.req_trust_sim.input['s_trust'] = s
        self.req_trust_sim.compute()
        print("Request trust is ", self.req_trust_sim.output['r_trust'])
    
RRule()