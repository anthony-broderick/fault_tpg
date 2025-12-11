# given core data
primary_inputs = []
primary_outputs = []
gates = []
wire_values = {}
input_wires = []
duplicate_wires = {}
fault_list = set ()
target_line = ""
fault_value = ""
max_recursion_depth = 50
recursion_depth = 0


class Gate:
    def __init__(self, name: str, output: list, gate_type: str, inputs: list, c: int = 0, inv: int = 0, PI: bool = False):
        self.name = name
        self.output = output
        self.gate_type = gate_type
        self.inputs = inputs
        self.PI = False
        
        for out in self.output:
            wire_values[out] = 'X'  # initialize output wire value

            # add output s-a-faults
            fault_list.add(f"{out}: s-a-0")
            fault_list.add(f"{out}: s-a-1")
        for inp in self.inputs:
            wire_values[inp] = 'X' # initialize input wire value
            if inp in input_wires:
                if inp not in duplicate_wires:
                    duplicate_wires[inp] = 1 # first duplicate means there are at least 2 branches to be considered fanout
                else:
                    duplicate_wires[inp] += 1
            input_wires.append(inp)

            # add input s-a-faults
            fault_list.add(f"{inp}: s-a-0")
            fault_list.add(f"{inp}: s-a-1")
            if inp in primary_inputs:
                self.PI = True


        # set controlling and inverting values
        if gate_type == "nand" or gate_type == "not":
            self.c = 0
            self.inv = 1
        elif gate_type == "nor" or gate_type == "xnor":
            self.c = 1
            self.inv = 1
        elif gate_type == "or" or gate_type == "xor":
            self.c = 1
            self.inv = 0
        elif gate_type == "and":
            self.c = 0
            self.inv = 0
        else:
            self.c = c
            self.inv = inv

# faults
def reset_wire_values():
    global wire_values
    for wire in wire_values:
        wire_values[wire] = 'X'
    global recursion_depth 
    recursion_depth = 0

# reset for new netlist
def reset_globals():
    global primary_inputs, primary_outputs, gates
    primary_inputs.clear()
    primary_outputs.clear()
    wire_values.clear()
    fault_list.clear()
    gates.clear()
    input_wires.clear()
    duplicate_wires.clear()
