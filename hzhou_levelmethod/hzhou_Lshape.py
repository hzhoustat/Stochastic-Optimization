import cPickle
from gurobipy import *

### This file was generated from a separate python file, using the `cPickle' module
### This is just for convenience -- data can be read in many ways in Python

dfile = open('forest41031.pdat','r')

B = cPickle.load(dfile)  # set of base locations (list of strings) 
F = cPickle.load(dfile)  # set of fire districts (list of strings)
S = cPickle.load(dfile)  # set of scenarios (list of strings0
c = cPickle.load(dfile)  # dictionary of cost parameters c[i,j] is unit cost to relocate from i in B to j in B 
h = cPickle.load(dfile)  # dictionary or purchase params, h[i] is unit cost to add new resource at i in B
init = cPickle.load(dfile)  # dictionary of initial resource placements, init[i] is amt of resource at i in B
closesets = cPickle.load(dfile)  # dictionary of "close enough sets". closesets[f] is a list of base locations (subset of B)
demscens = cPickle.load(dfile)  # dictionary of demand scnearios. demscens[s,f] is demand of resource in scenario s at district f 
costscens = cPickle.load(dfile) # dictionary of cost scenarios. costscnes[s,f] is cost of resource shortage in scenario s at district f
budget = 500.0   ### hard coded here!!!
dfile.close() 

### NoTE: demscens and costscens are very sparse. In particular, for a given s, there are only one or two districts f
### that have nonzero demscens vals (and only these have costscens vals, since without demand there is no need for a cost param)
### Here I define the set of keys which exist in these sets

SFkeys = demscens.keys()
SFkeys = tuplelist(SFkeys)  ## make tuplelist for easy selection

### it may also be useful to have a "reverse" version of the dictionary closesets, which provides for each facility i in
### B, the set of districts it can serve. This is constructed here
closedists = {}
for i in B:
    closedists[i] = []

for f in F:
    for i in closesets[f]:
        closedists[i].append(f)

##### This is just a check of the data. Probably you want to comment/delete these lines once you see the structure 
##
##print B 
##print F 
##print S 
##print c 
##print h
##print init
##print closesets
##print demscens
##print costscens
##print budget

nscen=float(len(S))

##### Master problem #####
master=Model("master")
master.params.logtoconsole=0
### Theta
Theta=master.addVar(obj=1,name='Theta') 

### reposition
trans={}
for i,j in c:
    trans[i,j]=master.addVar(obj=0,name='Trans_from%s_to%s' % (i,j))

### expand
epd = {}
for b in B:
    epd[b] = master.addVar(obj=0, name='Expand %s' % b )

master.modelSense = GRB.MINIMIZE
master.update()

master.addConstr(Theta >= 0,name='Nonnegative')
master.addConstr(
    quicksum(trans[i,j]*c[i,j] for i,j in c)+quicksum(epd[b]*h[b] for b in B) == budget, name='budget')
for b in B:
    master.addConstr(
        init[b]+epd[b]+quicksum(trans[i,b] for i in B)-quicksum(trans[b,i] for i in B)>=0,name='StationNonnegative')
master.update()


### Subproblem
sub=Model("seasonflow")
sub.params.logtoconsole=0

### demand unmet
unmet = {}
for f in F:
    unmet[f] = sub.addVar(obj=0, name='Unmet%s' % f )

### flow
flow = {}
for f in closesets:
    for b in closesets[f]:
        flow[b,f] = sub.addVar(obj=0, name='Flow_%s_%s' % (b,f))
# The objective is to minimize the total fixed and variable costs
sub.modelSense = GRB.MINIMIZE 
sub.update()

### Demand constraints
demcon={}
for f in F:
    demcon[f] = sub.addConstr(
        quicksum(flow[b,f] for b in closesets[f]) + unmet[f] >= 0,name='Demand_%s' % f )

### station constraints
stacon={}
for b in B:
    stacon[b]=sub.addConstr(
        quicksum(flow[b,f] for f in closedists[b]) <= init[b],name='Station_%s' % b )
sub.update()

# Begin the single-cut loop
cutfound = 1  ## keep track if violated
iter = 1
upper_bound=100000
while cutfound:
    print '================ Iteration ', iter, ' ==================='
    iter = iter+1
    # Solve current master problem
    cutfound = 0 
    master.update()
    master.optimize()
    print 'lower bound (objval) = ', master.objVal  
        # Fix the right-hand side in subproblem constraints according to each scenario and master solution, then solve
    for b in B:
        stacon[b].RHS = init[b]+epd[b].x+sum(trans[i,b].x for i in B)-sum(trans[b,i].x for i in B)
    sec_obj=0
    rhs_D=0
    rhs_B={}
    for b in B:
        rhs_B[b]=0
    for s in S:
        for f in F:
            if (s,f) in SFkeys.select(s,'*'):
                demcon[f].RHS = demscens[s,f]
            else:
                demcon[f].RHS = 0
        for f in F:
            if (s,f) in SFkeys.select(s,'*'):
                unmet[f].obj = costscens[s,f]
            else:
                unmet[f].obj = 0
        sub.update()
        sub.optimize()
        for b in B:
            rhs_B[b] += stacon[b].pi
        for s,f in SFkeys.select(s,'*'):
            rhs_D += demcon[f].pi*demscens[s,f]
        # Display info, compute Benders cut, display, add to master 
        sec_obj +=1/nscen*sub.objVal
    rhs_D=rhs_D/nscen
    for b in B:
        rhs_B[b]=rhs_B[b]/nscen
    upper_bound = min(sec_obj,upper_bound)
    if upper_bound > master.objVal + 0.000001:  ### violation tolerance
        master_rhs = rhs_D
        for b in B:
            master_rhs +=(init[b]+epd[b])*rhs_B[b]
        for i,j in c:
            master_rhs +=(rhs_B[j]-rhs_B[i])*trans[i,j]
        master.addConstr(Theta>=master_rhs)
        cutfound = 1
##    for i,j in c:
##        print trans[i,j].x
##    for b in B:
##        print epd[b].x
    print 'upper bound = ', upper_bound
