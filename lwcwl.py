#!/usr/bin/env python
import sys
import json

import scanner
from parser import L, SW, Any, Gen, EOL

def listify(x, l):
    if isinstance(x, tuple):
        listify(x[0], l)
        listify(x[1], l)
    elif x is not None and x != "":
        l.append(x)

class Seq(object):
    def __init__(self, pat):
        self.line = []
        listify(pat, self.line)

class Comment(Seq):
    def __repr__(self):
        return "Comment(%s)" % self.line

    def apply(self, target):
        pass

class Arguments(Seq):
    def __repr__(self):
        return "Arguments(%s)" % self.line

class Lit(object):
    def __init__(self, s):
        self.s = s

    def __repr__(self):
        return "Lit(%s)" % self.s

    def apply(self, workflow, step, tool):
        return self.s

class Ref(object):
    def __init__(self, s):
        self.s = s

    def __repr__(self):
        return "Ref(%s)" % self.s

    def apply(self, workflow, step, tool):
        if self.s:
            if self.s[0] not in workflow.binds:
                tp = self.s[1] if len(self.s) > 1 else "Any"
                workflow.wf["inputs"][self.s[0]] = tp
                workflow.binds[self.s[0]] = (self.s[0], tp)
            step["in"][self.s[0]] = workflow.binds[self.s[0]][0]
            tool["inputs"][self.s[0]] = workflow.binds[self.s[0]][1]
            return "$(inputs.%s)" % self.s[0]
        else:
            step["in"]["_inp"] = "%s/out" % workflow.laststep["id"]
            tool["inputs"]["_inp"] = workflow.laststep["run"]["outputs"]["out"]["type"]
            return "$(inputs._inp)"

class Arg(object):
    def __init__(self, pat):
        self.concat = []
        for c in scanner.lex(pat, join=False):
            if c.startswith("${"):
                self.concat.append(Ref(scanner.lex(c[2:-1])))
            elif c.startswith("'") and c.endswith("'"):
                self.concat.append(Lit(c[1:-1]))
            elif c.startswith('"') and c.endswith('"'):
                self.concat.append(Lit(c[1:-1]))
            else:
                self.concat.append(Lit(c))

    def __repr__(self):
        return "Arg(%s)" % self.concat

    def apply(self, workflow, step, tool):
        tool["arguments"].append(''.join(c.apply(workflow, step, tool) for c in self.concat))

class Command(object):
    def __init__(self, pat):
        line = []
        listify(pat, line)
        self.args = line[0]
        self.outputOp = line[1]
        self.outputs = line[2:]

    def __repr__(self):
        return "Command(%s, %s, %s)" % (self.args, self.outputOp, self.outputs)

    def apply(self, workflow):
        tool = {
            "id": "tool",
            "class": "CommandLineTool",
            "inputs": {
            },
            "outputs": {
            },
            "requirements": {},
            "hints": {},
            "doc": "",
            "arguments": []
        }

        step = {
            "in": {},
            "out": ["out"],
            "run": tool
        }

        for arg in self.args.line:
            arg.apply(workflow, step, tool)

        stepname = tool["arguments"][0]
        step["id"] = stepname

        tool["outputs"]["out"] = {
            "type": "File",
            "outputBinding": {
                "glob": self.outputs[0]
            }
        }
        if self.outputOp == ">":
            tool["stdout"] = self.outputs[0]

        workflow.binds[stepname] = ("%s/out" % stepname, "File")

        workflow.wf["steps"].append(step)
        workflow.laststep = step


class Require(object):
    def __init__(self, pat):
        line = []
        listify(pat, line)
        self.req = line[0]
        self.cls = line[1]
        self.etc = line[2:]

    def __repr__(self):
        return "Require(%s, %s, %s)" % (self.req, self.cls, self.etc)

    def apply(self, target):
        pass

class ForScatter(object):
    def __init__(self, pat):
        line = []
        listify(pat, line)
        self.var = line[1]
        self.varset = line[3]
        self.commands = line[5:-1]

    def __repr__(self):
        return "For(%s, %s, %s)" % (self.var, self.varset, self.commands)

    def apply(self, target):
        pass

rest = EOL | (+(Any - EOL) >> EOL)
comment = Gen(SW("#") >> rest, Comment)
arguments = Gen(+(Gen(Any - L(">") - L("=>"), Arg)), Arguments)
command = Gen(arguments >> (L(">") | L("=>")) >> rest, Command)
require = Gen((L("hint") | L("require")) >> Any >> rest, Require)
forscatter = Gen(L("for") >> Any >> L("in") >> Any >> L("do") >> EOL >> +(command - L("done")) >> L("done"), ForScatter)
blank = EOL
statement = comment | require | forscatter | command | blank
grammar = +statement

class Workflow(object):
    def __init__(self):
        self.binds = {}
        self.laststep = None
        self.wf = {
            "class": "Workflow",
            "inputs": {},
            "outputs": {},
            "steps": []
        }

    def finish(self):
        self.wf["outputs"]["out"] = {
            "type": self.laststep["run"]["outputs"]["out"]["type"],
            "outputSource": "%s/out" % self.laststep["id"]
        }

class Translate(object):
    def load(self, fn):
        with open(fn) as f:
            self.pieces = scanner.lex(f.read()+"\n", join=True)
            #self.cmds = grammar.match(self.pieces)
            self.cmds = []
            g, c = grammar.match(self.pieces)
            if c:
                print("Failed at", c)
            else:
                listify(g, self.cmds)

    def emit(self):
        workflow = Workflow()
        for c in self.cmds:
            c.apply(workflow)
        workflow.finish()
        workflow.wf["cwlVersion"] = "v1.0"
        return workflow.wf

def main(argv):
    t = Translate()
    t.load(sys.argv[1])
    print json.dumps(t.emit(), indent=4)

    return 0

if __name__ == "__main__":
    exit(main(sys.argv))
