import cPickle
from gurobipy import *

### Read data from file you choose: commont/uncomment to choose the different files
### This file was generated from a separate python file, using the `cPickle' module
### This is just for convenience -- data can be read in many ways in Python

dfile = open('nd10-4-10-15.pdat','r')
#dfile = open('nd30-10-20-3000.pdat','r')

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
dfile.close() 


### Define sets of arcs (used as keys to dictionaries)
FHArcs = [(i,j) for i in Fset for j in Hset]  ## arcs from facilities to warehouses
HCArcs = [(i,j) for i in Hset for j in Cset]   ## arcs from warehouses to customers
AllArcs = FHArcs + HCArcs

### Make them Gurobi tuplelists
FHArcs = tuplelist(FHArcs)
HCArcs = tuplelist(HCArcs)
AllArcs = tuplelist(AllArcs)


##### Start building the Model #####
m=Model("JLWRC")

### First stage vars, capacity increasing cost
capcost={}
for i,j in AllArcs:
    capcost[i,j]=m.addVar(obj=arcExpCost[i,j],name='Expansion%s_%s' % (i,j)) 

### Second stage, ship between arcs
ship={}
for i,j in AllArcs:
    for k in Sset:
        ship[i,j,k]=m.addVar(obj=0,name='Ship_from%s_to%s_scenario_%s' % (i,j,k))

### Second stage vars, unmet demands
nscen=len(Sset)
unmet = {}
for c in Cset:
    for s in Sset:
        unmet[c,s] = m.addVar(obj=float(unmetCost[c])/nscen, name='Unmet%s_%s' %(c,s))

m.modelSense = GRB.MINIMIZE

m.update()

### arcs constraints
for i,j in AllArcs:
    for s in Sset:
        m.addConstr(ship[i,j,s]-capcost[i,j] <= curArcCap[i,j], name='Arcs%s_%s_scenario_%s' %(i,j,s))

### warehouses constraints
for h in Hset:
    for s in Sset:
        m.addConstr(
            quicksum(ship[i,h,s] for i,h in FHArcs.select('*',h))-quicksum(ship[h,j,s] for h,j in HCArcs.select(h,'*'))>=0,name='warehouse%s_scenario_%s' %(h,s))

### facilities constraints
for f in Fset:
    m.addConstr(
        quicksum(curArcCap[f,h]+capcost[f,h] for f,h in FHArcs.select(f,'*'))<= facCap[f],name='Facility%s' %f)

### Demand constraints
for c in Cset:
    for s in Sset:
        m.addConstr(
            quicksum(ship[h,c,s] for h,c in HCArcs.select('*',c)) + unmet[c,s] >= demScens[c,s], name='Demand%s_%s' %(c,s))

m.update()

## Solve
m.optimize()
optimal_sol=m.objVal
print('\nEXPECTED COST : %g' % m.objVal)

############ Build and solve the mean value problem  ############

mvm = Model("avgfacility")
### First stage vars, capacity increasing cost
mvcapcost={}
for i,j in AllArcs:
    mvcapcost[i,j]=mvm.addVar(obj=arcExpCost[i,j],name='Expansion%s_%s' % (i,j)) 

### ship between arcs
mvship={}
for i,j in AllArcs:
    mvship[i,j]=mvm.addVar(obj=0,name='Ship_from%s_to%s' % (i,j))

### unmet demands
mvunmet = {}
for c in Cset:
    mvunmet[c] = mvm.addVar(obj=float(unmetCost[c]), name='Unmet%s' % c )

mvm.modelSense = GRB.MINIMIZE

mvm.update()
### arcs constraints
for i,j in AllArcs:
    mvm.addConstr(mvship[i,j]-mvcapcost[i,j] <= curArcCap[i,j], name='Arcs%s_%s' %(i,j))

### warehouses constraints
for h in Hset:
    mvm.addConstr(
            quicksum(mvship[i,h] for i,h in FHArcs.select('*',h))-quicksum(mvship[h,j] for h,j in HCArcs.select(h,'*'))>=0,name='warehouse%s' % h )

### facilities constraints
for f in Fset:
    mvm.addConstr(
        quicksum(curArcCap[f,h]+mvcapcost[f,h] for f,h in FHArcs.select(f,'*'))<= facCap[f],name='Facility%s' %f)

### Demand constraints
for c in Cset:
    mvm.addConstr(
        quicksum(mvship[h,c] for h,c in HCArcs.select('*',c)) +mvunmet[c] >= quicksum(demScens[c,s] for s in Sset)/nscen, name='Demand%s' % c )

mvm.update()

## Solve
mvm.optimize()
for i,j in AllArcs:
    capcost[i,j].lb=mvcapcost[i,j].x
    capcost[i,j].ub=mvcapcost[i,j].x
m.update()
m.optimize()
value_stsol=m.objVal-optimal_sol
print('\nVALUE OF STOCHASTIC SOLUTION: %g' % value_stsol)
