from netlist_parsing import read_ckt_netlist, read_v_netlist
from fault_collapse import collapse_faults
from podem import PODEM
from simulate import get_test_vector
import globals

def display_menu():
    print("""
    [0] Read the input net-list
    [1] Perform fault collapsing
    [2] List fault classes
    [3] Simulate
    [4] Generate tests (PODEM)
    [5] Exit
          """)
    return input("Select an option: ")

def handle_selection(selection):
    if selection == '0':
        file_type = input("Select netlist type (0 = .ckt, 1 = .v): ").strip()

        match file_type:
            case '0':
                filepath = input("Enter the path to the .ckt netlist file: ").strip()
                read_ckt_netlist(filepath)
            case '1':
                filepath = input("Enter the path to the .v netlist file: ").strip()
                read_v_netlist(filepath)
            case _:
                print("Invalid selection. Enter 0.")
            
        
    elif selection == '1':
        if not globals.gates:
            print("No gates loaded. Enter netlist with [0] first.")
            return
        collapse_faults()
        print("Faults collapsed.")
    elif selection == '2':
        if not globals.gates:
            print("No gates loaded. Enter netlist with [0] first.")
            return
        print("Fault List:")
        for fault in sorted(globals.fault_list):
            print(f"{fault}")
    elif selection == '3':
        if not globals.gates:
            print("No gates loaded. Enter netlist with [0] first.")
            return
        get_test_vector()
    elif selection == '4':
        if not globals.gates:
            print("No gates loaded. Enter netlist with [0] first.")
            return
        # print test vector format
        test_vector_format = " ".join([pi for pi in globals.primary_inputs])
        print(f"Test Vector Format: {test_vector_format}")
        # print test vector for each fault
        for wire in sorted(globals.wire_values):
            for val in ['0', '1']:
                globals.reset_wire_values()
                globals.target_line = wire
                globals.fault_value = val
                result = PODEM()
                if result == "SUCCESS":
                    test_vector = []
                    for pi in globals.primary_inputs:
                        if globals.wire_values[pi] == 'D':
                            globals.wire_values[pi] = '1'
                        elif globals.wire_values[pi] == "D'":
                            globals.wire_values[pi] = '0'
                        test_vector.append(globals.wire_values[pi])
                    test_vector = ''.join(test_vector)
                        
                    print(f"{wire} s-a-{val}: {test_vector}")
                else:
                    print(f"{wire} s-a-{val}: Undetectable fault")
    elif selection == '5':
        print("Exiting program.")
        #exit_program()
    else:
        print("Invalid selection. Please try again.")
    return True