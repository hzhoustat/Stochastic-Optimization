import cPickle
from gurobipy import *
import time
import math

### Read data from file you choose: commont/uncomment to choose the different files
### This file was generated from a separate python file, using the `cPickle' module
### This is just for convenience -- data can be read in many ways in Python

dfile = open('nd151020500.pdat','r')
##dfile=open('nd1041015.pdat','r')

Fset = cPickle.load(dfile)  # set of facilities (list of strings)
Hset = cPickle.load(dfile)  # set of warehouses (list of strings)
Cset = cPickle.load(dfile)  # set of customers (list of strings)
Sset = cPickle.load(dfile)  # set of scenarios (list of strings)
arcExpCost = cPickle.load(dfile)  # arc expansion costs (dictionary mapping F,H and H,C pairs to floats)
facCap = cPickle.load(dfile)   # facility capacities (dictionary mapping F to floats) 
curArcCap = cPickle.load(dfile)  # current arc capacities (dictionary mapping (i,j) to floats, where either 
                                 # i is facility, j is warehouse, or i is warehouse and j is customer
unmetCost = cPickle.load(dfile)  # penalty for unment customer demands (dicationary mapping C to floats)
demScens = cPickle.load(dfile)  # demand scenarios (dictionary mapping (i,k) tuples to floats, where i is customer, k is
                                #scenario
numscen=len(Sset)
avarweight = 0.5
alpha = 0.95
dfile.close() 


### Define sets of arcs (used as keys to dictionaries)
FHArcs = [(i,j) for i in Fset for j in Hset]  ## arcs from facilities to warehouses
HCArcs = [(i,j) for i in Hset for j in Cset]   ## arcs from warehouses to customers
AllArcs = FHArcs + HCArcs

### Make them Gurobi tuplelists
FHArcs = tuplelist(FHArcs)
HCArcs = tuplelist(HCArcs)
AllArcs = tuplelist(AllArcs)

def Single_scen(capcost,demscens):
    ms=Model("Single_scen")
    ms.params.logtoconsole=0
    ship={}
    for i,j in AllArcs:
        ship[i,j]=ms.addVar(obj=0)
    nscen=numscen
    unmet = {}
    for c in Cset:
        unmet[c] = ms.addVar(obj=float(unmetCost[c]))
    ms.modelSense = GRB.MINIMIZE
    ms.update()
    Edge_dual={}
    for i,j in AllArcs:
        Edge_dual[i,j]=ms.addConstr(ship[i,j]-capcost[i,j] <= curArcCap[i,j])
    for h in Hset:
        ms.addConstr(
            quicksum(ship[i,h] for i,h in FHArcs.select('*',h))-quicksum(ship[h,j] for h,j in HCArcs.select(h,'*'))>=0)
    for c in Cset:
        ms.addConstr(
            quicksum(ship[h,c] for h,c in HCArcs.select('*',c)) + unmet[c] >= demscens[c])
    for f in Fset:
        ms.addConstr(
            quicksum(ship[f,h] for f,h in FHArcs.select(f,'*'))<= facCap[f])
    ms.update()
    ms.optimize()
    obj=0
    for i,j in AllArcs:
        obj += capcost[i,j]*arcExpCost[i,j]
    obj += ms.objval
    capcost_grad={}
    for i,j in AllArcs:
        capcost_grad[i,j] = arcExpCost[i,j]+Edge_dual[i,j].pi
    return [obj,capcost_grad]

def Mu_generate(scen_values):
    mufun=Model("Mu_generator")
    mufun.params.logtoconsole=0
    mu={}
    for k in Sset:
        obj_value=scen_values[k]
        mu[k]=mufun.addVar(obj= - obj_value,lb=0,ub=7.33/float(numscen))
    mufun.update()
    mufun.addConstr(quicksum(mu[k] for k in Sset)==1)
    mufun.update()
    mufun.optimize()
    mu_value={}
    for k in Sset:
        mu_value[k]=mu[k].x
    return mu_value

def Grad_generate(scen_grads,mu):
    capcost_grad={}
    for i,j in AllArcs:
        capcost_grad[i,j]=0
    for k in Sset:
        capcost_curgrad={}
        for i,j in AllArcs:
            capcost_curgrad[i,j]=scen_grads[i,j,k]
        for i,j in AllArcs:
            capcost_grad[i,j]+=capcost_curgrad[i,j]*mu[k]
    return capcost_grad

def Whole_scens(scen_values,mu):
    obj=0
    for k in Sset:
        obj_value=scen_values[k]
        obj+=obj_value*mu[k]
    return obj

##master=Model("master_problem")
##Theta=master.addVar(obj=1,lb=0,name="Theta")
##capcost_var={}
##for i,j in AllArcs:
##    capcost_var[i,j]=master.addVar(obj=0,lb=0)
##master.update()
##
##cutfound =1
##iteration =1
##while cutfound:
##    print '================ Iteration ', iteration, ' ==================='
##    iteration = iteration+1
##    cutfound=0
##    master.update()
##    master.optimize()
##    lowerbound=master.objval
##    capcost={}
##    for i,j in AllArcs:
##        capcost[i,j]=capcost_var[i,j].x
##    scen_values={}
##    scen_grads={}
##    for k in Sset:
##        scen={}
##        for c in Cset:
##            scen[c]=demScens[c,k]
##        [obj_value,grad_value]=Single_scen(capcost,scen)
##        scen_values[k]=obj_value
##        for i,j in AllArcs:
##            scen_grads[i,j,k]=grad_value[i,j]
##    mu=Mu_generate(scen_values)
##    upperbound=Whole_scens(scen_values,mu)
##    if upperbound > lowerbound +0.000001:
##        cutfound = 1
##        capcost_grad=Grad_generate(scen_grads,mu)
##        master.addConstr(Theta>=upperbound+quicksum(capcost_grad[i,j]*(capcost_var[i,j]-capcost[i,j]) for i,j in AllArcs))
##
##pk={}
##for k in Sset:
##    pk[k]=1/float(numscen)
##EZ=Whole_scens(scen_values,pk)
##AVaR=2*(lowerbound*(1+0.5)-EZ)
##print 'Expected cost ', EZ, 'Average value at risk ', AVaR
capcost={}
for i,j in AllArcs:
        capcost[i,j]=0
for iteration in range(10):
    print"---",iteration
    tt=iteration
    tt=float(tt)
    scen_values={}
    scen_grads={}
    for k in Sset:
        scen={}
        for c in Cset:
            scen[c]=demScens[c,k]
        [obj_value,grad_value]=Single_scen(capcost,scen)
        scen_values[k]=obj_value
        for i,j in AllArcs:
            scen_grads[i,j,k]=grad_value[i,j]
    mu=Mu_generate(scen_values)
    capcost_grad=Grad_generate(scen_grads,mu)
    for i,j in AllArcs:
        capcost[i,j]-=math.pow(tt,0.75)*capcost_grad[i,j]
        if capcost[i,j]<=0:
            capcost[i,j]=0
    print Whole_scens(scen_values,mu)
