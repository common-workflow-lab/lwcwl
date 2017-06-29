cwlVersion: v1.0
class: CommandLineTool
inputs:
  msg: string
outputs: []
arguments: [echo, $(inputs.msg)]