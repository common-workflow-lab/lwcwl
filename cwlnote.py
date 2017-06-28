#!/usr/bin/env python
import sys
import json

class Var(object):
    def __init__(self):
        self.pieces = []

    def __repr__(self):
        return "Var%s" % self.pieces


class Redirect(object):
    def __init__(self, pipe, fn):
        self.pipe = pipe
        self.fn = fn

    def __repr__(self):
        return "Redirect%s%s" % (self.pipe, self.fn)

def main(argv):
    f = open(argv[1])
    cont = ""
    cmds = []
    for l in f:
        l = l.strip()
        if not l:
            continue
        cont += l
        if l.endswith("\\"):
            cont += " "
            continue
        sp = cont.split(" ")
        pieces = []
        while sp:
            n = sp.pop(0)
            if not n:
                continue
            if n.startswith("$("):
                v = Var()
                n = n[2:]
                while not n.endswith(")"):
                    v.pieces.append(n)
                    n = sp.pop(0)
                v.pieces.append(n[:-1])
                pieces.append(v)
            elif n[0] in ("<", ">"):
                if len(n) == 1:
                    n += sp.pop(0)
                pieces.append(Redirect(n[0], n[1:]))
            else:
                pieces.append(n)
        cmds.append(pieces)
        cont = ""

    inputs = {}
    outputs = {}
    state = {}
    steps = []

    wf = {}

    for c in cmds:
        if c[0] in ("DockerPull",):
            state[c[0]] = c[1]
        else:
            tool = {
                "id": "tool",
                "class": "CommandLineTool",
                "inputs": {
                },
                "outputs": {
                    "out": {
                        "type": "Directory",
                        "outputBinding": {
                            "glob": "."
                        }
                    }
                },
                "arguments": []
            }

            toolin = {}
            for elm in c:
                if isinstance(elm, Var):
                    if '/' in elm.pieces[0]:
                        srcstep, path = elm.pieces[0].split('/', 1)
                        tool["arguments"].append("$(inputs.%s)/%s" % (srcstep, path))
                        tool["inputs"][srcstep] = "Directory"
                        toolin[srcstep] = "%s/out" % srcstep
                    else:
                        inpvar = elm.pieces[0]
                        if inpvar not in inputs:
                            inputs[inpvar] = elm.pieces[1]
                        if inpvar not in tool["inputs"]:
                            tool["inputs"][elm.pieces[0]] = elm.pieces[1]
                        if len(elm.pieces) > 3 and elm.pieces[1] == "boolean" and elm.pieces[2] == "?":
                            tool["arguments"].append({
                                "prefix": elm.pieces[3],
                                "valueFrom": "$(inputs.%s)" % inpvar
                            })
                        else:
                            tool["arguments"].append("$(inputs.%s)" % inpvar)
                        toolin[inpvar] = inpvar
                elif isinstance(elm, Redirect):
                    if elm.pipe == ">":
                        tool["stdout"] = elm.fn
                else:
                    tool["arguments"].append(elm)

            stepid = c[0]
            step = {
                "id": stepid,
                "run": tool,
                "in": toolin,
                "out": ["out"]
            }
            steps.append(step)
            laststep = stepid

    wf = {
        "cwlVersion": "v1.0",
        "class": "Workflow",
        "steps": steps,
        "inputs": inputs,
        "outputs": []
    }

    print json.dumps(wf, indent=4)

    return 0

if __name__ == "__main__":
    exit(main(sys.argv))
