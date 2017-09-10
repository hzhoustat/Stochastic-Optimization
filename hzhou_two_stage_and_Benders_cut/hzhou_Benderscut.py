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

nscen=float(len(Sset))

##### Master problem #####
master=Model("master")
master.params.logtoconsole=0
### Capacity increasing cost
capcost={}
for i,j in AllArcs:
    capcost[i,j]=master.addVar(obj=arcExpCost[i,j],name='Expansion%s_%s' % (i,j)) 

# Value function decision variables
theta = {}
for k in Sset:
    theta[k] = master.addVar(vtype=GRB.CONTINUOUS, obj=1/nscen, name="Theta%s" % k)

master.modelSense = GRB.MINIMIZE
master.update()

### facilities constraints
for f in Fset:
    master.addConstr(
        quicksum(curArcCap[f,h]+capcost[f,h] for f,h in FHArcs.select(f,'*'))<= facCap[f],name='Facility%s' %f)

master.update()

### Subproblem
sub=Model("demand")
sub.params.logtoconsole=0

### demand unmet
unmet = {}
for c in Cset:
        unmet[c] = sub.addVar(obj=float(unmetCost[c]), name='Unmet%s' % c )

### ship
ship={}
for i,j in AllArcs:
    ship[i,j]=sub.addVar(obj=0,name='Ship_from%s_to%s' % (i,j))

# The objective is to minimize the total fixed and variable costs
sub.modelSense = GRB.MINIMIZE 
sub.update()

### Demand constraints
demcon={}
for c in Cset:
    demcon[c] = sub.addConstr(
           quicksum(ship[h,c] for h,c in HCArcs.select('*',c)) + unmet[c] == demScens[c,'S0'], name='Demand%s' % c)

### arcs constraints
arccon={}
for i,j in AllArcs:
    arccon[i,j]=sub.addConstr(ship[i,j] <= curArcCap[i,j], name='Arcs%s_%s' %(i,j))

### warehouses constraints
warecon={}
for h in Hset:
    warecon[h]=sub.addConstr(
        quicksum(ship[i,h] for i,h in FHArcs.select('*',h))-quicksum(ship[h,j] for h,j in HCArcs.select(h,'*'))>=0,name='warehouse%s' %h)
sub.update()

# Begin the cutting plane loop
cutfound = 1  ## keep track if any violated cuts were found
iter = 1
while cutfound:

    print '================ Iteration ', iter, ' ==================='
    iter = iter+1
    # Solve current master problem
    cutfound = 0 
    master.update()
    master.optimize()
    print 'lower bound (objval) = ', master.objVal   
        # Fix the right-hand side in subproblem constraints according to each scenario and master solution, then solve
    upper_bound=0
    capobj=quicksum(capcost[i,j].x*arcExpCost[i,j] for i,j in AllArcs)
    upper_bound=capobj.getValue()
    cutnum=0
    for i,j in AllArcs:
        arccon[i,j].RHS=curArcCap[i,j]+capcost[i,j].x
    for k in Sset:
        for c in Cset:
            demcon[c].RHS=demScens[c,k]
        sub.update()
        sub.optimize()
        # Display info, compute Benders cut, display, add to master 
        upper_bound +=1/nscen*sub.objVal          
        if sub.objVal > theta[k].x + 0.000001:  ### violation tolerance
             rhs=0.0
             for c in Cset:
                 rhs +=demScens[c,k]*demcon[c].pi
             for i,j in AllArcs:
                 rhs +=arccon[i,j].pi*(curArcCap[i,j]+capcost[i,j])
             master.addConstr(theta[k]>=rhs)
             cutfound = 1
             cutnum +=1
    print 'upper bound = ', upper_bound
    print ' cuts added number = ', cutnum

### print final solution             
##print 'final optimal solution:'
##for i,j in AllArcs:
##    print 'Ship from %s to %s is %s, expansion is %s' % (i,j,ship[i,j].x,capcost[i,j].x)
##for k in Sset:
##    print 'theta[', k, ']=', theta[k].x
##print 'objval = ', master.objVal 
