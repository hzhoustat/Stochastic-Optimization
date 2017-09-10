from gurobipy import *
import time
import numpy
import math

### Base data

T=5  ## (Number of stages)
fracoutcomes = [0.05,0.1,0.15] ## set of possible fraction destroyed outcomes in each period
start_treenum = {}
start_treenum[0,1] = 8000
start_treenum[0,2] = 10000
start_treenum[0,3] = 20000
start_treenum[0,4] = 60000
yield_num = {}
yield_num[2] = 250
yield_num[3] = 510
yield_num[4] = 710

Nodes = []
NodeStage = {}
StageNodes = {}
NodeChildren = {}
NodeFracHist = {}
### Initialize Model
m = Model("Tree")

### Initialize with root node
curnodeid = 1
Nodes.append(curnodeid)
NodeStage[curnodeid]=1
StageNodes[1] = [curnodeid]
NodeFracHist[curnodeid]=[0.0] 
NodeChildren[1] = []

### Add root node variable
treenum = {}
for i in range(1,5):
    treenum[1,i] = m.addVar(obj = 0, name='Tree_Node_1_Class_%g' % i)
cutnum = {}
for i in range(2,5):
    cutnum[1,i] = m.addVar(obj = 0, name='Cut_Node_1_Class_%g' % i)
yielding = {}
yielding[1] = m.addVar(obj =0, name='Yielding_Node_1')
m.update()
### Add root node constraint
m.addConstr(yielding[1]==quicksum(yield_num[i]*cutnum[1,i] for i in range(2,5)))
m.addConstr(treenum[1,1] == quicksum(cutnum[1,i] for i in range(2,5)))
m.addConstr(treenum[1,2] == start_treenum[0,1])
m.addConstr(treenum[1,3] == start_treenum[0,2]-cutnum[1,2])
m.addConstr(treenum[1,4] == start_treenum[0,3]+start_treenum[0,4]-cutnum[1,3]-cutnum[1,4])
m.addConstr(start_treenum[0,3] >= cutnum[1,3])
m.addConstr(start_treenum[0,4] >= cutnum[1,4])
m.update()
### Build the tree moving forward in stages
for t in range(2,T+1): ## 2...T
    StageNodes[t] = []
    if t == T:
        unmet = {}
    for n in StageNodes[t-1]:
        for f in fracoutcomes:
            curnodeid+=1
            NodeFracHist[curnodeid]=NodeFracHist[n]+[f]
            NodeChildren[n] += [curnodeid]
            NodeChildren[curnodeid]=[]
            NodeStage[curnodeid]=t
            StageNodes[t]+=[curnodeid]
            Nodes+=[curnodeid]
            ### Add Variable
            for i in range(1,5):
                treenum[curnodeid,i] = m.addVar(obj = 0, name='Tree_Node_%g_Class_%g' % (curnodeid,i))
            for i in range(2,5):
                cutnum[curnodeid,i] = m.addVar(obj = 0, name='Cut_Node_%g_Class_%g' % (curnodeid,i))
                yielding[curnodeid] = m.addVar(obj = 0, name='Yielding_Node_%g' % curnodeid)
            m.update()
            ### Add Constraint
            m.addConstr(yielding[curnodeid]==yielding[n]+quicksum(yield_num[i]*cutnum[curnodeid,i] for i in range(2,5)))
            m.addConstr(treenum[curnodeid,1] == quicksum(cutnum[curnodeid,i] for i in range(2,5)))
            m.addConstr(treenum[curnodeid,2] == treenum[n,1]+f*quicksum(treenum[n,i] for i in range(2,5)))
            m.addConstr(treenum[curnodeid,3] == (1-f)*treenum[n,2]-cutnum[curnodeid,2])
            m.addConstr(treenum[curnodeid,4] == (1-f)*treenum[n,3]+(1-f)*treenum[n,4]-cutnum[curnodeid,3]-cutnum[curnodeid,4])
            m.addConstr((1-f)*treenum[n,3] >= cutnum[curnodeid,3])
            m.addConstr((1-f)*treenum[n,4] >= cutnum[curnodeid,4])
            m.update()
            if t == T:
                unmet[curnodeid,1] = m.addVar(obj = -10, name='Less than 98 million')
                unmet[curnodeid,2] = m.addVar(obj = -7, name='Less than 105 million')
                unmet[curnodeid,3] = m.addVar(obj = 5, name='More than 105 million')
                m.update()
                m.addConstr(yielding[curnodeid]+unmet[curnodeid,1] >= 98000000)
                m.addConstr(yielding[curnodeid]+unmet[curnodeid,1]+unmet[curnodeid,2] >= 105000000+unmet[curnodeid,3])
                m.update()
m.modelSense = GRB.MAXIMIZE
m.optimize()
Finalobj = (m.objVal/81.0 + 10*98000000 +7*7000000)/100.0
print('\n Final objective:%f dollars' % Finalobj)

####
##### The following recursively defined function gets all leaf nodes (which correspond to scenarios) that originate from a node n
##def getLeafs(n):
##	if NodeStage[n] == T:
##		return [n]
##	else:
##		tmp = []
##		for c in NodeChildren[n]:
##			tmp += getLeafs(c)	
##		return tmp
##
##### The full set of scenarios corresponds to the set of node indices that are Leafs in the tree from node 1
##Scens = getLeafs(1)
##
####
####### Let's see what we have! 
####
####### here is the full observation in each scenario (path through tree)
####for n in Scens:
####	print(NodeFracHist[n])
####
####Nscen = len(Scens)
####print("number of scenarios: %d" % Nscen)
####
####### print the node indices in each stage
####for t in range(1,T+1):
####	print(StageNodes[t])
####
###### as an example, let's pick out node 3 and look at key information:
####print("Node 3 time stage: %d" % NodeStage[3])
####print("Node 3 scenarios that share this same history:")
####print(getLeafs(3))
####
