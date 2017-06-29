#!/usr/bin/env python
import sys
import json

class Var(object):
    def __init__(self, pieces=None):
        self.pieces = pieces if pieces else []

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
            elif n[0] == "|":
                if len(n) == 1:
                    n += sp.pop(0)
                pieces.append(n)
            else:
                pieces.append(n)
        cmds.append(pieces)
        cont = ""

    inputs = {}
    outputs = {}
    config = {}
    binds = {}
    steps = []

    wf = {}

    for c in cmds:
        if c[0] in ("DockerPull",):
            config[c[0]] = c[1]
        elif c[0] in ("Output",):
            outputs[c[1]] = {
                "type": binds[c[1]].pieces[1],
                "outputSource": binds[c[1]].pieces[0]
            }
        else:
            tool = {
                "id": "tool",
                "class": "CommandLineTool",
                "inputs": {
                },
                "requirements": {},
                "hints": {},
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

            if "DockerPull" in config:
                tool["hints"]["DockerRequirement"] = {"dockerPull": config["DockerPull"]}

            toolin = {}
            for elm in c:
                if isinstance(elm, Var):
                    if '/' in elm.pieces[0]:
                        srcstep, path = elm.pieces[0].split('/', 1)
                        tool["arguments"].append("$(inputs.%s.path)/%s" % (srcstep, path))
                        tool["inputs"][srcstep] = "Directory"
                        toolin[srcstep] = binds[srcstep].pieces[0]
                    else:
                        inpvar = elm.pieces[0]
                        if inpvar in binds:
                            var = binds[inpvar]
                        else:
                            var = elm
                            binds[inpvar] = var
                            inputs[inpvar] = var.pieces[1]

                        tool["inputs"][inpvar] = var.pieces[1]

                        if len(elm.pieces) > 2 and elm.pieces[1] in ("boolean", "boolean?"):
                            tool["arguments"].append({
                                "prefix": elm.pieces[2],
                                "valueFrom": "$(inputs.%s)" % inpvar
                            })
                        else:
                            tool["arguments"].append("$(inputs.%s)" % inpvar)

                        toolin[inpvar] = var.pieces[0]
                elif isinstance(elm, Redirect):
                    if elm.pipe == ">":
                        tool["stdout"] = elm.fn
                elif elm[0] == "|":
                    tool["arguments"].append({"shellQuote": False, "valueFrom": "|"})
                    tool["arguments"].append(elm[1:])
                    tool["hints"]["ShellCommandRequirement"] = {}
                else:
                    tool["arguments"].append(elm)

            stepid = "step_"+c[0]
            step = {
                "id": stepid,
                "run": tool,
                "in": toolin,
                "out": ["out"]
            }
            steps.append(step)
            laststep = stepid
            binds[c[0]] = Var(["%s/%s" % (stepid, "out"), "Directory"])

    wf = {
        "cwlVersion": "v1.0",
        "class": "Workflow",
        "steps": steps,
        "inputs": inputs,
        "outputs": outputs
    }

    print json.dumps(wf, indent=4)

    return 0

if __name__ == "__main__":
    exit(main(sys.argv))
