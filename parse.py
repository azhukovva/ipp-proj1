import sys
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import tostring
import getopt
import re

# --------------- HELP MESSAGE ---------------
try:
    opts, _ = getopt.getopt(sys.argv[1:], "h", ["help"])
except getopt.GetoptError as err:
    exit(10)

for o, a in opts:
    if o in ("-h", "--help") and len(sys.argv) == 2:
        print(len(sys.argv))
        print(
            """
        Welcome to my brilliant IPPCode24 parser!

        Script takes IPPCode24 as input, creates XML representation (encoding UTF-8)
        and sends it to output.

        Default options:
        --help or -h print help info
        """
        )
        sys.exit(0)
    else:
        print("Error: parametr --help/-h can't be combined with other options")
        sys.exit(10)


# --------------- PATTERNS FOR ARGUMENTS ---------------
PATTERN_VAR_NAME = r"[a-zA-Z_$&%*!?-]+[a-zA-Z0-9_$&%*!?-]*"
PATTERN_VAR = r"^(GF|LF|TF)@{0}$".format(PATTERN_VAR_NAME)
PATTERN_CONST_INT = r"(?i)int@(\+|-)?(0|0[xX][0-9a-fA-F]+|0o[0-7]+|[1-9][0-9]*|0)"
PATTERN_CONST_NIL = r"^nil@nil$"
PATTERN_CONST_STRING = r"string@(([^\\]|\\[0-9]{3})*)$"
PATTERN_CONST_BOOL = r"bool@(true|false)"
PATTERN_LIT_NOT_STRING = r"^({0}|{1}|{2})$".format(
    PATTERN_CONST_INT, PATTERN_CONST_NIL, PATTERN_CONST_BOOL
)
PATTERN_CONST = r"({0}|{1}|{2}|{3})".format(
    PATTERN_CONST_INT, PATTERN_CONST_STRING, PATTERN_CONST_NIL, PATTERN_CONST_BOOL
)
PATTERN_SYMB = r"({0}|{1})".format(PATTERN_CONST, PATTERN_VAR)
PATTERN_TYPE = r"^(int|string|bool)$"
PATTERN_LABEL = r"^{0}$".format(PATTERN_VAR_NAME)
PATTERN_CONST_FLOAT = r"float@(\+|-)?(0x[0-9a-fA-FpP]+|[0-9]*\.[0-9]+([eE][+-]?[0-9]+)?)"


# --------------- FORMATTER ---------------
# RETURN a formatted line
class Formatter:
    def format_line(self, line):
        if not isinstance(line, str):
            return False

        line = self.remove_ending(line)
        line = self.remove_comments(line)
        line = self.remove_empty(line)

        return line

    # ----- formatting methods -----
    def remove_ending(self, line):
        return line.rstrip("\n")

    def remove_comments(self, line):
        return re.sub(r"#.*", "", line).strip()  # (pattern, repl, string)

    def remove_empty(self, line):
        if not line.strip():

            return None  # line's empty
        return line


# --------------- INPUT HANDLER ---------------
# Read input line by line from standard input (stdin) and format it
# RETURN list of formatted lines
class InputReader(Formatter):
    def __init__(self):
        self.input = []  # list of formatted lines

    def get_input(self):
        if not sys.stdin.isatty():  # if there's something in stdin
            for line in sys.stdin:
                formatted_line = self.format_line(line)  # format each line
                if formatted_line is not None:
                    self.input.append(formatted_line)  # add the formatted line to list
            return self.input  # list of formatted lines


class Instruction:
    def __init__(self, order, opcode):
        self.order = order
        self.opcode = opcode
        self.argTypes = []

    def parse_instruction(self, instruction, headerCount, instrCount):
        self.opcode = instruction

        opcode_types = {
            ".IPPCODE24": [],
            "CREATEFRAME": [],
            "PUSHFRAME": [],
            "POPFRAME": [],
            "RETURN": [],
            "BREAK": [],
            "DEFVAR": ["var"],
            "POPS": ["var"],
            "CALL": ["label"],
            "LABEL": ["label"],
            "JUMP": ["label"],
            "PUSHS": ["symb"],
            "WRITE": ["symb"],
            "EXIT": ["symb"],
            "DPRINT": ["symb"],
            "MOVE": ["var", "symb"],
            "STRLEN": ["var", "symb"],
            "TYPE": ["var", "symb"],
            "NOT": ["var", "symb"],
            "INT2CHAR": ["var", "symb"],
            "READ": ["var", "type"],
            "ADD": ["var", "symb", "symb"],
            "SUB": ["var", "symb", "symb"],
            "MUL": ["var", "symb", "symb"],
            "IDIV": ["var", "symb", "symb"],
            "LT": ["var", "symb", "symb"],
            "GT": ["var", "symb", "symb"],
            "EQ": ["var", "symb", "symb"],
            "AND": ["var", "symb", "symb"],
            "OR": ["var", "symb", "symb"],
            "STRI2INT": ["var", "symb", "symb"],
            "CONCAT": ["var", "symb", "symb"],
            "GETCHAR": ["var", "symb", "symb"],
            "SETCHAR": ["var", "symb", "symb"],
            "JUMPIFEQ": ["label", "symb", "symb"],
            "JUMPIFNEQ": ["label", "symb", "symb"],
            'INT2FLOAT': ['var', 'symb'],
            'FLOAT2INT': ['var', 'symb'],
        }

        if self.opcode in opcode_types:  # if name exists
            # ========== TYPES ARRAY ==========
            for type in opcode_types[self.opcode]:
                self.argTypes.append(type)
            # ================================
            if (
                self.opcode == ".IPPCODE24" and headerCount == 1
            ):  # If there is alredy header
                sys.exit(23)
            instrXML = ET.SubElement(
                root, "instruction", order=str(self.order), opcode=instruction
            )
            # ---------- Tabulation ----------
            instrXML.text = "\n\t\t"
            if self.order != instrCount:
                instrXML.tail = "\n\t"
            else:
                instrXML.tail = "\n"

            return instrXML
        else:
            sys.exit(22)  # Opcode does not exist


