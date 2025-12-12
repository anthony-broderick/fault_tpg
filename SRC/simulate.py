import globals

# 5-value logic constants
X = 'X'
ZERO = '0'
ONE = '1'
D = 'D'
DB = "D'"

# test vector
test_vector = {}

# print table
fault_rows = []

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

	# don't cares make it so output is unknown
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
	print(f"{gate.gate_type} with {[globals.wire_values[inp] for inp in gate.inputs]} = {out}")

	# account for gate inversion
	if gate.inv == 1:
		out = invert_value(out)

	return out

def get_test_vector():
	# collect test vector
	print("Primary inputs:")
	global test_vector
	for pi in globals.primary_inputs:
		while True:
			val = input(f"  Enter value for {pi} (0/1/X): ").strip().upper()
			if val in ('0', '1', 'X'):
				test_vector[pi] = val
				break
			print("    Invalid value — enter 0, 1, or X.")

	# print all wires user can choose from
	print("\nAvailable wires in circuit (can inject faults on any):")
	wires = sorted(globals.wire_values.keys())
	if wires:
		print("  " + ", ".join(wires))
	else:
		print("  (no wires detected)")

	# reset print table
	global fault_rows
	fault_rows = []

	# call simulate for each stuck at fault listed
	raw_faults = input("\nEnter faults to inject (comma-separated, e.g. 'a: s-a-0, b: s-a-0'), or leave blank: ").strip()
	sa0_faults = {}
	sa1_faults = {}
	if raw_faults:
		parts = [p.strip() for p in raw_faults.split(',') if p.strip()]
		for p in parts:
			# accept formats like "wire: s-a-0" or "wire s-a-0" or "wire:s-a-0"
			token = p.replace(':', ' ').split()
			if len(token) >= 2:
				line = token[0]
				sa = token[1]
				if sa.endswith('0'):
					# represent s-a-0 as D (good=1, faulty=0)
					if line in globals.wire_values:
						sa0_faults[line] = 'D'
					else:
						print(f"Warning: fault line {line} not found in circuit.")
				elif sa.endswith('1'):
					# represent s-a-1 as D' (good=0, faulty=1)
					if line in globals.wire_values:
						sa1_faults[line] = "D'"
					else:
						print(f"Warning: fault line {line} not found in circuit.")
				else:
					print(f"Warning: couldn't parse stuck value in '{p}'.")
			else:
				print(f"Warning: couldn't parse fault '{p}'.")

	# call simulate for each fault entered
	for line, val in sa0_faults.items():
		simulate(line, val)
	for line, val in sa1_faults.items():
		simulate(line, val)

	if sa0_faults or sa1_faults:
		print_fault_table()
	else:
		simulate_no_faults()

def simulate_no_faults():
	globals.reset_wire_values()
	for pi in globals.primary_inputs:
		globals.wire_values[pi] = test_vector.get(pi, 'X')

	# iterative simulation
	changed = True
	iteration = 0
	while changed:
		changed = False
		iteration += 1
		for gate in globals.gates:
			if gate.gate_type == 'fanout':
				for out in gate.output:
					old = globals.wire_values.get(out, X)
					new = globals.wire_values[gate.inputs[0]]
					if new != old:
						globals.wire_values[out] = new
						changed = True
			else:
				# gate.output may be a list (fanout) or a single value; normalize to list
				outputs = gate.output if isinstance(gate.output, list) else [gate.output]
				# evaluate gate once; only update outputs that do not have injected faults
				new = evaluate_gate(gate)
				# assign new value to each output wire and mark changed if any updated
				for out in outputs:
					old = globals.wire_values.get(out, 'X')
					if new != old:
						globals.wire_values[out] = new
						changed = True
	print("")
	for po in globals.primary_outputs:
		val = globals.wire_values.get(po, 'X')
		print(f"{po}: {val}")
    

def simulate(fault_line, fault_value):
	globals.reset_wire_values()
	for pi in globals.primary_inputs:
		globals.wire_values[pi] = test_vector.get(pi, 'X')
	if fault_line in globals.primary_inputs:
		pi = globals.wire_values[fault_line]
		if (pi == '1' and fault_value == "D'") or (pi == '0' and fault_value == 'D'):
			# fault on PI that matches PI value; no effect
			pass
		else:
			globals.wire_values[fault_line] = fault_value
	else:
		globals.wire_values[fault_line] = fault_value


	# iterative simulation
	changed = True
	iteration = 0
	while changed:
		changed = False
		iteration += 1
		for gate in globals.gates:
			if gate.gate_type == 'fanout':
				for out in gate.output:
					# handle target fault on fanout branch
					if out == fault_line:
						continue
					old = globals.wire_values.get(out, X)
					new = globals.wire_values[gate.inputs[0]]
					if new != old:
						globals.wire_values[out] = new
						changed = True
			else:
				# gate.output may be a list (fanout) or a single value; normalize to list
				outputs = gate.output if isinstance(gate.output, list) else [gate.output]
				# evaluate gate once; only update outputs that do not have injected faults
				new = evaluate_gate(gate)
				# assign new value to each output wire and mark changed if any updated
				for out in outputs:
					# don't overwrite wires with explicitly injected faults
					if out == fault_line:
						continue
					old = globals.wire_values.get(out, 'X')
					if new != old:
						globals.wire_values[out] = new
						changed = True
	# collect results for table
	add_fault_result(fault_line, fault_value)

def add_fault_result(fault_line, fault_value):
    """
    Adds a row to the fault result table.
    Uses the current globals.wire_values for each PO.
    """
    row = [
        fault_line,
        f"s-a-{'0' if fault_value == D else '1'}",
    ]
    
    # Add each primary output value
    for po in globals.primary_outputs:
        val = globals.wire_values.get(po, 'X')
        row.append(val)
    
    fault_rows.append(row)


def print_fault_table():
	"""Prints the accumulated table with multiple rows."""
	if not fault_rows:
		print("No fault results to display.")
		return

	# Build header
	headers = ["fault line", "fault value"] + globals.primary_outputs

	# Compute column widths
	# Width = max(header width, max cell width in that column) + padding
	num_cols = len(headers)
	col_widths = [len(h) for h in headers]

	for row in fault_rows:
		for i in range(num_cols):
			col_widths[i] = max(col_widths[i], len(str(row[i])))

	col_widths = [w + 2 for w in col_widths]  # add padding

	# Formatting helpers
	def fmt_row(row):
		return "".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))

	# Print header
	print("")
	print(fmt_row(headers))
	print("".join("-" * w for w in col_widths))

	# Print each saved row
	for row in fault_rows:
		print(fmt_row(row))

