import os
import globals

gate_number = 0

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

def read_v_netlist(filepath: str):
    # validate file
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
            if not line or line.startswith('//'):
                continue
            line = line.split("//")[0].strip()
            if line.startswith("input"):
                # remove keywords
                stripped_line = line.replace("input", "")
                stripped_line = stripped_line.replace("wire","")
                stripped_line = stripped_line.replace(";","")
                stripped_line = stripped_line.lower()

                # append PIs
                tokens = [s.strip() for s in stripped_line.split(',') if s.strip()]  # remove empty strings
                for wire in tokens:
                    globals.primary_inputs.append(wire)
            elif line.startswith("output"):
                # remove keywords
                stripped_line = line.replace("output", "")
                stripped_line = stripped_line.replace("wire","")
                stripped_line = stripped_line.replace(";","")
                stripped_line = stripped_line.lower()

                # append POs
                tokens = [s.strip() for s in stripped_line.split(',') if s.strip()]
                for wire in tokens:
                    globals.primary_outputs.append(wire)
            # structural modeling gates
            elif line.startswith(("and", "xor", "or", "nand", "xnor", "nor")):
                gate_type, rest = line.split("(", 1)
                gate_type = gate_type.strip()
                rest = rest.rstrip(");")

                tokens = [t.strip() for t in rest.split(",") if t.strip()]

                output = [tokens[0]]
                inputs = tokens[1:]
                name = "G" + str(gate_number)
                # make gate
                gate_obj = globals.Gate(name, output, gate_type, inputs)
                globals.gates.append(gate_obj) 
                gate_number += 1
            # data-flow modeling gates
            elif line.startswith("assign"):
                line = line.replace("assign", "")
                equality_index = line.find("=")
                line = line.lower()
                left_half = line[:equality_index].strip()
                right_half = line[equality_index:].strip()
                right_half = right_half[1:].strip() # remove '='

                # left half - gather outputs
                outputs = []
                if left_half.startswith("{") and left_half.endswith("}"):
                    # remove {}
                    inner = left_half[1:-1]
                    signals = inner.split(",")
                    for s in signals:
                        outputs.append(s.strip())
                else:
                    outputs.append(left_half)

                # right half - gather inputs and operands then build gates
                rh_tokens = tokenize(right_half)
                ast = parse(rh_tokens)
                generate_gates(ast)

                # set last gate in line equal to wire left of the '=' sign
                last_gate = globals.gates[-1]
                wire_to_replace = last_gate.output[0]
                last_gate.output[0] = outputs[0]
                # remove old wire
                globals.wire_values.pop(wire_to_replace, None)
    
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

def tokenize(line):
    tokens = []
    i = 0

    while i < len(line):
        c = line[i]

        if c == ' ' or c == ';':
            i += 1
            continue

        # operator and parantheses
        if c in '()&|^~':
            # negation gates
            if c == '~' and i + 1 < len(line) and line[i+1] in '&|^':
                tokens.append(line[i:i+2])
                i += 2
            else:
                tokens.append(c)
                i += 1
            continue

        # input
        if c.isalpha():
            start = i
            while i < len(line) and line[i].isalnum():
                i += 1
            tokens.append(line[start:i])
            continue

        raise ValueError("Invalid character: " + c)

    return tokens


class Node:
    def __init__(self, op=None, left=None, right=None, value=None):
        self.op = op
        self.left = left
        self.right = right
        self.value = value

def parse(tokens):

    """
    parses from bottom to top of precedence level 
    (lowest becomes root of the tree)

    ~          (NOT)
    &  ~&      (AND / NAND)
    ^  ~^      (XOR / XNOR)
    |  ~|      (OR / NOR)
    """

    def parse_or():
        node = parse_xor()
        while tokens and tokens[0] in ('|', '~|'):
            op = tokens.pop(0)
            node = Node(op=op, left=node, right=parse_xor())
        return node

    def parse_xor():
        node = parse_and()
        while tokens and tokens[0] in ('^', '~^'):
            op = tokens.pop(0)
            node = Node(op=op, left=node, right=parse_and())
        return node

    def parse_and():
        node = parse_not()
        while tokens and tokens[0] in ('&', '~&'):
            op = tokens.pop(0)
            node = Node(op=op, left=node, right=parse_not())
        return node

    def parse_not():
        if tokens[0] == '~':
            tokens.pop(0)
            return Node(op='~', left=parse_not())
        return parse_atom()

    def parse_atom():
        tok = tokens.pop(0)
        if tok == '(':
            node = parse_or()
            tokens.pop(0)  # ')'
            return node
        return Node(value=tok)

    return parse_or()

def generate_gates(ast):
    wire_num = 0

    def new_wire():
        nonlocal wire_num
        while True:
            w = f"w{wire_num}"
            wire_num += 1
            if w not in globals.wire_values:
                return w

    def new_gate_name():
        global gate_number
        g = "G" + str(gate_number)
        gate_number += 1
        return g

    def walk(node):
        if node.value:
            return node.value

        if node.op == '~':
            inp = walk(node.left)
            out = new_wire()

            gate = globals.Gate(
                name=new_gate_name(),
                gate_type="not",
                inputs=[inp],
                output=[out]
            )
            globals.gates.append(gate)
            return out

        # binary gates
        left = walk(node.left)
        right = walk(node.right)
        out = new_wire()

        gate_map = {
            '&': 'and',
            '|': 'or',
            '^': 'xor',
            '~&': 'nand',
            '~|': 'nor',
            '~^': 'xnor'
        }

        gate = globals.Gate(
            name=new_gate_name(),
            gate_type=gate_map[node.op],
            inputs=[left, right],
            output=[out]
        )
        globals.gates.append(gate)

        return out

    walk(ast)

# test runner
if __name__ == "__main__":
    # Example usage
    filepath = input("Enter the path to the net-list file: ").strip()
    read_v_netlist(filepath)