import globals

# 5-value logic constants
X = 'X'
ZERO = '0'
ONE = '1'
D = 'D'
DB = "D'"

test_line = "A_fan1"

n = -1
status = "OK"

def invert_value(val):
    if val == ONE:
        return ZERO
    if val == ZERO:
        return ONE
    if val == D:
        return DB
    if val == DB:
        return D
    return X

def PODEM():
    if error_at_PO():
        return 'SUCCESS'
    
    if test_not_possible():
        return 'FAILURE'

    # set intial fault line on first run
    # find necessary input to propagate fault
    k, vk = Objective() 
    if k is None:
        return 'FAILURE'
    
    # using input from Objective, backtrace to PI (does not change any values)
    j, vj = Backtrace(k, vk)
    if j is None:
        return 'FAILURE'

    # from PI, keep evaluating gate output until its no longer changing outputs
    Imply(j, vj)

    if PODEM() == 'SUCCESS': return 'SUCCESS'

    # reverse decision
    vj_complement = invert_value(vj)
    Imply(j, vj_complement) 

    if PODEM() == 'SUCCESS': return 'SUCCESS'

    # reverse j to 'X'
    Imply(j, X)

    return 'FAILURE'

def Objective():
    if globals.wire_values[globals.target_line] == 'X':
        if globals.fault_value == '1':
            return (globals.target_line, DB)
        else:
            return (globals.target_line, D)
    
    D_frontier = get_D_frontier()

    if D_frontier: # D-frontier not empty

        # iterate through DF if backtrace gets stuck on gate with no X input
        global n
        global status
        if status == "TRY_NEXT_DF":
            n += 1
        else: 
            # status == "OK"
            n = -1
        if n == len(D_frontier):
            # iterated through each DF gate with no success
            return (None, None)
        

        gate = D_frontier[n] # select last gate in most cases unless trying next DF
        for inp in gate.inputs:
            if globals.wire_values[inp] == 'X':
                if gate.c == 0:
                    complement = ONE
                else:
                    complement = ZERO
                return (inp, complement)
    return (None, None)

def Backtrace(k, complement):
    v = complement
    iteration = 0
    visited = set()
    global status

    while k not in globals.primary_inputs: # k is not PI

        if k in visited:
            status = "TRY_NEXT_DF"
            return (None, None)
            
        visited.add(k)

        if iteration > (4 * globals.max_recursion_depth):
            print("Backtrace iteration limit exceeded")
            return (None, None)
        iteration += 1
        for gate in globals.gates:
            if k in gate.output:

                # Diagnose Case 1: No X inputs
                x_inputs = [j for j in gate.inputs if globals.wire_values[j] == 'X']
                if len(x_inputs) == 0:
                    status = "TRY_NEXT_DF"
                    return (None, None)


                # handle non PI target_fault
                if k == globals.target_line:
                    globals.wire_values[k] = D if globals.fault_value == '1' else DB
                    v = ONE if globals.fault_value == '0' else ZERO
                for j in gate.inputs:
                    if globals.wire_values[j] == 'X':
                        #v = v ^ gate.inv
                        v = invert_value(v) if gate.inv == 1 else v
                        k = j
                    if k in globals.primary_inputs:
                        status = "OK"
                        return (k,v)
    status = "OK"
    return (k, v) # k is already a PI

def Imply(j,vj): # first call is a PI line (j) and needed value (vj)
    globals.wire_values[j] = vj # assigning PI to a value

    # evaluating gates (assigning outputs) until output does not change
    changed = True
    while changed:
        changed = False
        for gate in globals.gates:
            if gate.gate_type == 'fanout':
                for out in gate.output:
                    # handle target fault on fanout branch
                    if out == globals.target_line:
                        continue
                    old = globals.wire_values.get(out, X)
                    new = globals.wire_values[gate.inputs[0]]
                    if new != old:
                        globals.wire_values[out] = new
                        changed = True
            else:
                # handle target fault on gate output
                if gate.output[0] == globals.target_line:
                    continue
                old = globals.wire_values.get(gate.output[0], X)
                new = evaluate_gate(gate)
                if new != old:
                    globals.wire_values[gate.output[0]] = new
                    changed = True

def get_initial_output(gate):
    values = []
    has_x = False
    control = ONE if gate.c == 1 else ZERO
    gate_type = gate.gate_type

    for i in gate.inputs:
        inp_val = globals.wire_values[i]
        # can't compute xor/xnor with don't care
        if gate_type in ["xor", "xnor"] and inp_val == X:
            return X
        # check for controlling value
        if gate_type not in ["xor", "xnor"]:
            if inp_val == control:
                return control

        if inp_val == X:
            has_x = True
        # assign good and fault inputs
        elif inp_val == D:
            values += ["1", "0"]
        elif inp_val == DB:
            values += ["0", "1"]
        elif inp_val == ZERO:
            values += ["0", "0"]
        else:
            values += ["1", "1"]

    # 'X' make it so output is unknown
    if gate_type not in ["xor", "xnor"]:
        if has_x == True:
            return X

    good_output = 0
    fault_output = 0
    if gate_type in ["and", "nand"]:
        good_output = 1
        fault_output = 1
    # make gate computation for good and fault values
    for i in range(len(values)):
        if i % 2 == 0:
            match gate_type:
                case "and" | "nand":
                    good_output *= int(values[i])
                case "or" | "nor":
                    good_output |= int(values[i])
                case "xor" | "xnor":
                    good_output ^= int(values[i])
        else:
            match gate_type:
                case "and" | "nand":
                    fault_output *= int(values[i])
                case "or" | "nor":
                    fault_output |= int(values[i])
                case "xor" | "xnor":
                    fault_output ^= int(values[i])

    # set output
    if good_output == 0 and fault_output == 0:
        return ZERO
    elif good_output == 1 and fault_output == 1:
        return ONE
    elif good_output == 1 and fault_output == 0:
        return D
    elif good_output == 0 and fault_output == 1:
        return DB
    else:
        raise ValueError("Unknown output combination")

def evaluate_gate(gate):
    # returns new 5-valued logic for gate.output[0] based on gate.inputs
    in_vals = [globals.wire_values.get(i, X) for i in gate.inputs]

    # NOT gate
    if gate.gate_type == 'not':
        return invert_value(in_vals[0])
    
    out = get_initial_output(gate)

    # account for gate inversion
    if gate.inv == 1:
        out = invert_value(out)

    return out

def error_at_PO():
    # true if any primary output has D or D'
    for po in globals.primary_outputs:
        val = globals.wire_values.get(po, X)
        if val == D or val == DB:
            return True
    return False

def test_not_possible():
    globals.recursion_depth += 1
    if globals.recursion_depth > globals.max_recursion_depth:
        return True


def get_D_frontier():
    D_frontier = []
    for gate in globals.gates:
        for inp in gate.inputs:
            if globals.wire_values.get(inp, X) == D or globals.wire_values.get(inp, X) == DB:
                output = globals.wire_values.get(gate.output[0], X)
                if output == D or output == DB:
                    break
                D_frontier.append(gate)
                break

    return D_frontier