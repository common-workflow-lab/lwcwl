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

class Translate(object):
    def load(self, fn):
        f = open(fn)
        cont = ""
        self.cmds = []
        for l in f:
            l = l.strip()
            if not l:
                cont = ""
                continue

            if l[0] == "#":
                self.cmds.append([l])
                cont = ""
                continue

            cont += l
            if l.endswith("\\"):
                cont = cont[:-1]
                continue
            sp = cont.split(" ")

            if "=" in sp[0]:
                cap = cont.split("=", 2)
                self.cmds.append(["=", cap[0], cap[1]])
                cont = ""
                continue

            pieces = []
            while sp:
                n = sp.pop(0)
                if not n:
                    continue
                if n.startswith("${"):
                    v = Var()
                    n = n[2:]
                    while not n.endswith("}"):
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
            self.cmds.append(pieces)
            cont = ""

    def start_tool(self, stepvar):
        self.toolin = {}
        self.toolout = ["out"]
        self.stepvar = stepvar
        self.stepid = "%s_%i" % (self.stepvar, len(self.steps))
        self.tool = {
            "id": "tool",
            "class": "CommandLineTool",
            "inputs": {
            },
            "requirements": {},
            "hints": {},
            "doc": "",
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
        if "DockerPull" in self.config:
            self.tool["hints"]["DockerRequirement"] = {"dockerPull": self.config["DockerPull"]}


    def emit(self):
        self.config = {}
        self.binds = {}
        self.stepid = None

        inputs = {}
        outputs = {}
        self.steps = []

        wf = {}

        self.tool = None

        comment_block = False

        for c in self.cmds:
            if c[0] in ("DockerPull",):
                self.config[c[0]] = c[1]
            elif c[0] == "Output":
                outputs[c[1]] = {
                    "type": self.binds[c[1]].pieces[1],
                    "outputSource": self.binds[c[1]].pieces[0]
                }
            elif c[0] == "Run":
                c.pop(0)
                run = c.pop(0)
                stepin = {}
                if not self.stepid:
                    self.stepid = run
                while c:
                    var = c.pop(0)
                    v, r = var.split("=", 2)
                    end = None
                    if r.startswith("${"):
                        end = "}"
                    if r.startswith("\""):
                        end = "\""
                    while not r.endswith(end):
                        r += " " + c.pop(0)
                    if r.startswith("${"):
                        var = Var(r[2:-1].split(" "))
                        self.binds[var.pieces[0]] = var
                        inputs[var.pieces[0]] = var.pieces[1]
                        stepin[v] = var.pieces[0]
                    else:
                        stepin[v] = {"default": json.loads(r)}
                step = {
                    "id": self.stepid,
                    "run": run,
                    "in": stepin,
                    "out": []
                }
                self.steps.append(step)
                self.binds[self.stepid] = Var(["%s/%s" % (self.stepid, "out"), "Directory"])
                self.stepid = None
            elif c[0] == "=":
                self.tool["outputs"][c[1]] = {
                    "type": "File",
                    "outputBinding": {
                        "glob": c[2]
                    }
                }
                self.toolout.append(c[1])
                self.binds[c[1]] = Var(["%s/%s" % (self.stepid, c[1]), "File"])
            elif c[0][0] == "#":
                if comment_block:
                    self.tool["doc"] += c[0][1:] + "\n"
                else:
                    if c[0].startswith("##"):
                        self.start_tool(c[0][2:].strip())
                        comment_block = True
            else:
                if c[0][0] == "\\":
                    c[0] = c[0][1:]

                if not comment_block:
                    self.start_tool(c[0])

                for elm in c:
                    if isinstance(elm, Var):
                        if '/' in elm.pieces[0]:
                            srcstep, path = elm.pieces[0].split('/', 1)
                            self.tool["arguments"].append("$(inputs.%s.path)/%s" % (srcstep, path))
                            self.tool["inputs"][srcstep] = "Directory"
                            self.toolin[srcstep] = self.binds[srcstep].pieces[0]
                        else:
                            inpvar = elm.pieces[0]
                            if inpvar in self.binds:
                                var = self.binds[inpvar]
                            else:
                                var = elm
                                self.binds[inpvar] = var
                                inputs[inpvar] = var.pieces[1]

                            self.tool["inputs"][inpvar] = var.pieces[1]

                            if len(elm.pieces) > 2 and elm.pieces[1] in ("boolean", "boolean?"):
                                self.tool["arguments"].append({
                                    "prefix": elm.pieces[2],
                                    "valueFrom": "$(inputs.%s)" % inpvar
                                })
                            else:
                                self.tool["arguments"].append("$(inputs.%s)" % inpvar)

                            self.toolin[inpvar] = var.pieces[0]
                    elif isinstance(elm, Redirect):
                        if elm.pipe == ">":
                            self.tool["stdout"] = elm.fn
                    elif elm[0] == "|":
                        self.tool["arguments"].append({"shellQuote": False, "valueFrom": "|"})
                        self.tool["arguments"].append(elm[1:])
                        self.tool["hints"]["ShellCommandRequirement"] = {}
                    else:
                        self.tool["arguments"].append(elm)

                step = {
                    "id": self.stepid,
                    "run": self.tool,
                    "in": self.toolin,
                    "out": self.toolout
                }
                self.steps.append(step)
                self.binds[self.stepvar] = Var(["%s/%s" % (self.stepid, "out"), "Directory"])
                comment_block = False
                self.stepid = None

        wf = {
            "cwlVersion": "v1.0",
            "class": "Workflow",
            "steps": self.steps,
            "inputs": inputs,
            "outputs": outputs
        }

        return wf


def main(argv):
    t = Translate()
    t.load(sys.argv[1])
    print json.dumps(t.emit(), indent=4)

    return 0

if __name__ == "__main__":
    exit(main(sys.argv))
