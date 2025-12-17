import os
import globals

def make_fanouts():
    for wire, fanout_number in globals.duplicate_wires.items():
        fanout_number += 1 # account for original wire
        input_wire = wire
        output_wires = [f"{wire}_fan{i}" for i in range(fanout_number)] # rename fanout branches

        branch_index = 0 # index to track which fanout branch to use
        # Update each gate that uses this wire
        for gate in globals.gates:
            if wire in gate.inputs:
                # Replace only the first occurrence
                gate.inputs[gate.inputs.index(wire)] = output_wires[branch_index]

                branch_index += 1
                if branch_index >= fanout_number:
                    break
        # create fanout gate        
        globals.gates.append(
            globals.Gate(f"Fanout_{wire}", output_wires, "fanout", [input_wire])
        )


    

def read_ckt_netlist(filepath: str):
    # validate file
    # not yet implemented
    if not os.path.isfile(filepath):
        print(f"Error: File '{filepath}' does not exist.")
        return None
    
    # clear any previous netlist data
    globals.reset_globals()
    gate_number = 0

    # read and strip lines
    with open(filepath, "r") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith('$'):
                continue
        
            tokens = line.split()

            lower_line = line.lower()
            # primary inputs
            if "primary input" in lower_line:
                wire_name = tokens[0]
                globals.primary_inputs.append(wire_name)

            # primary outputs
            elif "primary output" in lower_line:
                wire_name = tokens[0]
                globals.primary_outputs.append(wire_name)
            
            # gates
            else:
                if len(tokens) >= 3:
                    output = [tokens[0]]
                    gate_type = tokens[1]
                    inputs = tokens[2:]
                    name = f"G{gate_number}"
                    gate_obj = globals.Gate(name, output, gate_type.lower(), inputs)
                    gate_number += 1
                    globals.gates.append(gate_obj) 
                else:
                    print(f"Warning: Unrecognized line format: '{line}'")

    make_fanouts()

    # display for testing
    print(f"Primary Inputs: {globals.primary_inputs}")
    print(f"Primary Outputs: {globals.primary_outputs}")
    print(f"Fanouts: {globals.duplicate_wires}")
    print(f"Wire Values: {globals.wire_values}")
    print("Gates:")
    for gate in globals.gates:
        if gate.gate_type == "fanout":
            print(f"  {gate.name}: {gate.output}")
        else:
            print(f"  {gate.name}: {gate.output} = {gate.gate_type}({', '.join(gate.inputs)})   c={gate.c}, inv={gate.inv}")

# test runner
if __name__ == "__main__":
    # Example usage
    filepath = input("Enter the path to the net-list file: ").strip()
    read_ckt_netlist(filepath)