class Argument:
    def __init__(self, arg):
        self.arg = arg
        self.type = ""
        self.text = ""
        self.typeForCheck = ""

    def parse_argument(self, arg, instruction, number, typesArray, argLength):
        self.arg = arg
        match = 0

        if re.match(PATTERN_VAR, self.arg):
            self.type = "var"
            self.typeForCheck = "var" 
            frame = re.sub(r"@.*$", "", self.arg).strip()  # GF, LF, TF
            if not frame.isupper():
                sys.exit(23)
            self.text = self.arg
            match = 1
        else:
            self.text = re.sub(
                r"^.*?@", "", self.arg
            ).strip()  # int@5, string@lalala, ...
            match = 1
        # ============================== TYPES ==============================
        if re.match(PATTERN_CONST_INT, self.arg):
            self.type = "int"
            self.typeForCheck = "symb"
            match = 1
        if re.match(PATTERN_CONST_FLOAT, self.arg):
            self.type = "float"
            self.typeForCheck = "symb"
            match = 1
        if re.match(PATTERN_CONST_NIL, self.arg):
            self.type = "nil"
            self.typeForCheck = "symb" 
            match = 1
        if re.match(PATTERN_CONST_STRING, self.arg):
            self.type = "string"
            self.typeForCheck = "string" # s
            match = 1
        if re.match(PATTERN_CONST_BOOL, self.arg):
            self.type = "bool"
            self.typeForCheck = "bool" # s
            match = 1
        if re.match(PATTERN_TYPE, self.arg):
            self.type = "type"
            self.typeForCheck = "type"
            match = 1
        elif re.match(PATTERN_LABEL, self.arg):
            self.type = "label"
            self.typeForCheck = "label"
            match = 1

        if arg.isupper() and not self.type == "var":
            sys.exit(23)

        if match == 0:
            sys.exit(23)

        # ========================================================
        if self.text.startswith("&"):
            self.text = self.text.replace("&", "&amp;")
        if self.text.startswith("<"):
            self.text = self.text.replace("<", "&lt;")
        if self.text.startswith(">"):
            self.text = self.text.replace(">", "&gt;")
        
    
        # ---------- Check compatibility of types ----------

        if self.typeForCheck == typesArray[number - 1]:
            self.type = self.type
        elif self.typeForCheck in ["var", 'bool', 'nil', 'string'] and typesArray[number - 1] == "symb":
            self.type = self.type
        else:
            sys.exit(23)
            

        argXML = ET.SubElement(instruction, "arg{}".format(number), type=str(self.type))
        # ---------- Tabulation ----------
        argXML.text = self.text
        if number != argLength:
            argXML.tail = "\n\t\t"
        else:
            argXML.tail = "\n\t"
        return argXML


# ======================================== MAIN ========================================

input = InputReader()  # == __init__ == tut sozdalsya self.input = []
formatted_lines = input.get_input()  # ['line1', 'line2' '...', ......]
if not formatted_lines:
    sys.exit(21)  # Empty input


root = ET.Element("program", language="IPPcode24")
tree = ET.ElementTree(root)
root.text = "\n\t"  # add new line and tab

# ========== Used Variables ==========
order = 0  # for instructions
isHeader = False

typesArray = []
# ====================================

for formatted_line in formatted_lines:
    # --------------- CHECK HEADER ---------------
    if isHeader == False:
        headerCount = 0
        if formatted_lines[0] == ".IPPcode24":
            isHeader = True
            headerCount += 1
            continue
        else:
            sys.exit(21)
    # --------------------------------------------

    instrCount = len(formatted_lines) - 1
    elements = formatted_line.split()  # ['JUMPIFEQ', 'end', 'GF@counter', 'string@aaa']

    # ================================ INSTRUCTION ================================
    firstElem = elements[0].upper()  # case insensitive
    order += 1
    # ---------- Initialize instruction and check if it's valid ----------
    instrInit = Instruction(order, firstElem)
    readyInstruction = instrInit.parse_instruction(
        firstElem, headerCount, instrCount
    )  # XML object like <Element 'instruction' at 0x10444ebd0>

    typesArray = instrInit.argTypes  # How many args should we have
    # ==============================================================================
    # ============================== ARGUMENT PARSING ==============================
    arguments = []
    for elem in elements[1:]:
        arguments.append(elem)

    number = 0  # number of argument
    argLength = len(arguments) # How many args we got from input
 
    # Check if the number of arguments is allowed
    if argLength > 3 or argLength != len(typesArray):
        sys.exit(23)

    for arg in arguments:
        number += 1
        arg = Argument(arg).parse_argument(
            arg, readyInstruction, number, typesArray, argLength
        )
    # ==============================================================================

xml_string = ET.tostring(root, encoding='utf-8').decode('utf-8')
print(xml_string)

