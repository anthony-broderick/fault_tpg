import globals
from collections import defaultdict

def collapse_faults():
    # create set of faults for each value in wire_values 
    # (s-a-0 and s-a-1)
    collapsed_faults = {
        f"{wire}: s-a-{sa}"
        for wire in globals.wire_values.keys()
        for sa in (0, 1)
    }

    # build dict for efficient check for non PI fanouts later
    wire_to_gates = defaultdict(list)

    for gate in globals.gates:
        for wire in gate.inputs:
            wire_to_gates[wire].append(gate)
    
    PI_fanout_gates = set()

    for gate in globals.gates:
        if gate.gate_type == "fanout" and gate.inputs[0] in globals.primary_inputs:
            for out in gate.output:
                for g in wire_to_gates.get(out, []):
                    PI_fanout_gates.add(g)

    for gate in PI_fanout_gates:
        print(gate.name)

    for gate in globals.gates:
        check = False
        if gate.gate_type == "fanout":
            continue
        if gate.gate_type == "not":
            wire_name = f"{gate.output[0]}: s-a-0"
            collapsed_faults.discard(wire_name)
            wire_name = f"{gate.output[0]}: s-a-1"
            collapsed_faults.discard(wire_name)
            continue
        # FAULT EQUIVALENCE
        # input s-a-(c) equivalent to output s-a-(c XOR i)
        # remove all but one input s-a-(c) and remove output s-a-(c XOR i)
        for inp in gate.inputs:
            wire_name = f"{inp}: s-a-{gate.c}"
            # remove all non PI fanout fault equivalence
            if (
                '_fan' in wire_name 
                and gate not in PI_fanout_gates
            ):
                collapsed_faults.discard(wire_name)
                continue
            if check == False and wire_name in collapsed_faults:
                check = True
                continue
            collapsed_faults.discard(wire_name)
        for out in gate.output:
            wire_name = f"{out}: s-a-{gate.c ^ gate.inv}"
            collapsed_faults.discard(wire_name)
            # FAULT DOMINANCE
            # output s-a-(c XNOR i) dominates input s-a-(c')s
            # remove output s-a-(c XNOR i) and keep both input s-a-(c')s
            wire_name = f"{out}: s-a-{~(gate.c ^ gate.inv) & 1}"
            collapsed_faults.discard(wire_name)

    globals.fault_list = collapsed_faults